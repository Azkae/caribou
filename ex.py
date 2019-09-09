import uuid
import caribou

BASE_URLS = {
    "prod": "https://httpbin.org",
    "local": "http://localhost:8080",
}


def _generate_uuid():
    return str(uuid.uuid4())


@caribou.group('api settings')
@caribou.param('target', type=caribou.Choice(list(BASE_URLS.keys())))
@caribou.param('user_id', default='default-user', generator=_generate_uuid)
def api(ctx, target, user_id):
    ctx['base_url'] = BASE_URLS[target]
    ctx['headers'] = {
        'X-UserID': user_id,
    }


@api.route()
@caribou.param('value')
def get_httpbin(ctx, value):
    return caribou.request.post(
        'http://httpbin.org/post',
        json={
            'test_value': value,
            'test_number': 1,
            'test_bool': True,
        }
    )
