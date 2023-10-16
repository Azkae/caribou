import os
import json
from pathlib import Path
from typing import Any, Optional

from caribou.models import Parameter, Route
from .exceptions import MissingParameter

VERSION = 1
DATA_PATH = Path(os.path.expanduser("~/.caribou/data"))

GLOBAL_STORAGE = {}
TEMPORARY_STORAGE = {}


def load_setting(name: str) -> Optional[str]:
    return GLOBAL_STORAGE.get("settings.%s" % name)


def save_setting(name: str, value: str) -> None:
    GLOBAL_STORAGE["settings.%s" % name] = value


def save_parameter(prefix: str, parameter: Parameter, value: str) -> None:
    GLOBAL_STORAGE[parameter.storage_path(prefix)] = value


def load_parameter(prefix: str, parameter: Parameter) -> Optional[str]:
    return GLOBAL_STORAGE.get(parameter.storage_path(prefix))


def save_request_result(route: Route, value: str) -> None:
    TEMPORARY_STORAGE["%s.result" % route.storage_prefix] = value


def load_request_result(route: Route) -> Optional[str]:
    return TEMPORARY_STORAGE.get("%s.result" % route.storage_prefix)


def get_parameter_values(prefix: str, parameters: list[Parameter]) -> dict[str, Any]:
    values = {}
    for param in parameters:
        storage_path = param.storage_path(prefix)

        value = GLOBAL_STORAGE.get(storage_path)

        if value in (None, ""):
            value = param.default
        else:
            value = param.process_value(value)

        if param.required and value in (None, ""):
            raise MissingParameter(param.name)

        values[param.name] = value
    return values


def get_parameter_values_for_route(
    route: Route,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if route.group is not None:
        group_values = get_parameter_values(
            route.group.storage_prefix, route.group.parameters
        )
    else:
        group_values = {}

    route_values = get_parameter_values(route.storage_prefix, route.parameters)
    return group_values, route_values


# XXX: cleanup
def load_storage() -> None:
    global GLOBAL_STORAGE
    if DATA_PATH.exists():
        with DATA_PATH.open() as f:
            data = json.load(f)
            if data["version"] != VERSION:
                return
            GLOBAL_STORAGE = data["data"]


def persist_storage() -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w") as f:
        json.dump({"version": VERSION, "data": GLOBAL_STORAGE}, f)
