"""
Functions for converting a Sureberus schema into a list of instructions.
"""
from copy import deepcopy

import six

from .instructions import AddToDefaultRegistry, AddToModifyContextRegistry, AddToSchemaRegistry, AllowUnknown, BranchWhenTagIs, CheckAllowList, CheckElements, CheckField, CheckType, ModifyContext, SetTagFromKey, SetTagValue
from . import errors as E
from .constants import _marker

def compile(schema):
    return list(_compile(schema))


def _compile(og):
    schema = deepcopy(og)

    # Meta Directives

    if "default_registry" in schema:
        yield AddToDefaultRegistry(schema.pop("default_registry"))
    if "registry" in schema:
        registry = {k: compile(v) for k, v in schema.pop("registry").items()}
        yield AddToSchemaRegistry(registry)

    if "modify_context_registry" in schema:
        yield AddToModifyContextRegistry(schema.pop("modify_context_registry"))

    if "set_tag" in schema:
        set_tag = schema.pop("set_tag")
        if isinstance(set_tag, six.string_types):
            yield SetTagFromKey(set_tag, set_tag)
        elif "key" in set_tag:
            yield SetTagFromKey(set_tag["tag_name"], set_tag["key"])
        elif "value" in set_tag:
            yield SetTagValue(set_tag["tag_name"], set_tag["value"])
    if "modify_context" in schema:
        yield ModifyContext(schema.pop("modify_context"))

    if "allow_unknown" in schema:
        yield AllowUnknown(schema.pop("allow_unknown"))


    if "choose_schema" in schema:
        choose_schema = schema.pop("choose_schema")
        if "when_tag_is" in choose_schema:
            branches = {k: compile(v) for k, v in choose_schema["when_tag_is"]["choices"].items()}
            yield BranchWhenTagIs(choose_schema["when_tag_is"]["tag"], choose_schema["when_tag_is"].get("default_choice", _marker), branches)
    if "elements" in schema:
        yield CheckElements(compile(schema.pop("elements")))
    if "allowed" in schema:
        yield CheckAllowList(schema.pop("allowed"))
    if "fields" in schema:
        for k, v in schema.pop("fields").items():
            required = v.pop("required", False)
            default = v.pop("default", _marker)
            # todo: default_setter, rename
            yield CheckField(k, compile(v), required=required, default=default)
    if "type" in schema:
        yield CheckType(schema.pop("type"))

    if "schema" in schema:
        subschema = schema.pop("schema")
        try:
            instructions = compile(subschema)
            yield CheckElements(instructions)
        except E.SchemaError:
            for x in compile({"fields": subschema}):
                yield x



    if "required" in schema:
        # We put `required` in places where it doesn't necessarily make sense...
        # Just ignore it.
        schema.pop("required")

    if schema:
        raise E.UnknownSchemaDirectives(schema)
