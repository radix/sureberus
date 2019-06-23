"""
Functions for converting a Sureberus schema into a list of instructions.
"""


from .instructions import AddToDefaultRegistry, AddToSchemaRegistry, CheckAllowList, CheckFields, CheckType


def compile(schema):
    return list(_compile(schema))


def _compile(schema):
    if "default_registry" in schema:
        yield AddToDefaultRegistry(schema["default_registry"])
    if "registry" in schema:
        registry = {k: compile(v) for k, v in schema["registry"].items()}
        yield AddToSchemaRegistry(registry)
    if "type" in schema:
        yield CheckType(schema["type"])
    if "allowed" in schema:
        yield CheckAllowList(schema["allowed"])
    if "fields" in schema:
        fields = {k: compile(v) for k, v in schema["fields"].items()}
        yield CheckFields(fields)
