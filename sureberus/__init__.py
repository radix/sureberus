from __future__ import print_function

from copy import deepcopy
from inspect import getmembers
import re

import attr
import six

from . import errors as E

__all__ = ["normalize_dict", "normalize_schema"]


@attr.s
class Context(object):
    stack = attr.ib()
    allow_unknown = attr.ib()

    def push_stack(self, x):
        return Context(stack=self.stack + (x,), allow_unknown=self.allow_unknown)

    def set_allow_unknown(self, x):
        return Context(stack=self.stack, allow_unknown=x)


def normalize_dict(dict_schema, value, stack=(), allow_unknown=False):
    ctx = Context(stack=(), allow_unknown=allow_unknown)
    return _normalize_dict(dict_schema, value, ctx)


def normalize_schema(schema, value, stack=(), allow_unknown=False):
    ctx = Context(stack=(), allow_unknown=allow_unknown)
    return _normalize_schema(schema, value, ctx)


def _normalize_dict(dict_schema, value, ctx):
    new_dict = {}
    extra_keys = set(value.keys()) - set(dict_schema.keys())
    if extra_keys:
        if ctx.allow_unknown:
            for k in extra_keys:
                new_dict[k] = value[k]
        else:
            raise E.UnknownFields(value, extra_keys, stack=ctx.stack)
    for key, key_schema in dict_schema.items():
        new_key = key_schema.get("rename", key)
        if key not in value:
            replacement = _get_default(key, key_schema, value, ctx)
            if replacement is not _marker:
                new_dict[new_key] = replacement
            elif key_schema.get("required", False) == True:
                raise E.DictFieldNotFound(key, value=value, stack=ctx.stack)
        if key in value:
            new_dict[new_key] = _normalize_schema(
                key_schema, value[key], ctx.push_stack(key)
            )
            excludes = key_schema.get("excludes", [])
            if not isinstance(excludes, list):
                excludes = [excludes]
            for excluded_field in excludes:
                if excluded_field in value:
                    raise E.DisallowedField(key, excluded_field, ctx.stack)
    return new_dict


def _get_default(key, key_schema, doc, ctx):
    default = key_schema.get("default", _marker)
    if default is not _marker:
        return default
    else:
        default_setter = key_schema.get("default_setter", None)
        if default_setter is not None:
            try:
                return default_setter(doc)
            except Exception as e:
                raise E.DefaultSetterUnexpectedError(key, doc, e, ctx.stack)
    return _marker


_marker = object()

TYPES = {
    "none": type(None),
    "integer": six.integer_types,
    "float": (float,)
    + six.integer_types,  # cerberus documentation lies -- float also includes ints.
    "number": (float,) + six.integer_types,
    "dict": dict,
    "list": list,
    "string": six.string_types,
    "boolean": bool,
}

_directive_count = 0


def directive(directive_name, short_circuit=False):
    def decorator(method):
        global _directive_count
        method.sureberus_directive = {
            "directive": directive_name,
            "short_circuit": short_circuit,
            "order": _directive_count,
            "method": method,
        }
        _directive_count += 1
        return method

    return decorator


class _ShortCircuit(object):
    """
    A marker to indicate that schema directives should stop being processed, and
    a value should immediately be returned.
    """

    def __init__(self, value):
        self.value = value


@attr.s
class Normalizer(object):
    schema = attr.ib()

    @directive("allow_unknown")
    def handle_allow_unknown(self, value, directive_value, ctx):
        return (value, ctx.set_allow_unknown(directive_value))

    @directive("coerce")
    def handle_coerce(self, value, directive_value, ctx):
        try:
            return (directive_value(value), ctx)
        except E.SureError:
            raise
        except Exception as e:
            raise E.CoerceUnexpectedError(value, e, ctx.stack)

    @directive("nullable")
    def handle_nullable(self, value, directive_value, ctx):
        if value is None and directive_value:
            return _ShortCircuit(value)
        return (value, ctx)

    @directive("when_key_is")
    def handle_when_key_is(self, value, directive_value, ctx):
        # At this point, we *need* this thing to be a dict, so we can look up
        # keys. So let's make sure it's a dict.
        self.handle_type(value, "dict", ctx)
        choice_key = directive_value["key"]
        new_schema = deepcopy(self.schema)
        # Putting the "choice key" into the dict schema is not required,
        # since we can figure out exactly which values it should allow based
        # on what's in the `when_key_is`.
        allowed_choices = list(directive_value["choices"].keys())
        if choice_key not in new_schema.setdefault("schema", {}):
            new_schema["schema"][choice_key] = {"allowed": allowed_choices}
        if choice_key not in value:
            raise E.DictFieldNotFound(choice_key, value, ctx.stack)
        chosen_type = value[choice_key]
        if chosen_type not in directive_value["choices"]:
            raise E.DisallowedValue(
                chosen_type, allowed_choices, ctx.push_stack(choice_key).stack
            )
        subschema = directive_value["choices"][chosen_type].copy()
        new_schema["schema"].update(subschema.pop("schema"))
        new_schema.update(subschema)
        del new_schema["when_key_is"]
        return _ShortCircuit(_normalize_schema(new_schema, value, ctx))

    @directive("when_key_exists")
    def handle_when_key_exists(self, value, directive_value, ctx):
        self.handle_type(value, "dict", ctx)
        chosen_type = None
        possible_keys = list(directive_value.keys())
        for key in possible_keys:
            if key in value:
                if chosen_type is not None:
                    raise E.DisallowedField(chosen_type, key, ctx.stack)
                chosen_type = key
        if chosen_type is None:
            raise E.ExpectedOneField(possible_keys, value, ctx.stack)

        new_schema = deepcopy(self.schema)

        subschema = directive_value[chosen_type].copy()
        new_schema.setdefault("schema", {}).update(subschema.pop("schema"))
        new_schema.update(subschema)
        del new_schema["when_key_exists"]
        return _ShortCircuit(_normalize_schema(new_schema, value, ctx))

    @directive("oneof")
    def handle_oneof(self, value, directive_value, ctx):
        return _ShortCircuit(_normalize_multi(self.schema, value, "oneof", ctx))

    @directive("anyof")
    def handle_anyof(self, value, _directive_value, ctx):
        return _ShortCircuit(_normalize_multi(self.schema, value, "anyof", ctx))

    @directive("allowed")
    def handle_allowed(self, value, directive_value, ctx):
        if value not in directive_value:
            raise E.DisallowedValue(value, directive_value, ctx.stack)
        return (value, ctx)

    @directive("type")
    def handle_type(self, value, directive_value, ctx):
        types = TYPES[directive_value]
        if not isinstance(value, types):
            raise E.BadType(value, directive_value, ctx.stack)
        return (value, ctx)

    @directive("maxlength")
    def handle_maxlength(self, value, directive_value, ctx):
        if len(value) > directive_value:
            raise E.MaxLengthExceeded(value, directive_value, ctx.stack)
        return (value, ctx)

    @directive("min")
    def handle_min(self, value, directive_value, ctx):
        if value < directive_value:
            raise E.OutOfBounds(
                value, directive_value, self.schema.get("max"), ctx.stack
            )
        return (value, ctx)

    @directive("max")
    def handle_max(self, value, directive_value, ctx):
        if value > directive_value:
            raise E.OutOfBounds(
                value, self.schema.get("min"), directive_value, ctx.stack
            )
        return (value, ctx)

    @directive("regex")
    def handle_regex(self, value, directive_value, ctx):
        # apparently you can put `regex` even when `type` isn't `string`, and it
        # only actually gets run if the runtime value is a string.
        if isinstance(value, str):
            if not re.match(directive_value, value):
                raise E.RegexMismatch(value, directive_value, ctx.stack)
        return (value, ctx)

    @directive("schema")
    def handle_schema(self, value, directive_value, ctx):
        # The meaning of a `schema` key inside a schema changes based on the
        # type of the *value*. e.g., it is possible to define a schema like
        # `{'schema': {'type': 'integer'}}` note that there is no `type`
        # specified along with this schema. So it checks the value at runtime.
        # If it is a list, it validates each element of the list with that
        # sub-schema. If it is a dict, it *tries* to apply the schema directly
        # as the dict-schema, which leads to a runtime error when it tries to
        # interpret the string `integer` as a schema! Welp, bug-for-bug...
        if isinstance(value, list):
            result = []
            for idx, element in enumerate(value):
                result.append(
                    _normalize_schema(directive_value, element, ctx.push_stack(idx))
                )
            return (result, ctx)
        elif isinstance(value, dict):
            return (_normalize_dict(directive_value, value, ctx), ctx)
        # And if you pass something that's not a list or a dict, cerberus just allows it
        return (value, ctx)

    @directive("coerce_post")
    def handle_coerce_post(self, value, directive_value, ctx):
        """
        A coerce function that is explicitly done *after* other coercions are
        done (most importantly, after any normalization done in child dict
        values or list elements).
        """
        return self.handle_coerce(value, directive_value, ctx)

    @directive("validator")
    def handle_validator(self, value, directive_value, ctx):
        """
        Run a custom validator. This is intentionally the last step; it will
        validate only after all other normalization has been done.
        """
        field = ctx.stack[-1] if len(ctx.stack) else None

        def error(f, m):
            raise E.CustomValidatorError(f, m, stack=ctx.stack)

        try:
            directive_value(field, value, error)
        except E.SureError:
            raise
        except Exception as e:
            raise E.ValidatorUnexpectedError(field, value, e, ctx.stack)
        return (value, ctx)


def _normalize_schema(schema, value, ctx):
    normalizer = Normalizer(schema)
    directives = _get_directives(normalizer)
    known_directives = set(directive["directive"] for directive in directives)
    # These are handled outside of the directive machinery
    known_directives.update(
        {"excludes", "required", "default", "default_setter", "rename"}
    )
    unknown_directives = set(schema.keys()) - known_directives
    if unknown_directives:
        raise E.UnknownSchemaDirectives(unknown_directives)
    for directive in directives:
        if directive["directive"] in schema:
            directive_value = schema[directive["directive"]]
            result = directive["method"](normalizer, value, directive_value, ctx)
            if isinstance(result, _ShortCircuit):
                return result.value
            else:
                value, ctx = result
    return value


def _get_directives(normalizer):
    directives = []
    for (name, value) in getmembers(normalizer):
        directive = getattr(value, "sureberus_directive", None)
        if directive:
            directives.append(directive)
    directives.sort(key=lambda d: d["order"])
    return directives


def _normalize_multi(schema, value, key, ctx):
    clone = deepcopy(value)
    results = []
    errors = []
    matched_schemas = []
    for subrule in schema[key]:
        cloned_schema = deepcopy(schema)
        del cloned_schema[key]  # This is not very principled...?
        cloned_schema.update(subrule)
        subrule = cloned_schema
        try:
            subresult = _normalize_schema(subrule, clone, ctx)
        except E.SureError as e:
            errors.append(e)
        else:
            if key == "oneof":
                results.append(subresult)
                matched_schemas.append(schema[key])
            elif key == "anyof":
                return subresult
    if not results:
        raise E.NoneMatched(clone, errors, ctx.stack)
    elif key == "oneof" and len(results) > 1:
        raise E.MoreThanOneMatched(clone, matched_schemas, ctx.stack)
    else:
        return results[0]
