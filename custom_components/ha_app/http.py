import time
import json
import logging
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.network import get_url

from .utils import call_service, async_http_post, async_register_sensor, timestamp_state, md5, get_notifications

_LOGGER = logging.getLogger(__name__)

class HttpView(HomeAssistantView):

    url = "/api/haapp"
    name = "api:haapp"
    requires_auth = False
    # 计数器
    count = 0
    
    async def get(self, request):
        query = request.query
        ver = query.get('ver')
        # 判断当前APP版本是否支持本插件
        result = ''
        if ver is not None and ver < '2.2':
            result = '请将APP升级到最新版本'
        return self.json_message(result, status_code=200)

    async def post(self, request):
        ''' 保留通知消息 '''
        hass = request.app["hass"]

        body = await request.json()
        _LOGGER.debug(body)

        push_token = body.get('push_token')
        title = body.get('title')
        message = body.get('message')
        data = body.get('data')

        registration_info = body.get('registration_info')
        webhook_id = registration_info.get('webhook_id')

        # 特殊情况
        if message == 'ha_app_control':
            hass.bus.fire("ha_app_control", {"webhook_id": webhook_id, **data})
            return self.json_message("触发成功", status_code=201)

        result = {
            'title': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) if title is None else title,
            'message': message,
        }

        # 附加数据
        if data is not None:
            # 按钮
            actions = data.get('actions')
            if actions is not None:
                result['actions'] = actions
            # 图片
            image = data.get('image')
            if image is not None:
                result['image'] = image

        notification_id = f'{md5(webhook_id)}{time.strftime("%m%d%H%M%S", time.localtime())}{self.count}'
        self.count = self.count + 1
        if self.count > 50:
            self.count = 0

        call_service(hass, 'persistent_notification.create', {
            'title': message,
            'message': json.dumps(result, indent=2, ensure_ascii=False),
            'notification_id': notification_id
        })
        return self.json_message("推送成功", status_code=201)

    async def put(self, request):
        ''' 上传GPS信息 '''
        result = await self.async_validate_access_token(request)
        if result is not None:
            return result

        # 上报GPS位置
        hass = request.app["hass"]
        body = await request.json()
        _LOGGER.debug(body)

        webhook_id = body.get('webhook_id')
        if webhook_id is None:
            return self.json_message("参数异常", status_code=204)

        # 获取设备webhook地址
        base_url = get_url(hass)
        webhook_url = f"{base_url}/api/webhook/{webhook_id}"

        _type = body.get('type')
        data = body.get('data')

        if _type == 'gps':  # 位置
            hass.loop.create_task(
                self.async_update_device(hass, webhook_url, data))
        elif _type == 'notify_list':  # 通知列表
            for item in data:
                await self.async_update_notify(hass, webhook_url, item)
        elif _type == 'sms':  # 短信
            hass.loop.create_task(
                self.async_update_sms(hass, webhook_url, data))
        elif _type == 'button':  # 按钮事件
            hass.loop.create_task(
                self.async_update_button(hass, webhook_url, data))
        elif _type == 'nfc':  # NFC
            hass.loop.create_task(
                self.async_update_nfc(hass, webhook_url, data))
        elif _type == 'event':  # 系统事件
            hass.loop.create_task(
                self.async_update_event(hass, webhook_url, data))

        # 使用新版通知
        notifications = get_notifications(hass, webhook_id)
        response = {
            'notify': notifications
        }
        if _type == 'webhook':
            # webhook
            response['data'] = await async_http_post(webhook_url, data)
        # print(response)
        return self.json(response)

    async def delete(self, request):
        ''' 清除通知 '''
        result = await self.async_validate_access_token(request)
        if result is not None:
            return result

        hass = request.app["hass"]
        query = request.query
        ids = query.get('id').split(',')
        for notification_id in ids:
            call_service(hass, 'persistent_notification.dismiss',
                         {'notification_id': notification_id})
        return self.json_message("删除通知提醒", status_code=200)

    def get_access_token(self, request):
        authorization = request.headers.get('Authorization')
        return str(authorization).replace('Bearer', '').strip()

    async def async_validate_access_token(self, request):
        ''' 授权验证 '''
        hass = request.app["hass"]
        hass_access_token = self.get_access_token(request)
        token = hass.auth.async_validate_access_token(hass_access_token)
        if token is None:
            return self.json_message("未授权", status_code=401)

    async def async_update_device(self, hass, webhook_url, body):
        ''' 更新设备 '''
        latitude = body.get('latitude')
        longitude = body.get('longitude')
        battery = body.get('battery')
        gps_accuracy = body.get('gps_accuracy')

        # 更新位置
        result = await async_http_post(webhook_url, {
            "type": "update_location",
            "data": {
                "gps": [latitude, longitude],
                "gps_accuracy": gps_accuracy,
                "battery": battery
            }
        })
        if result is not None:
            await self.async_update_battery(hass, webhook_url, battery)

    async def async_update_battery(self, hass, webhook_url, battery):
        ''' 更新电量 '''
        battery = int(battery)
        icon = "mdi:battery"

        if battery <= 90:
            icon = "mdi:battery-90"
        elif battery <= 80:
            icon = "mdi:battery-80"
        elif battery <= 70:
            icon = "mdi:battery-70"
        elif battery <= 60:
            icon = "mdi:battery-60"
        elif battery <= 50:
            icon = "mdi:battery-50"
        elif battery <= 40:
            icon = "mdi:battery-40"
        elif battery <= 30:
            icon = "mdi:battery-30"
        elif battery <= 20:
            icon = "mdi:battery-20"
        elif battery <= 10:
            icon = "mdi:battery-10"

        await async_register_sensor(webhook_url,
                                    unique_id="battery_level",
                                    icon=icon,
                                    state=battery,
                                    attributes={},
                                    register_data={
                                        "device_class": "battery",
                                        "unit_of_measurement": "%",
                                        "name": "电量",
                                    }
                                    )

    async def async_update_sms(self, hass, webhook_url, data):
        ''' 更新短信 '''
        await async_register_sensor(webhook_url,
                                    unique_id="short_message",
                                    icon="mdi:message",
                                    state=timestamp_state(hass),
                                    attributes={
                                        "from": str(data['from']),
                                        "text": data['content']
                                    },
                                    register_data={
                                        "name": "短信",
                                        "device_class": "timestamp"
                                    }
                                    )

    async def async_update_button(self, hass, webhook_url, data):
        ''' 更新按钮事件 '''
        await async_register_sensor(webhook_url,
                                    unique_id="ha_app_button",
                                    icon="mdi:gesture-tap-button",
                                    state=timestamp_state(hass),
                                    attributes={"key": data},
                                    register_data={
                                        "name": "按钮事件",
                                        "device_class": "timestamp"
                                    }
                                    )

    async def async_update_nfc(self, hass, webhook_url, data):
        ''' 更新NFC '''
        await async_register_sensor(webhook_url,
                                    unique_id="scan_nfc",
                                    icon="mdi:nfc-variant",
                                    state=timestamp_state(hass),
                                    attributes={
                                        "id": data['id']
                                    },
                                    register_data={
                                        "name": "NFC",
                                        "device_class": "timestamp"
                                    }
                                    )

    async def async_update_notify(self, hass, webhook_url, data):
        ''' 更新通知 '''
        await async_register_sensor(webhook_url,
                                    unique_id="application_notification",
                                    icon="mdi:cellphone-message",
                                    state=timestamp_state(hass),
                                    attributes={
                                        "title": data['title'],
                                        "content": data['content'],
                                        "text": data['text'],
                                        "package": data['package']
                                    },
                                    register_data={
                                        "device_class": "timestamp",
                                        "name": "通知",
                                    }
                                    )

    async def async_update_event(self, hass, webhook_url, data):
        ''' 系统事件 '''
        battery = data.get('battery')
        text = data.get('text')
        source = data.get('source')

        await async_register_sensor(webhook_url,
                                    unique_id="system_event",
                                    icon="mdi:cellphone-information",
                                    state=timestamp_state(hass),
                                    attributes={
                                        'text': text,
                                        'source': source
                                    },
                                    register_data={
                                        "device_class": "timestamp",
                                        "name": "系统事件",
                                    }
                                    )
        # 更新手机电量
        await self.async_update_battery(hass, webhook_url, battery)