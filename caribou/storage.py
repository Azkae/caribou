import os
import json

VERSION = 1


class MissingParameter(Exception):
    def __init__(self, parameter_name):
        self.parameter_name = parameter_name


GLOBAL_STORAGE = {}


def save_parameter(prefix, parameter, value):
    global GLOBAL_STORAGE
    GLOBAL_STORAGE[parameter.storage_path(prefix)] = value


def load_parameter(prefix, parameter):
    global GLOBAL_STORAGE
    return GLOBAL_STORAGE.get(parameter.storage_path(prefix))


def save_request_result(route, value):
    global GLOBAL_STORAGE
    GLOBAL_STORAGE['%s.result' % route.storage_prefix] = value


def load_request_result(route):
    global GLOBAL_STORAGE
    return GLOBAL_STORAGE.get('%s.result' % route.storage_prefix)


def get_parameter_values(prefix, parameters):
    values = {}
    for param in parameters:
        storage_path = param.storage_path(prefix)

        value = GLOBAL_STORAGE.get(storage_path)

        if value in (None, ''):
            value = param.default

        if param.required and value in (None, ''):
            raise MissingParameter(param.name)

        values[param.name] = value
    return values


def get_parameter_values_for_route(route):
    if route.group is not None:
        group_values = get_parameter_values(
            route.group.storage_prefix,
            route.group.parameters
        )
    else:
        group_values = {}

    route_values = get_parameter_values(
        route.storage_prefix,
        route.parameters
    )
    return group_values, route_values


# XXX: cleanup
def load_storage():
    global GLOBAL_STORAGE
    if os.path.exists('/tmp/caribou'):
        with open('/tmp/caribou') as f:
            data = json.load(f)
            if data['version'] != VERSION:
                return
            GLOBAL_STORAGE = data['data']


def persist_storage():
    with open('/tmp/caribou', 'w') as f:
        json.dump({
            'version': VERSION,
            'data': GLOBAL_STORAGE
        }, f)
