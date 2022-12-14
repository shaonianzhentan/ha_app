import time, json, requests, aiohttp
from homeassistant.components.http import HomeAssistantView
from .manifest import manifest
from homeassistant.helpers.network import get_url
from .EncryptHelper import md5, EncryptHelper
import logging

_LOGGER = logging.getLogger(__name__)

class HttpView(HomeAssistantView):

    url = "/api/haapp"
    name = "api:haapp"
    requires_auth = False
    # 计数器
    count = 0

    async def post(self, request):
        ''' 保留通知消息 '''
        hass = request.app["hass"]

        body = await request.json()
        _LOGGER.debug(body)
        
        push_token = body.get('push_token')
        title = body.get('title')
        message = body.get('message')

        registration_info = body.get('registration_info')
        webhook_id = registration_info.get('webhook_id')

        result = {
            'title': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) if title is None else title,
            'message': message,
        }

        notification_id = f'{md5(webhook_id)}{self.count}'
        self.count = self.count + 1
        if self.count > 50:
            self.count = 0

        self.call_service(hass, 'persistent_notification.create', {
                    'title': message,
                    'message': json.dumps(result),
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
            return self.json([])

        # 获取设备webhook地址
        base_url = get_url(hass)
        webhook_url = f"{base_url}/api/webhook/{webhook_id}"

        # 新版数据
        _type = body.get('type')
        if _type is not None:
            data = body.get('data')
            if _type == 'gps': # 位置
                hass.loop.create_task(self.async_update_device(hass, webhook_url, data))
            elif _type == 'notify': # 通知
                hass.bus.fire('ha_app_notify', data)
            elif _type == 'ringing': # 来电
                hass.bus.fire('ha_app_ringing', data)
            elif _type == 'text': # 短信
                hass.bus.fire('ha_app_text', data)
            elif _type == 'ScreenOn': # 亮屏
                hass.bus.fire('ha_app', { 'action': 'screen_on' })
                battery = data.get('battery')
                if battery is not None:
                    hass.loop.create_task(self.async_update_battery(hass, webhook_url, battery))
        else:
            hass.loop.create_task(self.async_update_device(hass, webhook_url, body))

        _list = []
        states = hass.states.async_all('persistent_notification')
        notification_id = md5(webhook_id)
        for state in states:
            if state.entity_id.startswith(f'persistent_notification.{notification_id}'):
                message = state.attributes.get('message')
                result = json.loads(message)
                result['id'] = state.entity_id.replace('persistent_notification.', '')
                _list.append(result)
        return self.json(_list)

    async def delete(self, request):
        ''' 清除通知 '''
        result = await self.async_validate_access_token(request)
        if result is not None:
            return result

        hass = request.app["hass"]
        query = request.query
        ids = query.get('id').split(',')
        for notification_id in ids:
            self.call_service(hass, 'persistent_notification.dismiss', { 'notification_id': notification_id })
        return self.json_message("删除通知提醒", status_code=200)

    def call_service(self, hass, service_name, service_data):
        ''' 调用服务 '''
        arr = service_name.split('.')
        hass.loop.create_task(hass.services.async_call(arr[0], arr[1], service_data))

    async def async_validate_access_token(self, request):
        ''' 授权验证 '''
        hass = request.app["hass"]
        authorization = request.headers.get('Authorization')
        hass_access_token = str(authorization).replace('Bearer', '').strip()
        # print(hass_access_token)
        token = await hass.auth.async_validate_access_token(hass_access_token)
        if token is None:
            return self.json_message("未授权", status_code=401)

    async def async_http_post(self, hass, url, data):
        headers = {
            'Content-Type': 'application/json'
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=json.dumps(data), headers=headers) as response:
                return await response.json()

    async def async_update_device(self, hass, webhook_url, body):
        ''' 更新设备 '''
        latitude = body.get('latitude')
        longitude = body.get('longitude')
        battery = body.get('battery')
        gps_accuracy = body.get('gps_accuracy')

        # 更新位置
        result = await self.async_http_post(hass, webhook_url, {
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

        battery_data = {
            "state": battery,
            "type": "sensor",
            "unique_id": "battery_level"
        }
        result = await self.async_http_post(hass, webhook_url, {
            "data": [ battery_data ],
            "type": "update_sensor_states"
        })
        bl = result.get('battery_level')
        if bl is not None and 'error' in bl:
            error = bl.get('error')
            if error.get('code') == 'not_registered':
                # 注册传感器
                await self.async_http_post(hass, webhook_url, {
                    "data": {
                        "state_class": "measurement",
                        "entity_category": "diagnostic",
                        "device_class": "battery",
                        "unit_of_measurement": "%",
                        "name": "电量",
                        "icon": "mdi:battery",
                        **battery_data
                    },
                    "type": "register_sensor"
                })