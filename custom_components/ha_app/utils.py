import aiohttp, json, os, pytz, hashlib
from homeassistant.helpers.storage import STORAGE_DIR
from datetime import datetime
from homeassistant.components.persistent_notification import _async_get_or_create_notifications


def get_notifications(hass, device_id):
    # 使用新版通知
    _list = []
    notifications = _async_get_or_create_notifications(hass)
    notification_id = md5(device_id)
    for key in notifications:
        if key.startswith(notification_id):
            notification = notifications[key]
            message = notification.get('message')
            result = json.loads(message)
            result['id'] = key
            _list.append(result)
    return _list

def call_service(hass, service_name, service_data):
    ''' 调用服务 '''
    arr = service_name.split('.')
    hass.loop.create_task(hass.services.async_call(arr[0], arr[1], service_data))

def get_storage_dir(file_name):
    ''' 存储目录 '''
    return os.path.abspath(f'{STORAGE_DIR}/{file_name}')

def md5(data):
    return hashlib.md5(data.encode('utf-8')).hexdigest()

async def async_http_post(url, data):
    ''' HTTP POST '''
    headers = {
        'Content-Type': 'application/json'
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=json.dumps(data), headers=headers) as response:
            return await response.json()
        
def timestamp_state(hass):
    ''' 时间戳状态 '''
    return datetime.now(pytz.timezone(hass.config.time_zone)).isoformat()
        
async def async_register_sensor(webhook_url, unique_id, icon, state, attributes, register_data):
    ''' 注册传感器 '''
    sensor_data = {
        "unique_id": unique_id,
        'icon': icon,
        'state': state,
        'attributes': attributes,
        "type": "sensor"
    }
    result = await async_http_post(webhook_url, {
        "data": [ sensor_data ],
        "type": "update_sensor_states"
    })
    bl = result.get(unique_id)
    if bl is not None and 'error' in bl:
        error = bl.get('error')
        if error.get('code') == 'not_registered':
            # 注册传感器
            await async_http_post(webhook_url, {
                "data": {
                    "entity_category": "diagnostic",
                    **register_data,
                    **sensor_data
                },
                "type": "register_sensor"
            })