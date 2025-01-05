from inspect import signature
from typing import Callable, get_type_hints

from pydantic import TypeAdapter


def callable_params_as_json_schema(func: Callable) -> dict:
    type_hints = get_type_hints(func)
    sig = signature(func)

    properties = {
        param: TypeAdapter(typ).json_schema()
        for param, typ in type_hints.items()
        if param != "return"
    }

    defs = {}
    for schema in properties.values():
        if "$defs" in schema:
            defs.update(schema["$defs"])

    required = [
        param_name
        for param_name, param in sig.parameters.items()
        if param.default == param.empty
    ]

    schema = dict(type="object")
    if properties:
        schema["properties"] = properties
    if defs:
        schema["$defs"] = defs
    if required:
        schema["required"] = required

    return schema
