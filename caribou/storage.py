GLOBAL_STORAGE = {}


def save_parameter(prefix, parameter, value):
    global GLOBAL_STORAGE
    GLOBAL_STORAGE[parameter.storage_path(prefix)] = value


def load_parameter(prefix, parameter):
    global GLOBAL_STORAGE
    return GLOBAL_STORAGE.get(parameter.storage_path(prefix))


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
