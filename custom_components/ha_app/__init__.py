from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CoreState, HomeAssistant, Context
import homeassistant.helpers.config_validation as cv

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
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.deprecated(DOMAIN)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.async_add_executor_job(
        HaApp,
        hass,
        entry.data
    )
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True

class HaApp():

    def __init__(self, hass, config):
        self.hass = hass
        self.msg_cache = {}

        self.key = config.get('key')
        self.topic = config.get('topic')

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
        HOST = 'broker-cn.emqx.io'
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
        print('connectd')
        self.client.subscribe(self.subscribe_topic, 2)

    # 清理缓存消息
    def clear_cache_msg(self):
        now = int(time.time())
        for key in self.msg_cache:
            # 缓存消息超过10秒
            if now - 10 > self.msg_cache[key]:
                del self.msg_cache[key]

    def on_message(self, client, userdata, msg):
        payload = str(msg.payload.decode('utf-8'))
        try:
            # 解析消息
            data = json.loads(self.encryptor.Decrypt(payload))
            _LOGGER.debug(data)
            self.clear_cache_msg()

            now = int(time.time())
            # 判断消息是否过期(5s)
            if now - 5 > data['time']:
                print('消息已过期')
                return

            msg_id = data['id']
            # 判断消息是否已接收
            if msg_id in self.msg_cache:
                print('消息已处理')
                return

            # 设置消息为已接收
            self.msg_cache[msg_id] = now

            # 消息类型
            msg_type = data['type']

            if msg_type == 'conversation':
                # 调用语音小助手API
                self.hass.loop.create_task(self.async_process(data['text'], conversation_id=msg_id))
            elif msg_type == 'gps':
                # 设置坐标位置
                latitude = data['latitude']
                longitude = data['longitude']
                self.hass.services.call('device_tracker', 'see', {
                    'dev_id': data['dev_id'],
                    'gps': [latitude, longitude]
                })

        except Exception as ex:
            print(ex)

    async def async_process(self, text, conversation_id):
        agent = await _get_agent(self.hass)
        try:
            intent_result = await agent.async_process(text, context=Context(), conversation_id=conversation_id)
        except intent.IntentHandleError as err:
            intent_result = intent.IntentResponse()
            intent_result.async_set_speech(str(err))

        if intent_result is None:
            intent_result = intent.IntentResponse()
            intent_result.async_set_speech("Sorry, I didn't understand that")

        # 推送回复消息
        plain = intent_result.speech['plain']
        _LOGGER.debug(plain)
        await self.hass.async_add_executor_job(self.publish, {
            'type': 'conversation',
            'data': plain
        })

    def on_subscribe(self, client, userdata, mid, granted_qos):
        print("On Subscribed: qos = %d" % granted_qos)

    def on_disconnect(self, client, userdata, rc):
        print("Unexpected disconnection %s" % rc)

    def publish(self, data):
        # 判断当前连接状态
        if self.client._state == 2:
            _LOGGER.debug('断开重连')
            self.client.reconnect()
            self.client.loop_start()

        # 加密消息
        payload = self.encryptor.Encrypt(json.dumps(data))
        self.client.publish(self.push_topic, payload, qos=0)