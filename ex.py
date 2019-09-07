import uuid
import caribou

BASE_URLS = {
    "prod": "https://prod.example.com",
    "staging": "https://staging.example.com",
    "local": "http://localhost:8080",
}


def _generate_uuid():
    return str(uuid.uuid4())


@caribou.group('api settings')
@caribou.param('target', cls=caribou.Choice(list(BASE_URLS.keys())))
@caribou.param('user_id', default='default-user', generator=_generate_uuid)
def api(ctx, target, user_id):
    ctx['base_url'] = BASE_URLS[target]
    ctx['headers'] = {
        'X-UserID': user_id,
    }


@api.route()
@caribou.param('pet_id')
def get_pet(ctx, pet_id):
    return caribou.request.get(
        ctx['base_url'] + '/v1/pet/' + pet_id,
        headers=ctx['headers']
    )


@api.route()
@caribou.param('pet_id', default='1')
def post_pet(ctx, pet_id):
    return caribou.request.post(
        ctx['base_url'] + '/v1/pet/' + pet_id,
        headers=ctx['headers'],
        json={
            'hello': 'kitty'
        }
    )


@caribou.route()
@caribou.param('test_header')
def get_httpbin(ctx, test_header):
    return caribou.request.post(
        'http://httpbin.org/post',
        json={
            'test': test_header,
            'test_number': 1,
            'test_bool': True,
        }
    )
