import uuid
import caribou

BASE_URLS = {
    "prod": "https://prod.example.com",
    "staging": "https://staging.example.com",
    "local": "http://localhost:8080",
}


def _generate_uuid():
    return str(uuid.uuid4())


@caribou.group('spot api')
@caribou.param('target', cls=caribou.Choice(list(BASE_URLS.keys())))
@caribou.param('user_id', default='default-user', generator=_generate_uuid)
def group(ctx, target, user_id):
    ctx['base_url'] = BASE_URLS[target]
    ctx['headers'] = {
        'X-UserID': user_id,
    }


@group.route()
@caribou.param('pet_id')
def get_pet(ctx, pet_id):
    return caribou.request.get(
        ctx['base_url'] + '/v1/pet/' + pet_id,
        headers=ctx['headers']
    )


@group.route()
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
    return caribou.request.get(
        'http://httpbin.org',
        headers={
            'X-Test': test_header
        }
    )
