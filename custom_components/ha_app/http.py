import time, json, aiohttp, hashlib
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.persistent_notification import _async_get_or_create_notifications
from homeassistant.helpers.storage import STORAGE_DIR
from homeassistant.util.json import load_json
from .manifest import manifest
from homeassistant.helpers.network import get_url
from datetime import datetime
import logging, pytz, os

from .file_api import mkdir

_LOGGER = logging.getLogger(__name__)

def md5(data):
    return hashlib.md5(data.encode('utf-8')).hexdigest()

class HttpView(HomeAssistantView):

    url = "/api/haapp"
    name = "api:haapp"
    requires_auth = False
    # 计数器
    count = 0
    timezone = None
    # 设备名称
    device = {}

    @property
    def now(self):
        return datetime.now(self.timezone).isoformat()
    
    def get_storage_dir(self, file_name):
        return os.path.abspath(f'{STORAGE_DIR}/{file_name}')

    def get_device(self, webhook_id):
        ''' 获取设备信息 '''
        if webhook_id not in self.device:
            config_entries = load_json(self.get_storage_dir('core.config_entries'))
            entries = config_entries['data']['entries']
            for entity in entries:
                entity_data = entity.get('data')
                if entity_data is not None and entity_data.get('webhook_id') == webhook_id:
                    self.device[webhook_id] = {
                        'id': entity_data.get('device_id'),
                        'latitude': 0,
                        'longitude': 0
                    }
        return self.device.get(webhook_id)

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

        # 附加数据
        data = body.get('data')
        if data is not None:
            # 链接
            url = data.get('url')
            if url is not None:
                result['url'] = url
            # TTS
            tts = data.get('tts')
            if tts is not None:
                result['tts'] = tts
            # 启动项
            start = data.get('start')
            if start is not None:
                result['start'] = start

        device = self.get_device(webhook_id)
        notification_id = f'{md5(device.get("id"))}{self.count}'
        self.count = self.count + 1
        if self.count > 50:
            self.count = 0

        self.call_service(hass, 'persistent_notification.create', {
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

        # 设置时区
        self.timezone = pytz.timezone(hass.config.time_zone)
        
        webhook_id = body.get('webhook_id')
        if webhook_id is None:
            return self.json([])

        # 获取设备webhook地址
        base_url = get_url(hass)
        webhook_url = f"{base_url}/api/webhook/{webhook_id}"

        _type = body.get('type')
        data = body.get('data')

        # 发送事件
        if ['notify', 'sms', 'button'].count(_type) > 0:
            hass.bus.fire('ha_app', { 'type': _type, 'data': data })

        device = self.get_device(webhook_id)
        if _type == 'gps': # 位置
            hass.loop.create_task(self.async_update_device(hass, webhook_url, data, device))
        elif _type == 'notify': # 通知                
            hass.loop.create_task(self.async_update_notify(hass, webhook_url, data))
        elif _type == 'notify_list': # 通知列表
            for item in data:
                await self.async_update_notify(hass, webhook_url, item)
        elif _type == 'sms': # 短信
            hass.loop.create_task(self.async_update_sms(hass, webhook_url, data))
        elif _type == 'event': # 系统事件
            hass.loop.create_task(self.async_update_event(hass, webhook_url, data))

        # 使用新版通知
        _list = []
        notifications = _async_get_or_create_notifications(hass)
        notification_id = md5(device.get('id'))
        for key in notifications:
            if key.startswith(notification_id):
                notification = notifications[key]
                message = notification.get('message')
                result = json.loads(message)
                result['id'] = key
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

    async def async_update_device(self, hass, webhook_url, body, device):
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
            # 鹰眼轨迹服务
            map = hass.data.get(manifest.domain)
            if map is not None:
                device_id = device.get('id')
                if device.get('latitude') == latitude and device.get('longitude') == longitude:
                    _LOGGER.debug('位置相同不上报，节省额度')
                else:
                    await map.async_add_point(device_id, latitude, longitude, gps_accuracy)
                # 记录坐标
                device['latitude'] = latitude
                device['longitude'] = longitude

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

        battery_data = {
            "state": battery,
            "type": "sensor",
            "icon": icon,
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
                        **battery_data
                    },
                    "type": "register_sensor"
                })
                # 注册

    async def async_update_sms(self, hass, webhook_url, data):
        ''' 更新短信 '''

        sensor_data = {
            "attributes": {
                "from": str(data['from']),
                "text": data['content']
            },
            "state": self.now,
            "type": "sensor",
            "icon": "mdi:message",
            "unique_id": "short_message"
        }
        result = await self.async_http_post(hass, webhook_url, {
            "data": [ sensor_data ],
            "type": "update_sensor_states"
        })
        bl = result.get('short_message')
        if bl is not None and 'error' in bl:
            error = bl.get('error')
            if error.get('code') == 'not_registered':
                # 注册传感器
                await self.async_http_post(hass, webhook_url, {
                    "data": {
                        "device_class": "timestamp",
                        "entity_category": "diagnostic",
                        "name": "短信",
                        **sensor_data
                    },
                    "type": "register_sensor"
                })

    async def async_update_notify(self, hass, webhook_url, data):
        ''' 更新通知 '''

        sensor_data = {
            "attributes": {
                "title": data['title'],
                "content": data['content'],
                "text": data['text'],
                "package": data['package']
            },
            "state": self.now,
            "type": "sensor",
            "icon": "mdi:cellphone-message",
            "unique_id": "application_notification"
        }
        result = await self.async_http_post(hass, webhook_url, {
            "data": [ sensor_data ],
            "type": "update_sensor_states"
        })
        bl = result.get('application_notification')
        if bl is not None and 'error' in bl:
            error = bl.get('error')
            if error.get('code') == 'not_registered':
                # 注册传感器
                await self.async_http_post(hass, webhook_url, {
                    "data": {
                        "device_class": "timestamp",
                        "entity_category": "diagnostic",
                        "name": "通知",
                        **sensor_data
                    },
                    "type": "register_sensor"
                })

    async def async_update_event(self, hass, webhook_url, data):
        ''' 系统事件 '''

        battery = data.get('battery')
        text = data.get('text')

        sensor_data = {
            "state": text,
            "type": "sensor",
            "icon": "mdi:cellphone-information",
            "unique_id": "system_event"
        }
        result = await self.async_http_post(hass, webhook_url, {
            "data": [ sensor_data ],
            "type": "update_sensor_states"
        })
        bl = result.get('system_event')
        if bl is not None and 'error' in bl:
            error = bl.get('error')
            if error.get('code') == 'not_registered':
                # 注册传感器
                await self.async_http_post(hass, webhook_url, {
                    "data": {
                        "entity_category": "diagnostic",
                        "name": "系统事件",
                        **sensor_data
                    },
                    "type": "register_sensor"
                })
        # 更新手机电量
        await self.async_update_battery(hass, webhook_url, battery)

class HttpViewTTS(HomeAssistantView):

    url = "/api/haapp/tts"
    name = "api:haapp:tts"
    requires_auth = True

    async def put(self, request):
        hass = request.app["hass"]

        reader = await request.multipart()
        formData = {}
        while True:
            part = await reader.next()
            if part is None:
                break
            '''
            if part.headers[aiohttp.hdrs.CONTENT_TYPE] == 'application/json':
                metadata = await part.json()
                continue
            '''
            if part.filename is None:
                value = await part.text()
            else:
                value = await self.async_write_file(hass, part)
            formData[part.name] = value

        file = formData.get('file')
        entities = formData.get('entities')
        print(file, entities)
        if file is not None and entities is not None:
            self.call_service(hass, 'media_player.play_media', {
                        'media_content_type': 'audio/mpeg',
                        'media_content_id': file,
                        'entity_id': entities
                    })
            return self.json_message("推送成功")

        return self.json_message("参数异常", status_code=500)

    async def async_write_file(self, hass, file):
        filename = file.filename
        size = 0
        path = hass.config.path(f'media/ha_app')
        mkdir(path)
        with open(f'{path}/{filename}', 'wb') as f:
            while True:
                chunk = await file.read_chunk()  # 默认是8192个字节。
                if not chunk:
                    break
                size += len(chunk)
                f.write(chunk)

        return f'media-source://media_source/local/ha_app/{filename}'

    def call_service(self, hass, service_name, service_data):
        ''' 调用服务 '''
        arr = service_name.split('.')
        hass.loop.create_task(hass.services.async_call(arr[0], arr[1], service_data))