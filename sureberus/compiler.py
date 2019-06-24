"""
Functions for converting a Sureberus schema into a list of instructions.
"""
from copy import deepcopy

from .instructions import AddToDefaultRegistry, AddToSchemaRegistry, AllowUnknown, CheckAllowList, CheckField, CheckType
from . import errors as E

def compile(schema):
    return list(_compile(schema))


def _compile(og):
    schema = deepcopy(og)
    if "allow_unknown" in schema:
        yield AllowUnknown(schema.pop("allow_unknown"))
    if "default_registry" in schema:
        yield AddToDefaultRegistry(schema.pop("default_registry"))
    if "registry" in schema:
        registry = {k: compile(v) for k, v in schema.pop("registry").items()}
        yield AddToSchemaRegistry(registry)
    if "type" in schema:
        yield CheckType(schema.pop("type"))
    if "allowed" in schema:
        yield CheckAllowList(schema.pop("allowed"))
    if "fields" in schema:
        fields = {}
        required_fields = []
        for k, v in schema.pop("fields").items():
            required = v.pop("required", False)
            # todo: default, default_setter, rename
            yield CheckField(k, compile(v), required)
    if "elements" in schema:
        yield CheckElements(compile(schema["elements"]))

    if "schema" in schema:
        try:
            instructions = compile(schema["schema"])
            yield CheckElements(instructions)
        except E.SchemaError:
            for x in compile({"fields": schema["schema"]}):
                yield x



    if "required" in schema:
        # We put `required` in places where it doesn't necessarily make sense...
        # Just ignore it.
        schema.pop("required")

    if schema:
        raise E.UnknownSchemaDirectives(schema)
