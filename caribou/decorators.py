from .models import Group, Route, Request


class RequestApi:
    def get(self, *args, **kwargs):
        return Request(method="GET", *args, **kwargs)

    def post(self, *args, **kwargs):
        return Request(method="POST", *args, **kwargs)

    def delete(self, *args, **kwargs):
        return Request(method="DELETE", *args, **kwargs)

    def patch(self, *args, **kwargs):
        return Request(method="PATCH", *args, **kwargs)

    def put(self, *args, **kwargs):
        return Request(method="PUT", *args, **kwargs)


request = RequestApi()


def group(name):
    def decorator(func):
        return Group(func, name=name)

    return decorator


def route():
    def decorator(func):
        return Route(func)

    return decorator


# def param(*args, **kwargs):
#     def decorator(func):
#         if not hasattr(func, "__caribou_params__"):
#             func.__caribou_params__ = []
#         func.__caribou_params__.append(Parameter(*args, **kwargs))
#         return func

#     return decorator
