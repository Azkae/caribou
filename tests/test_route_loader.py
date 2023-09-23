import enum
import random
from typing import Generic, Optional, Annotated

from caribou.loader import get_params_from_func
from caribou.models import Choice, Generator, Parameter, Shared


class SampleEnum(enum.Enum):
    FIRST = "first"
    SECOND = "second"


def _generate():
    return random.choice(["a", "b"])


def route(
    a: str,
    b: Optional[str] = "12",
    *,
    c: str | None,
    d: Annotated[str, Shared("test"), Generator(_generate)],
    e: SampleEnum = SampleEnum.FIRST,
):
    pass


def test_load_route():
    params = get_params_from_func(route)
    assert params == [
        Parameter(
            name="a",
            default=None,
            required=True,
            generator=None,
            id=None,
            type=None,
        ),
        Parameter(
            name="b",
            default="12",
            required=False,
            generator=None,
            id=None,
            type=None,
        ),
        Parameter(
            name="c",
            default=None,
            required=False,
            generator=None,
            id=None,
            type=None,
        ),
        Parameter(
            name="d",
            default=None,
            required=True,
            generator=_generate,
            id="test",
            type=None,
        ),
        Parameter(
            name="e",
            default="first",
            required=True,
            generator=None,
            id=None,
            type=Choice(["first", "second"]),
        ),
    ]
