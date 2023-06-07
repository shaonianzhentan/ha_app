import requests, time

class BaiduMap():

    def __init__(self, hass, ak, service_id) -> None:
        self.hass = hass
        self.config = {
            'ak': ak,
            'service_id': service_id
        }

    def get_entity_name(self, name):
        name = ''.join([i.strip(' ') for i in name])
        return name
    
    async def async_get_entitylist(self):
        ''' 验证实体 '''
        result = await self.hass.async_add_executor_job(self.get, 'https://yingyan.baidu.com/api/v3/entity/list', {
            **self.config
        })
        return result

    async def async_add_entity(self, name):
        ''' 注册设备 '''
        result = await self.hass.async_add_executor_job(self.post, 'https://yingyan.baidu.com/api/v3/entity/add', {
            **self.config,
            'entity_name': self.get_entity_name(name),
        })
        return result

    async def async_add_point(self, name, latitude, longitude, radius):
        ''' 上报位置 '''
        result = await self.hass.async_add_executor_job(self.post, 'https://yingyan.baidu.com/api/v3/track/addpoint', {
            **self.config,
            'entity_name': self.get_entity_name(name),
            'latitude': latitude,
            'longitude': longitude,
            'radius': radius,
            'loc_time': int(time.time()),
            'coord_type_input': 'wgs84'
        })
        return result

    def post(self, url, data):
        res = requests.post(url, data=data)
        return res.json()

    def get(self, url, data):
        res = requests.get(url, params=data)
        return res.json()