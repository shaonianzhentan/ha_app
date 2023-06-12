import requests, time, logging

_LOGGER = logging.getLogger(__name__)

class BaiduMap():

    def __init__(self, hass, ak, service_id) -> None:
        self.hass = hass
        self.config = {
            'ak': ak,
            'service_id': service_id
        }

    def get_entity_name(self, name):
        return name.replace(' ', '')

    async def async_get_entitylist(self):
        ''' 验证实体 '''
        result = await self.hass.async_add_executor_job(self.get, 'https://yingyan.baidu.com/api/v3/entity/list', {
            **self.config
        })
        if result.get('status') == 3003:
          result = await self.async_add_entity('homeassistant', '在HA中使用初始创建_并不会直接使用')
        return result

    async def async_add_entity(self, device_id, device_name):
        ''' 注册设备 '''
        result = await self.hass.async_add_executor_job(self.post, 'https://yingyan.baidu.com/api/v3/entity/add', {
            **self.config,
            'entity_name': device_id,
            'entity_desc': self.get_entity_name(device_name)
        })
        return result

    async def async_add_point(self, device_id, latitude, longitude, radius):
        ''' 上报位置 '''
        result = await self.hass.async_add_executor_job(self.post, 'https://yingyan.baidu.com/api/v3/track/addpoint', {
            **self.config,
            'entity_name': device_id,
            'latitude': latitude,
            'longitude': longitude,
            'radius': radius,
            'loc_time': int(time.time()),
            'coord_type_input': 'wgs84'
        })
        return result

    def post(self, url, data):
        res = requests.post(url, data=data)
        result = res.json()
        return result

    def get(self, url, data):
        res = requests.get(url, params=data)
        result = res.json()
        return result