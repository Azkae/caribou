from typing import Callable, Union, Optional
from dataclasses import dataclass


@dataclass
class Choice:
    options: list[str]

    def process_value(self, value):
        return value


@dataclass
class List:
    separator: str = ","

    def process_value(self, value):
        if value.strip() == "":
            return []
        return value.split(",")


@dataclass
class TextField:
    def process_value(self, value):
        return value


@dataclass
class Request:
    url: str
    method: str
    params: Optional[dict] = None
    headers: Optional[dict] = None
    json: Optional[dict] = None


@dataclass
class Parameter:
    name: str
    default: Optional[str] = None
    required: bool = True
    generator: Optional[Callable[[], str]] = None
    type: Union[Choice, List, None] = None
    id: Optional[str] = None

    def storage_path(self, prefix):
        if self.id is not None:
            return "globals.param.%s" % self.id
        else:
            return "%s.param.%s" % (prefix, self.name)

    def process_value(self, value):
        if self.type is None:
            return value
        return self.type.process_value(value)


class Route:
    def __init__(self, func, group=None):
        from .loader import register_route

        self.group = group
        self.func = func
        parameters = getattr(func, "__caribou_params__", [])
        self.parameters = list(reversed(parameters))

        register_route(self)

    @property
    def storage_prefix(self):
        return "routes.%s" % self.func.__name__

    @property
    def name(self):
        return self.func.__name__

    KEYWORDS = ("get", "post")

    @property
    def raw_display_name(self):
        name_items = self.func.__name__.split("_")
        name_items = [
            name.upper() if name in self.KEYWORDS else name for name in name_items
        ]
        return " ".join(name_items)

    def _style_word(self, name):
        if name == "get":
            return '<span style="color:#25A86B">GET</span>'
        elif name == "post":
            return '<span style="color:#FDA60A">POST</span>'
        else:
            return '<span style="color:#FFFFFF">%s</span>' % name

    @property
    def display_name(self):
        name_items = self.func.__name__.split("_")
        name_items = [self._style_word(name) for name in name_items]
        return " ".join(name_items)

    def __repr__(self):
        return "Route(group={}, parameters={})".format(self.group, self.parameters)

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
        parameters = getattr(func, "__caribou_params__", [])
        self.parameters = list(reversed(parameters))

    @property
    def storage_prefix(self):
        return "groups.%s" % self.func.__name__

    def __repr__(self):
        return "Group(parameters={})".format(self.parameters)

    def route(self):
        def decorator(func):
            return Route(func, group=self)

        return decorator

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class Generator:
    def __init__(self, func) -> None:
        self.func = func


class Shared:
    def __init__(self, id: str) -> None:
        self.id = id
