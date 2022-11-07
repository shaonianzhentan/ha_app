from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, HomeAssistant, Context
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.network import get_url
from homeassistant.const import __version__ as current_version

import urllib.parse
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
    EVENT_STATE_CHANGED,
)
# 导入语音小助手
from homeassistant.helpers import intent
from custom_components.conversation import _get_agent

import paho.mqtt.client as mqtt
import logging, json, time, uuid

from .EncryptHelper import EncryptHelper
from .manifest import manifest
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.deprecated(DOMAIN)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    config = entry.data
    app = await hass.async_add_executor_job(
        HaApp,
        hass,
        config.get('key'),
        config.get('topic'),
        entry.entry_id
    )

    hass.data[DOMAIN + config.get('key')] = app

    async def handle_service(service) -> None:
        data = service.data
        message = data.get('message')
        publish_data = {
            'message': message,
            'url': data.get('url', get_url(hass, prefer_external=True)).strip()
        }

        # 标题
        title = data.get('title')
        if title is not None:
            publish_data['title'] = title

        # 执行服务
        action = data.get('action')
        if action is not None:
            publish_data['action'] = json.dumps(action)

        # 推送消息
        result = app.publish({
            'type': 'notify',
            'data': publish_data
        })

        # 生成消息
        hass.loop.create_task(hass.services.async_call('persistent_notification', 'create', {
                    'title': message,
                    'message': json.dumps(result),
                    'notification_id': f'ha_app{result["id"]}'
                }))

    hass.services.async_register(DOMAIN, 'notify', handle_service)

    # 显示二维码
    async def qrcode_service(service):
        key = entry.data['key']
        topic = entry.data['topic']
        qrc = urllib.parse.quote(f'ha:{key}#{topic}')
        await hass.services.async_call('persistent_notification', 'create', {
                    'title': '使用【家庭助理Android应用】扫码关联',
                    'message': f'[![qrcode](https://cdn.dotmaui.com/qrc/?t={qrc})](https://github.com/shaonianzhentan/ha_app) 内含密钥和订阅主题，请勿截图分享'
                })

    hass.services.async_register(DOMAIN, 'qrcode', qrcode_service)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    config = entry.data
    key = DOMAIN + config.get('key')
    hass.data[key].unload()
    del hass.data[key]
    return True

class HaApp():

    def __init__(self, hass, key, topic, entry_id):
        self.hass = hass
        self.msg_cache = {}

        self.entry_id = entry_id
        self.key = key
        self.topic = topic

        self.encryptor = EncryptHelper(self.key, 'ha-app')

        # 订阅与推送
        self.push_topic = f"{self.topic}/app"
        self.subscribe_topic = f"{self.topic}/ha"

        # 运行MQTT服务
        if hass.state == CoreState.running:
            self.connect()
        else:
            hass.bus.listen_once(EVENT_HOMEASSISTANT_STARTED, self.connect)

    def connect(self, event=None):
        HOST = 'test.mosquitto.org'
        PORT = 1883
        client = mqtt.Client()
        self.client = client
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.on_subscribe = self.on_subscribe
        client.on_disconnect = self.on_disconnect
        client.connect(HOST, PORT, 60)
        client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        self.log("connectd %s" % self.subscribe_topic)
        self.client.subscribe(self.subscribe_topic, 2)

    def on_disconnect(self, client, userdata, rc):
        self.log("Unexpected disconnection %s" % rc)
        if rc == 7:
            self.hass.loop.create_task(self.hass.services.async_call('homeassistant', 'reload_config_entry', {
                    'entry_id': self.entry_id
                }))

    def on_subscribe(self, client, userdata, mid, granted_qos):
        self.log("On Subscribed: qos = %d" % granted_qos)

    def unload(self):
        self.log("停止服务 %s" % self.subscribe_topic)
        self.client.disconnect()
        self.client = None

    def on_message(self, client, userdata, msg):
        payload = str(msg.payload.decode('utf-8'))
        try:
            # 解析消息
            data = json.loads(self.encryptor.Decrypt(payload))
            _LOGGER.debug(data)
            self.clear_cache_msg()

            msg_time = data['time']
            msg_type = data['type']
            now = int(time.time())
            # 判断消息是否过期(5s)
            if now - 5 > msg_time:
                self.log(f'【{msg_time}】{msg_type}消息已过期')
                return

            msg_id = data['id']
            # 判断消息是否已接收
            if msg_id in self.msg_cache:
                self.log(f'【{msg_time}】{msg_type}消息已处理')
                return

            # 设置消息为已接收
            self.msg_cache[msg_id] = now

            # 消息类型
            msg_data = data['data']
            dev_id = data['dev_id']

            if msg_type == 'conversation':
                # 调用语音小助手API
                self.hass.loop.create_task(self.async_process(msg_data['text'], conversation_id=msg_id))
            elif msg_type == 'gps':
                # 设置坐标位置
                self.hass.services.call('device_tracker', 'see', {
                    'dev_id': dev_id,
                    'gps': [msg_data['latitude'], msg_data['longitude']],
                    'battery': msg_data['battery']
                })
                self.send_notify_msg()
            elif msg_type == 'qrcode':
                # 扫码成功
                self.hass.services.call('persistent_notification', 'create', {
                    'title': '家庭助理Android应用',
                    'message': f"【{dev_id}】扫码成功"
                })
                self.publish({
                    'type': msg_type,
                    'data': {
                        'internal_url': get_url(self.hass),
                        'external_url': get_url(self.hass, prefer_external=True),
                        'ha_version': current_version,
                        'version': manifest.version
                    }
                })
            elif msg_type == 'action':
                # 执行服务
                action_data = json.loads(msg_data)
                arr = action_data['service'].split('.')
                service_data = action_data.get('data', {})
                self.hass.services.call(arr[0], arr[1], service_data)
            elif msg_type == 'online':
                self.log(f'【{msg_time}】{msg_type}连接成功')
                # APP连接成功
                self.send_notify_msg()
            elif msg_type == 'notify':
                # 通知已读
                self.clear_notify_msg(msg_data)
            elif msg_type == 'log':
                # 显示日志
                _LOGGER.error(msg_data)

        except Exception as ex:
            self.log(ex, '出现异常')

    async def async_process(self, text, conversation_id):
        agent = await _get_agent(self.hass)
        try:
            intent_result = await agent.async_process(text, context=Context(), conversation_id=conversation_id)
        except intent.IntentHandleError as err:
            intent_result = intent.IntentResponse()
            intent_result.async_set_speech(str(err))

        if intent_result is None:
            intent_result = intent.IntentResponse()
            intent_result.async_set_speech("对不起，我不知道你想干啥")

        # 推送回复消息
        plain = intent_result.speech['plain']
        await self.hass.async_add_executor_job(self.publish, {
            'type': 'conversation',
            'data': plain
        })

    def publish(self, data):
        # 判断当前连接状态
        if self.client._state == 2:
            self.log('断开重连')
            self.connect()

        # 加密消息
        if 'id' not in data:
            data.update({
                'id': uuid.uuid1().hex,
                'time': int(time.time())
            })

        payload = self.encryptor.Encrypt(json.dumps(data))
        self.client.publish(self.push_topic, payload, qos=2)
        return data

    # 发送通知消息
    def send_notify_msg(self):
        states = self.hass.states.async_all('persistent_notification')
        for state in states:
            if state.entity_id.startswith('persistent_notification.ha_app'):
                message = state.attributes.get('message')
                data = json.loads(message)
                self.log(f'发送消息：{data["id"]}')
                self.publish(data)

    # 清除通知消息
    def clear_notify_msg(self, notify_id):
        self.log(f'消息已送达：{notify_id}')
        self.hass.services.call('persistent_notification', 'dismiss', {
            'notification_id': f'ha_app{notify_id}'
        })

    # 清理缓存消息
    def clear_cache_msg(self):
        now = int(time.time())
        for key in list(self.msg_cache.keys()):
            # 缓存消息超过10秒
            if key in self.msg_cache and now - 10 > self.msg_cache[key]:
                del self.msg_cache[key]

    # 日志
    def log(self, msg, title=''):
        print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), '【ha_app】', title , msg)