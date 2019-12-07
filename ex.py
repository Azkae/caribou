import uuid
import caribou

BASE_URLS = {
    "httpbin.org": "https://httpbin.org",
    "localhost": "http://localhost:8080",
}


def _generate_uuid():
    return str(uuid.uuid4())


@caribou.group('api settings')
@caribou.param('target', type=caribou.Choice(list(BASE_URLS.keys())))
def api(ctx, target):
    ctx['base_url'] = BASE_URLS[target]


@api.route()
@caribou.param('value')
@caribou.param('random_value', generator=_generate_uuid)
def get_httpbin(ctx, value, random_value):
    return caribou.request.post(
        ctx['base_url'] + '/post',
        json={
            'value': value,
            'random_value': random_value,
        }
    )
