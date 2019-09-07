from .models import Group, Route, Parameter, Request


class RequestApi():
    def get(self, *args, **kwargs):
        return Request(method='GET', *args, **kwargs)

    def post(self, *args, **kwargs):
        return Request(method='POST', *args, **kwargs)


request = RequestApi()


def group(name):
    def decorator(func):
        return Group(func, name=name)
    return decorator


def route():
    def decorator(func):
        return Route(func)
    return decorator


def param(*args, **kwargs):
    def decorator(func):
        if not hasattr(func, '__caribou_params__'):
            func.__caribou_params__ = []
        func.__caribou_params__.append(Parameter(*args, **kwargs))
        return func
    return decorator
