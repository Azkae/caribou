import enum
import os
import inspect
import typing
import importlib.util
from contextlib import contextmanager
from threading import Lock
from typing import Callable, get_type_hints
from typing_inspect import is_optional_type

from caribou.models import Choice, Generator, List, Parameter, Route, Shared

hook_enabled = False
routes = []
lock = Lock()


@contextmanager
def hook_context():
    global routes, hook_enabled
    try:
        with lock:
            assert not hook_enabled
            routes = []
            hook_enabled = True

        yield
    finally:
        with lock:
            hook_enabled = False


def register_route(route: Route) -> None:
    global routes
    with lock:
        if hook_enabled:
            routes.append(route)


def load_file(file_path: str) -> list[Route]:
    if not os.path.exists(file_path):
        raise Exception("File not found: %s" % file_path)

    spec = importlib.util.spec_from_file_location("routes", file_path)
    if spec is None or spec.loader is None:
        raise Exception("Could not load spec from routes")
    route_modules = importlib.util.module_from_spec(spec)

    with hook_context():
        spec.loader.exec_module(route_modules)
        return list(routes)


def get_params_from_func(func: Callable) -> list[Parameter]:
    type_hints = get_type_hints(func)
    signature = inspect.signature(func)
    params = []
    for param_name, param_type in type_hints.items():
        if param_name == "return":
            continue
        default = signature.parameters[param_name].default
        if default == inspect.Parameter.empty:
            default = None
        if isinstance(default, enum.Enum):
            default = default.value

        annotation = signature.parameters[param_name].annotation
        metadatas = getattr(annotation, "__metadata__", [])
        generator = None
        id = None

        for metadata in metadatas:
            match metadata:
                case Generator():
                    generator = metadata.func
                case Shared():
                    id = metadata.id

        type = None
        if param_type in (list, typing.List):
            type = List()
        elif inspect.isclass(param_type) and issubclass(param_type, enum.Enum):
            type = Choice([e.value for e in param_type])

        params.append(
            Parameter(
                name=param_name,
                default=default,
                required=not is_optional_type(param_type),
                generator=generator,
                id=id,
                type=type,
            )
        )
    return params
