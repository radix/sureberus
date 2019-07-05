"""
Functions for converting a Sureberus schema into a list of instructions.
"""
from copy import deepcopy
import warnings

import six

from . import instructions as I
from . import errors as E, INIT_CONTEXT
from .constants import _marker


def compile(schema, context=None):
    """Create a Transformer from a schema definition."""
    if context is None:
        context = INIT_CONTEXT
    schema = deepcopy(schema)
    required = schema.pop("required", False)
    default = schema.pop("default", _marker)
    default_setter = schema.pop("default_setter", None)
    rename = schema.pop("rename", None)
    excludes = schema.pop("excludes", [])
    if not isinstance(excludes, list):
        excludes = [excludes]

    return I.Transformer(
        list(_compile(schema, context)),
        required=required,
        default=default,
        default_setter=default_setter,
        rename=rename,
        excludes=excludes,
    )


def _compile(og, ctx):
    schema = deepcopy(og)

    # Meta Directives

    if "default_registry" in schema:
        yield I.AddToDefaultRegistry(schema.pop("default_registry"))

    if "validator_registry" in schema:
        validators = schema.pop("validator_registry")
        ctx = ctx.register_validators(validators)
        yield I.AddToValidatorRegistry(validators)

    if "coerce_registry" in schema:
        coerce_registry = schema.pop("coerce_registry")
        ctx = ctx.register_coerces(coerce_registry)
        yield I.AddToCoerceRegistry(coerce_registry)

    if "registry" in schema:
        registry = {k: compile(v, ctx) for k, v in schema.pop("registry").items()}
        ctx = ctx.register_schemas(registry)
        yield I.AddToSchemaRegistry(registry)

    if "modify_context_registry" in schema:
        yield I.AddToModifyContextRegistry(schema.pop("modify_context_registry"))

    if "set_tag" in schema:
        set_tag = schema.pop("set_tag")
        if isinstance(set_tag, six.string_types):
            yield I.SetTagFromKey(set_tag, set_tag)
        elif "key" in set_tag:
            yield I.SetTagFromKey(set_tag["tag_name"], set_tag["key"])
        elif "value" in set_tag:
            yield I.SetTagValue(set_tag["tag_name"], set_tag["value"])
    if "modify_context" in schema:
        yield I.ModifyContext(schema.pop("modify_context"))

    if "allow_unknown" in schema:
        yield I.AllowUnknown(schema.pop("allow_unknown"))

    if "nullable" in schema:
        if schema.pop("nullable") is True:
            yield I.SkipIfNone()

    if "coerce" in schema:
        coerce = ctx.resolve_coerce(schema.pop("coerce"))
        yield I.Coerce(coerce)

    if "type" in schema:
        yield I.CheckType(schema.pop("type"))

    if "when_key_exists" in schema:
        yield _compile_when_key_exists(schema.pop("when_key_exists"), ctx)

    if "when_key_is" in schema:
        yield _compile_when_key_is(
            schema.pop("when_key_is"),
            schema.pop("fields", schema.pop("schema", None)),
            ctx,
        )

    if "choose_schema" in schema:
        if "when_key_exists" in schema["choose_schema"]:
            yield _compile_when_key_exists(
                schema.pop("choose_schema")["when_key_exists"], ctx
            )
        elif "when_key_is" in schema["choose_schema"]:
            yield _compile_when_key_is(
                schema.pop("choose_schema")["when_key_is"],
                schema.pop("fields", schema.pop("schema", None)),
                ctx,
            )
        elif "when_tag_is" in schema["choose_schema"]:
            choose_schema = schema.pop("choose_schema")
            branches = {
                k: compile(v, ctx)
                for k, v in choose_schema["when_tag_is"]["choices"].items()
            }
            yield I.BranchWhenTagIs(
                choose_schema["when_tag_is"]["tag"],
                choose_schema["when_tag_is"].get("default_choice", _marker),
                branches,
            )
        elif "function" in schema["choose_schema"]:
            choose_schema = schema.pop("choose_schema")
            yield I.ApplyDynamicSchema(choose_schema["function"])

    if "schema_ref" in schema:
        schema_ref = schema.pop("schema_ref")
        transformer = ctx.find_schema(schema_ref)
        yield I.ApplyDynamicSchema(lambda v, c: transformer)

    if "oneof" in schema:
        yield I.OneOf([_compile_or_find(x, ctx) for x in schema.pop("oneof")])

    if "anyof" in schema:
        anyof = schema.pop("anyof")
        yield I.AnyOf([_compile_or_find(x, ctx) for x in anyof])

    if "min" in schema or "max" in schema:
        yield I.CheckBounds(min=schema.pop("min"), max=schema.pop("max"))
    if "maxlength" in schema:
        yield I.CheckLength(maxlength=schema.pop("maxlength"))
    if "regex" in schema:
        yield I.CheckRegex(schema.pop("regex"))

    if "elements" in schema:
        yield I.CheckElements(_compile_or_find(schema.pop("elements"), ctx))
    if "allowed" in schema:
        yield I.CheckAllowList(schema.pop("allowed"))
    if "fields" in schema:
        transformers = {
            k: _compile_or_find(v, ctx) for k, v in schema.pop("fields").items()
        }
        yield I.CheckFields(transformers)

    if "keyschema" in schema:
        yield I.CheckKeys(_compile_or_find(schema.pop("keyschema"), ctx))
    if "valueschema" in schema:
        yield I.CheckValues(_compile_or_find(schema.pop("valueschema"), ctx))

    if "schema" in schema:
        warnings.warn(
            "Please use 'fields' or 'elements' instead of 'schema'.", DeprecationWarning
        )
        subschema = schema.pop("schema")
        try:
            instructions = _compile_or_find({"fields": subschema}, ctx).instructions
        except Exception:
            instructions = _compile_or_find({"elements": subschema}, ctx).instructions
        else:
            # It could be compiled as a fields... but can it ALSO compile as elements?
            # If so, let's do some heuristics...
            try:
                elements_instructions = _compile_or_find(
                    {"elements": subschema}, ctx
                ).instructions
            except Exception:
                pass
                # ok, forget about it
            else:
                if "type" in subschema:
                    # let's assume it's an ELEMENTS.
                    instructions = elements_instructions

        for i in instructions:
            yield i

    if "validator" in schema:
        validator = ctx.resolve_validator(schema.pop("validator"))
        yield I.CustomValidator(validator)

    if "coerce_post" in schema:
        coerce_post = ctx.resolve_coerce(schema.pop("coerce_post"))
        yield I.Coerce(coerce_post)

    if schema:
        raise E.UnknownSchemaDirectives(schema)


def _compile_when_key_exists(directive, ctx):
    branches = {k: _compile_or_find(v, ctx) for k, v in directive.items()}
    return I.BranchWhenKeyExists(branches)


def _compile_when_key_is(directive, parent_fields, ctx):
    # We need to do various tricky things here
    # 1. merge in "fields" schemas in the choice-schema with "fields" in the current schema.
    #    The only reason we need to do this is because CheckFields explicitly checks if there are
    #    any EXTRA fields. We could maybe simplify this if we instead added another instruction
    #    called "CheckExcludedFields".
    # 2. implicitly add the key to the CheckFields that is generated
    key = directive["key"]
    choice_keys = list(directive["choices"].keys())
    for choice_key, choice_schema in directive["choices"].items():
        # schema usage here is deprecated
        fields = choice_schema.pop("fields", choice_schema.pop("schema", None))
        if fields is not None and key not in fields:
            fields[key] = {"allowed": choice_keys}
        new_fields = parent_fields.copy() if parent_fields is not None else {}
        new_fields.update(fields)
        choice_schema["fields"] = new_fields
    branches = {k: _compile_or_find(v, ctx) for k, v in directive["choices"].items()}
    return I.BranchWhenKeyIs(key, directive.get("default_choice", _marker), branches)


def _compile_or_find(schema, ctx):
    if isinstance(schema, six.string_types):
        # When compiling a *reference* to a schema, it may not actually be fully
        # defined yet! While schema-references must be purely lexical, the
        # situation in which this arises is recursive schemas.
        # E.g., {"registry": {"foo": {"fields": {"nested": "foo"}}}}
        try:
            return ctx.find_schema(schema)
        except KeyError:
            return I.SchemaReference(schema)
    else:
        return compile(schema, ctx)
