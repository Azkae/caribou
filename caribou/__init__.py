from .decorators import group, param, route, request
from .models import Route, Parameter, Group, Choice, List
from .exceptions import CaribouException
from packaging import version

__version__ = '0.9'


def require_version(required_version):
    caribou_version = version.parse(__version__)
    required_version = version.parse(required_version)

    if caribou_version < required_version:
        raise CaribouException(
            'Outdated Caribou version.\n\nUpdate here: https://github.com/Azkae/caribou/releases'.format(version=required_version)
        )
