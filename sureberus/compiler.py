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
    AnyOf,
    ApplyDynamicSchema,
    BranchWhenTagIs,
    CheckAllowList,
    CheckElements,
    CheckField,
    CheckType,
    Coerce,
    ModifyContext,
    SetTagFromKey,
    SetTagValue,
    Transformer,
    SchemaReference,
    SkipIfNone,
)
from . import errors as E, INIT_CONTEXT
from .constants import _marker


def compile(schema, context=None):
    """Create a Transformer from a schema definition."""
    if context is None:
        context = INIT_CONTEXT
    schema = deepcopy(schema)
    required = schema.pop("required", False)
    default = schema.pop("default", _marker)
    rename = schema.pop("rename", None)
    return Transformer(
        list(_compile(schema, context)),
        required=required,
        default=default,
        rename=rename,
    )


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

    if "nullable" in schema:
        del schema["nullable"]
        yield SkipIfNone()

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
    if "schema_ref" in schema:
        schema_ref = schema.pop("schema_ref")
        transformer = ctx.find_schema(schema_ref)
        yield ApplyDynamicSchema(lambda v, c: transformer)
    if "anyof" in schema:
        anyof = schema.pop("anyof")
        yield AnyOf([_compile_or_find(x, ctx) for x in anyof])

    if "coerce" in schema:
        yield Coerce(schema.pop("coerce"))
    if "elements" in schema:
        yield CheckElements(_compile_or_find(schema.pop("elements"), ctx))
    if "allowed" in schema:
        yield CheckAllowList(schema.pop("allowed"))
    if "fields" in schema:
        for k, v in schema.pop("fields").items():
            field_schema = _compile_or_find(v, ctx)
            yield CheckField(k, field_schema)
    if "type" in schema:
        yield CheckType(schema.pop("type"))

    if "schema" in schema:
        subschema = schema.pop("schema")
        try:
            instructions = _compile_or_find(subschema, ctx)
            yield CheckElements(instructions)
        except E.SchemaError:
            for x in _compile_or_find({"fields": subschema}, ctx).instructions:
                yield x


    if "coerce_post" in schema:
        yield Coerce(schema.pop("coerce_post"))

    if schema:
        raise E.UnknownSchemaDirectives(schema)


def _compile_or_find(schema, ctx):
    if isinstance(schema, six.string_types):
        # When compiling a *reference* to a schema, it may not actually be fully
        # defined yet! While schema-references must be purely lexical, the
        # situation in which this arises is recursive schemas.
        # E.g., {"registry": {"foo": {"fields": {"nested": "foo"}}}}
        try:
            return ctx.find_schema(schema)
        except KeyError:
            return SchemaReference(schema)
    else:
        return compile(schema, ctx)

