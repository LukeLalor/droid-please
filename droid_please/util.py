from inspect import signature
from typing import Callable, get_type_hints, Dict

import jsonschema
from pydantic import TypeAdapter


class SchemaWrapper:
    schema: dict

    def __init__(self, schema: dict, type_adapters=None):
        self.schema = schema
        self._type_adapters: Dict[str, TypeAdapter] = type_adapters or {}

    def parse(self, data: dict):
        jsonschema.validate(instance=data, schema=self.schema)
        return {
            k: self._type_adapters[k].validate_python(v)
            for k, v in data.items()
            if k in self._type_adapters
        }


def callable_params_as_json_schema(func: Callable) -> SchemaWrapper:
    type_hints = get_type_hints(func)
    sig = signature(func)

    adapters = {param: TypeAdapter(typ) for param, typ in type_hints.items() if param != "return"}

    properties = {p: a.json_schema() for p, a in adapters.items()}

    defs = {}
    for schema in properties.values():
        if "$defs" in schema:
            defs.update(schema["$defs"])

    required = [
        param_name for param_name, param in sig.parameters.items() if param.default == param.empty
    ]

    schema = dict(type="object")
    if properties:
        schema["properties"] = properties
    if defs:
        schema["$defs"] = defs
    if required:
        schema["required"] = required

    return SchemaWrapper(schema, adapters)
