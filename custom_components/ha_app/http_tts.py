from homeassistant.components.http import HomeAssistantView
from .utils import call_service, mkdir

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
            call_service(hass, 'media_player.play_media', {
                        'media_content_type': 'audio/mpeg',
                        'media_content_id': file,
                        'entity_id': entities
                    })
            return self.json_message("推送成功")

        return self.json_message("参数异常", status_code=500)

    async def async_write_file(self, hass, file):
        filename = file.filename
        size = 0
        path = hass.config.media_dirs.get('local', hass.config.path("media")) + '/ha_app'
        mkdir(path)
        with open(f'{path}/{filename}', 'wb') as f:
            while True:
                chunk = await file.read_chunk()  # 默认是8192个字节。
                if not chunk:
                    break
                size += len(chunk)
                f.write(chunk)

        return f'media-source://media_source/local/ha_app/{filename}'