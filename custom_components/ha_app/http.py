import time, json
from homeassistant.components.http import HomeAssistantView
from .manifest import manifest

class HttpView(HomeAssistantView):

    url = "/api/haapp"
    name = "api:haapp"
    requires_auth = False

    async def post(self, request):
        hass = request.app["hass"]

        body = await request.json()
        print(body)
        push_token = body.get('push_token')
        title = body.get('title')
        message = body.get('message')

        result = {
            'title': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) if title is None else title,
            'message': message,
        }

        hass.loop.create_task(hass.services.async_call('persistent_notification', 'create', {
                    'title': message,
                    'message': json.dumps(result),
                    'notification_id': f'ha_app{result["id"]}'
                }))
        return self.json_message("推送成功", status_code=201)