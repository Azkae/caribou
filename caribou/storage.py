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

        if value is None or value == '':
            if param.required:
                raise Exception('Missing parameter: %s' % param.name)
            values[param.name] = param.default
        else:
            values[param.name] = GLOBAL_STORAGE[storage_path]
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
