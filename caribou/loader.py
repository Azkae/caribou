import importlib.util
from contextlib import contextmanager
from threading import Lock

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


def register_route(route):
    global routes
    with lock:
        if hook_enabled:
            routes.append(route)


def load_file(file_path):
    spec = importlib.util.spec_from_file_location("routes", file_path)
    route_modules = importlib.util.module_from_spec(spec)

    with hook_context():
        spec.loader.exec_module(route_modules)
        return list(routes)
