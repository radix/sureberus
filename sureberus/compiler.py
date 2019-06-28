"""
Functions for converting a Sureberus schema into a list of instructions.
"""
from copy import deepcopy

import six

from .instructions import (
    AddToDefaultRegistry,
    AddToModifyContextRegistry,
    AddToSchemaRegistry,
    AllowUnknown,
    ApplyDynamicSchema,
    BranchWhenTagIs,
    CheckAllowList,
    CheckElements,
    CheckField,
    CheckType,
    FieldTransformer,
    ModifyContext,
    SetTagFromKey,
    SetTagValue,
    Transformer,
)
from . import errors as E, INIT_CONTEXT
from .constants import _marker


def compile(schema, context=None):
    """Create a Transformer from a schema definition.

    This might return either an instance of `Transformer` or `FieldTransformer`,
    depending on the presence of field-specific directives such as `required`.
    """
    if context is None:
        context = INIT_CONTEXT
    return Transformer(list(_compile(schema, context)))


def _compile_field(og, ctx):
    schema = deepcopy(og)
    required = schema.pop("required", False)
    default = schema.pop("default", _marker)
    transformer = compile(schema, ctx)
    return FieldTransformer(transformer.instructions, required=required, default=default)


def _compile(og, ctx):
    schema = deepcopy(og)

    # Meta Directives

    if "default_registry" in schema:
        yield AddToDefaultRegistry(schema.pop("default_registry"))
    if "registry" in schema:
        registry = {k: compile(v, ctx) for k, v in schema.pop("registry").items()}
        ctx = ctx.register_schemas(registry)
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
            branches = {
                k: compile(v, ctx)
                for k, v in choose_schema["when_tag_is"]["choices"].items()
            }
            yield BranchWhenTagIs(
                choose_schema["when_tag_is"]["tag"],
                choose_schema["when_tag_is"].get("default_choice", _marker),
                branches,
            )
        elif "function" in choose_schema:
            yield ApplyDynamicSchema(choose_schema["function"])
    if "elements" in schema:
        yield CheckElements(compile(schema.pop("elements"), ctx))
    if "allowed" in schema:
        yield CheckAllowList(schema.pop("allowed"))
    if "fields" in schema:
        for k, v in schema.pop("fields").items():
            if isinstance(v, six.string_types):
                field_schema = ctx.find_schema(v)
                print("[RADIX] looked up schema", v)
            else:
                field_schema = _compile_field(v, ctx)
            yield CheckField(k, field_schema)
    if "type" in schema:
        yield CheckType(schema.pop("type"))

    if "schema" in schema:
        subschema = schema.pop("schema")
        try:
            instructions = compile(subschema, ctx)
            yield CheckElements(instructions)
        except E.SchemaError:
            for x in compile({"fields": subschema}, ctx).instructions:
                yield x

    if "required" in schema:
        # We put `required` in places where it doesn't necessarily make sense...
        # Just ignore it.
        schema.pop("required")

    if schema:
        raise E.UnknownSchemaDirectives(schema)
