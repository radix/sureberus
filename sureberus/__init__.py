from __future__ import print_function

from copy import deepcopy
from inspect import getmembers
import re
import warnings

import attr
import six

from . import errors as E
from .constants import _marker

__all__ = ["normalize_dict", "normalize_schema"]


@attr.s(frozen=True)
class Context(object):
    allow_unknown = attr.ib()
    stack = attr.ib(factory=tuple)
    schema_registry = attr.ib(factory=dict)
    default_registry = attr.ib(factory=dict)
    coerce_registry = attr.ib(factory=dict)
    modify_context_registry = attr.ib(factory=dict)
    validator_registry = attr.ib(factory=dict)
    tags = attr.ib(factory=dict)

    def push_stack(self, x):
        return attr.evolve(self, stack=self.stack + (x,))

    def set_allow_unknown(self, x):
        return attr.evolve(self, allow_unknown=x)

    def register_schemas(self, registry):
        reg = self.schema_registry.copy()
        reg.update(registry)
        return attr.evolve(self, schema_registry=reg)

    def register_defaults(self, registry):
        reg = self.default_registry.copy()
        reg.update(registry)
        return attr.evolve(self, default_registry=reg)

    def register_coerces(self, registry):
        reg = self.coerce_registry.copy()
        reg.update(registry)
        return attr.evolve(self, coerce_registry=reg)

    def register_validators(self, registry):
        reg = self.validator_registry.copy()
        reg.update(registry)
        return attr.evolve(self, validator_registry=reg)

    def register_modify_contexts(self, registry):
        reg = self.modify_context_registry.copy()
        reg.update(registry)
        return attr.evolve(self, modify_context_registry=reg)

    def resolve_default_setter(self, setter):
        return self._resolve_registered(setter, self.default_registry, "default")

    def resolve_coerce(self, coerce):
        return self._resolve_registered(coerce, self.coerce_registry, "coerce")

    def resolve_validator(self, validator):
        return self._resolve_registered(validator, self.validator_registry, "validator")

    def resolve_modify_context(self, modify_context):
        return self._resolve_registered(
            modify_context, self.modify_context_registry, "modify_context"
        )

    def _resolve_registered(self, thing, registry, name):
        if isinstance(thing, six.string_types):
            if thing in registry:
                return registry[thing]
            else:
                # this *shouldn't* take the stack; this error should be discovered
                # when the schema is initially being parsed.
                raise E.RegisteredFunctionNotFound(thing, name, self.stack)
        else:
            return thing

    def find_schema(self, name):
        return self.schema_registry[name]

    def set_tag(self, tag, value):
        tags = self.tags.copy()
        tags[tag] = value
        return attr.evolve(self, tags=tags)

    def get_tag(self, tag, default=_marker):
        if default is _marker and tag not in self.tags:
            raise E.TagNotFound(tag, self.tags.keys(), self.stack)
        return self.tags.get(tag, default)


INIT_CONTEXT = Context(
    stack=(),
    allow_unknown=False,
    default_registry={
        "list": lambda _: [],
        "dict": lambda _: {},
        "set": lambda _: set(),
    },
    coerce_registry={
        "to_list": lambda x: [x] if not isinstance(x, list) else x,
        "to_set": lambda x: {x} if not isinstance(x, set) else x,
    },
)


def normalize_dict(dict_schema, value, stack=(), allow_unknown=False):
    schema = S.Dict(fields=dict_schema, allow_unknown=allow_unknown)
    return normalize_schema(schema, value, INIT_CONTEXT)


def normalize_schema(schema, value, stack=(), allow_unknown=False):
    ctx = INIT_CONTEXT.set_allow_unknown(allow_unknown)
    from .compiler import compile
    from .interpreter import interpret
    return interpret(compile(schema), value, ctx)


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
        if isinstance(key_schema, str):
            key_schema = ctx.find_schema(key_schema)
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
            default_setter = ctx.resolve_default_setter(default_setter)
            try:
                return default_setter(doc)
            except Exception as e:
                raise E.DefaultSetterUnexpectedError(key, doc, e, ctx.stack)
    return _marker


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

    @directive("default_registry")
    def handle_default_registry(self, value, directive_value, ctx):
        from .instructions import AddToDefaultRegistry
        return (value, AddToDefaultRegistry(directive_value).perform(value, ctx)[1])

    @directive("registry")
    def handle_registry(self, value, directive_value, ctx):
        from .instructions import AddToSchemaRegistry
        return (value, AddToSchemaRegistry(directive_value).perform(value, ctx)[1])

    @directive("coerce_registry")
    def handle_coerce_registry(self, value, directive_value, ctx):
        from .instructions import AddToCoerceRegistry
        return (value, AddToCoerceRegistry(directive_value).perform(value, ctx)[1])

    @directive("validator_registry")
    def handle_validator_registry(self, value, directive_value, ctx):
        from .instructions import AddToValidatorRegistry
        return (value, AddToValidatorRegistry(directive_value).perform(value, ctx)[1])

    @directive("modify_context_registry")
    def handle_modify_context_registry(self, value, directive_value, ctx):
        from .instructions import AddToModifyContextRegistry
        return (value, AddToModifyContextRegistry(directive_value).perform(value, ctx)[1])

    @directive("allow_unknown")
    def handle_allow_unknown(self, value, directive_value, ctx):
        from .instructions import AllowUnknown
        return AllowUnknown(directive_value).perform(value, ctx)

    @directive("schema_ref")
    def handle_registered_schema(self, value, directive_value, ctx):
        # this CANNOT be directly ported to an Instruction, because instructions don't have "schemas" to refer to.
        # The compiler will need to do something special about this... I don't fuckin' know!
        schema = self.schema.copy()
        new_schema = ctx.find_schema(directive_value)
        schema.update(new_schema)
        del schema["schema_ref"]
        return _ShortCircuit(_normalize_schema(schema, value, ctx))

    @directive("coerce")
    def handle_coerce(self, value, directive_value, ctx):
        from .instructions import Coerce
        func = ctx.resolve_coerce(directive_value)
        instruction = Coerce(func)
        return instruction.perform(value, ctx)

    @directive("nullable")
    def handle_nullable(self, value, directive_value, ctx):
        if directive_value: # why would you ever pass `nullable: false`?
            from .instructions import SkipIfNone
            return SkipIfNone().perform(value, ctx)
        return (value, ctx)

    @directive("modify_context")
    def handle_modify_context(self, value, directive_value, ctx):
        from .instructions import ModifyContext
        func = ctx.resolve_modify_context(directive_value)
        return ModifyContext(func).perform(value, ctx)

    @directive("set_tag")
    def handle_set_tag(self, value, directive_value, ctx):
        if not isinstance(directive_value, list):
            directive_value = [directive_value]
        # This logic will be moved to the compiler
        for dv in directive_value:
            if isinstance(dv, six.string_types):
                ctx = ctx.set_tag(dv, value[dv])
            else:
                if "key" in dv:
                    from .instructions import SetTagFromKey
                    ctx = SetTagFromKey(dv["tag_name"], dv["key"]).perform(value, ctx)[1]
                elif "value" in dv:
                    from .instructions import SetTagValue
                    ctx = SetTagValue(dv["tag_name"], dv["value"]).perform(value, ctx)[1]
                else:
                    raise E.SimpleSchemaError(
                        msg="`set_tag` must have `key` or `value`"
                    )
        return (value, ctx)

    @directive("choose_schema")
    def handle_choose_schema(self, value, directive_value, ctx):
        """
        A directive that allows dynamically choosing a schema based on all SORTS of stuff.
        """
        # TODO: validate w/ a when_key_exists schema. Only one should be allowed.
        if "when_tag_is" in directive_value:
            return self._handle_when_tag_is(value, directive_value["when_tag_is"], ctx)
        elif "function" in directive_value:
            schema = directive_value["function"](value, ctx)
            return _ShortCircuit(_normalize_schema(schema, value, ctx))
        elif "when_key_is" in directive_value:
            return self._handle_when_key_is(
                value, directive_value["when_key_is"], ctx, "choose_schema"
            )
        elif "when_key_exists" in directive_value:
            return self._handle_when_key_exists(
                value, directive_value["when_key_exists"], ctx, "choose_schema"
            )
        else:
            raise E.SimpleSchemaError(
                msg="`choose_schema` must have `when_tag_is` or `function`."
            )

    def _handle_when_tag_is(self, value, directive_value, ctx):
        #BranchWhenTagIs(directive_value["tag"],)
        choice_key = directive_value["tag"]
        chosen = ctx.get_tag(choice_key, directive_value.get("default_choice", _marker))
        if chosen not in directive_value["choices"]:
            raise E.DisallowedValue(
                chosen, directive_value["choices"].keys(), ctx.stack
            )
        subschema = directive_value["choices"][chosen]
        if isinstance(subschema, str):
            subschema = ctx.find_schema(subschema)
        new_schema = deepcopy(self.schema)
        subschema = subschema.copy()
        if "fields" in new_schema or "fields" in subschema:
            # merge in fields.
            # I wish I didn't need to do this, but it's the only sensible way I can figure out
            # to support both common and tag-specific fields in the same schema.
            new_schema.setdefault("fields", {}).update(subschema.pop("fields", {}))
        new_schema.update(subschema)
        del new_schema["choose_schema"]
        return _ShortCircuit(_normalize_schema(new_schema, value, ctx))

    @directive("when_key_is")
    def handle_when_key_is(self, value, directive_value, ctx):
        warnings.warn(
            "The top-level `when_key_is` directive is deprecated. Please use `choose_schema`.",
            DeprecationWarning,
        )
        return self._handle_when_key_is(value, directive_value, ctx, "when_key_is")

    def _handle_when_key_is(self, value, directive_value, ctx, directive_name):
        # At this point, we *need* this thing to be a dict, so we can look up
        # keys. So let's make sure it's a dict.
        self.handle_type(value, "dict", ctx)
        choice_key = directive_value["key"]
        new_schema = deepcopy(self.schema)
        # Putting the "choice key" into the dict schema is not required,
        # since we can figure out exactly which values it should allow based
        # on what's in the `when_key_is`.
        allowed_choices = list(directive_value["choices"].keys())
        if choice_key not in new_schema.setdefault("fields", {}):
            new_schema["fields"][choice_key] = {"allowed": allowed_choices}
        if choice_key not in value:
            if "default_choice" in directive_value:
                chosen_type = directive_value["default_choice"]
            else:
                raise E.DictFieldNotFound(choice_key, value, ctx.stack)
        else:
            chosen_type = value[choice_key]
        if chosen_type not in directive_value["choices"]:
            raise E.DisallowedValue(
                chosen_type, allowed_choices, ctx.push_stack(choice_key).stack
            )
        subschema = directive_value["choices"][chosen_type]
        if isinstance(subschema, str):
            subschema = ctx.find_schema(subschema)
        subschema = subschema.copy()
        # this is some shenanigans to support both "fields" and "schema"
        fields = new_schema.pop("schema", {}).copy()
        fields.update(new_schema.pop("fields", {}))
        new_schema["fields"] = fields
        new_schema["fields"].update(subschema.pop("schema", {}))
        new_schema["fields"].update(subschema.pop("fields", {}))
        new_schema.update(subschema)
        # Make sure that the new schema does not include the same `choose_schema`
        # or `when_key_is` directive, to avoid infinite recursion
        del new_schema[directive_name]
        return _ShortCircuit(_normalize_schema(new_schema, value, ctx))

    @directive("when_key_exists")
    def handle_when_key_exists(self, value, directive_value, ctx):
        warnings.warn(
            "The top-level `when_key_exists` directive is deprecated. Please use `choose_schema`.",
            DeprecationWarning,
        )
        return self._handle_when_key_exists(
            value, directive_value, ctx, "when_key_exists"
        )

    def _handle_when_key_exists(self, value, directive_value, ctx, directive_name):
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

        subschema = directive_value[chosen_type]
        if isinstance(subschema, str):
            subschema = ctx.find_schema(subschema)
        subschema = subschema.copy()
        # this is some shenanigans to support both "fields" and "schema"
        fields = new_schema.pop("schema", {}).copy()
        fields.update(new_schema.pop("fields", {}))
        new_schema["fields"] = fields
        new_schema["fields"].update(subschema.pop("schema", {}))
        new_schema["fields"].update(subschema.pop("fields", {}))
        new_schema.update(subschema)
        # Make sure that the new schema does not include the same `choose_schema`
        # or `when_key_is` directive, to avoid infinite recursion
        del new_schema[directive_name]
        return _ShortCircuit(_normalize_schema(new_schema, value, ctx))

    @directive("oneof")
    def handle_oneof(self, value, directive_value, ctx):
        return _ShortCircuit(_normalize_multi(self.schema, value, "oneof", ctx))

    @directive("anyof")
    def handle_anyof(self, value, _directive_value, ctx):
        return _ShortCircuit(_normalize_multi(self.schema, value, "anyof", ctx))

    @directive("allowed")
    def handle_allowed(self, value, directive_value, ctx):
        from .instructions import CheckAllowList
        return CheckAllowList(directive_value).perform(value, ctx)

    @directive("type")
    def handle_type(self, value, directive_value, ctx):
        from .instructions import CheckType
        return CheckType(directive_value).perform(value, ctx)

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

    @directive("keyschema")
    def handle_keyschema(self, value, directive_value, ctx):
        for k in list(value.keys()):
            new_key = _normalize_schema(directive_value, k, ctx.push_stack(k))
            value[new_key] = value.pop(k)
        return (value, ctx)

    @directive("valueschema")
    def handle_valueschema(self, value, directive_value, ctx):
        for k, v in value.items():
            value[k] = _normalize_schema(directive_value, v, ctx.push_stack(k))
        return (value, ctx)

    @directive("elements")
    def handle_elements(self, value, directive_value, ctx):
        result = [
            _normalize_schema(directive_value, element, ctx.push_stack(idx))
            for idx, element in enumerate(value)
        ]
        return (result, ctx)

    @directive("fields")
    def handle_fields(self, value, directive_value, ctx):
        return (_normalize_dict(directive_value, value, ctx), ctx)

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
            return self.handle_elements(value, directive_value, ctx)
        elif isinstance(value, dict):
            return self.handle_fields(value, directive_value, ctx)
        # And if you pass something that's not a list or a dict, cerberus just allows it
        return (value, ctx)

    @directive("validator")
    def handle_validator(self, value, directive_value, ctx):
        """
        Run a custom validator. This is intentionally the last step; it will
        validate only after all other normalization has been done.
        The only exception is `coerce_post`.
        """
        field = ctx.stack[-1] if len(ctx.stack) else None

        def error(f, m):
            raise E.CustomValidatorError(f, m, stack=ctx.stack)

        try:
            ctx.resolve_validator(directive_value)(field, value, error)
        except E.SureError:
            raise
        except Exception as e:
            raise E.ValidatorUnexpectedError(field, value, e, ctx.stack)
        return (value, ctx)

    @directive("coerce_post")
    def handle_coerce_post(self, value, directive_value, ctx):
        """
        A coerce function that is explicitly done *after* other coercions are
        done (most importantly, after any normalization done in child dict
        values or list elements).
        """
        return self.handle_coerce(value, directive_value, ctx)


def _normalize_schema(schema, value, ctx):
    if isinstance(schema, str):
        schema = ctx.find_schema(schema)
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
        if isinstance(subrule, str):
            subrule = ctx.find_schema(subrule)
        cloned_schema = deepcopy(schema)
        del cloned_schema[key]
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
