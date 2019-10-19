from typing import NamedTuple, Callable, Union, List as TList


class Choice(NamedTuple):
    options: TList[str]

    def process_value(self, value):
        return value


class List(NamedTuple):
    separator: str = ','

    def process_value(self, value):
        if value.strip() == '':
            return []
        return value.split(',')


class Request(NamedTuple):
    url: str
    method: str
    params: dict = None
    headers: dict = None
    json: dict = None


class Parameter(NamedTuple):
    name: str
    default: str = None
    required: bool = True
    generator: Callable[[], str] = None
    type: Union[Choice, List] = None

    def storage_path(self, prefix):
        return '%s.param.%s' % (prefix, self.name)

    def process_value(self, value):
        if self.type is None:
            return value
        return self.type.process_value(value)


class Route:
    def __init__(self, func, group=None):
        from .loader import register_route
        self.group = group
        self.func = func
        parameters = getattr(func, '__caribou_params__', [])
        self.parameters = list(reversed(parameters))

        register_route(self)

    @property
    def storage_prefix(self):
        return 'routes.%s' % self.func.__name__

    @property
    def name(self):
        return self.func.__name__

    @property
    def display_name(self):
        name = self.func.__name__.split('_')
        if name[0] in ('get', 'post'):
            name[0] = name[0].upper()
        return ' '.join(name)

    def __repr__(self):
        return 'Route(group={}, parameters={})'.format(
            self.group, self.parameters
        )

    def get_request(self, group_values, route_values):
        ctx = {}
        if self.group:
            self.group(ctx, **group_values)
        return self(ctx, **route_values)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class Group:
    def __init__(self, func, name):
        self.func = func
        self.name = name
        parameters = getattr(func, '__caribou_params__', [])
        self.parameters = list(reversed(parameters))

    @property
    def storage_prefix(self):
        return 'groups.%s' % self.func.__name__

    def __repr__(self):
        return 'Group(parameters={})'.format(
            self.parameters
        )

    def route(self):
        def decorator(func):
            return Route(func, group=self)
        return decorator

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)
