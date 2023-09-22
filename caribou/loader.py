import os
import importlib.util
from contextlib import contextmanager
from threading import Lock

from caribou.models import Route

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
