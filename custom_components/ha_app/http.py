import time, json
from homeassistant.components.http import HomeAssistantView
from .manifest import manifest

class HttpView(HomeAssistantView):

    url = "/api/haapp"
    name = "api:haapp"
    requires_auth = False
    # 计数器
    count = 0

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
        dev_id = push_token
        notification_id = f'{dev_id}{self.count}'
        self.count = self.count + 1
        if self.count > 50:
            self.count = 0

        hass.loop.create_task(hass.services.async_call('persistent_notification', 'create', {
                    'title': message,
                    'message': json.dumps(result),
                    'notification_id': notification_id
                }))

        result['id'] = notification_id
        hass.bus.fire(dev_id, result)

        return self.json_message("推送成功", status_code=201)