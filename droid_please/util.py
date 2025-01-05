from inspect import signature
from typing import Callable, get_type_hints

from pydantic import TypeAdapter


def callable_params_as_json_schema(func: Callable) -> dict:
    type_hints = get_type_hints(func)
    sig = signature(func)

    params = {
        param: TypeAdapter(typ).json_schema()
        for param, typ in type_hints.items()
        if param != "return"
    }

    required = [
        param_name
        for param_name, param in sig.parameters.items()
        if param.default == param.empty
    ]

    return dict(type="object", properties=params, required=required)
