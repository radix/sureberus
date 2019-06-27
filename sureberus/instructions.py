from abc import ABC, abstractmethod

import attr
import six

from . import errors as E
from . import _ShortCircuit
from .constants import _marker


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


class Instruction(ABC):
    @abstractmethod
    def perform(self, value, ctx):
        """Return a new value and a new context"""
        pass


@attr.s
class AddToDefaultRegistry(Instruction):
    defaults = attr.ib()

    def perform(self, value, ctx):
        return (value, ctx.register_defaults(self.defaults))


@attr.s
class AddToSchemaRegistry(Instruction):
    schemas = attr.ib()

    def perform(self, value, ctx):
        return (value, ctx.register_schemas(self.schemas))


@attr.s
class AddToCoerceRegistry(Instruction):
    coerces = attr.ib()

    def perform(self, value, ctx):
        return (value, ctx.register_coerces(self.coerces))


@attr.s
class AddToValidatorRegistry(Instruction):
    validators = attr.ib()

    def perform(self, value, ctx):
        return (value, ctx.register_validators(self.validators))


@attr.s
class AddToModifyContextRegistry(Instruction):
    modify_contexts = attr.ib()

    def perform(self, value, ctx):
        return (value, ctx.register_modify_contexts(self.modify_contexts))


@attr.s
class SetTagFromKey(Instruction):
    tag_name = attr.ib()
    key = attr.ib()

    def perform(self, value, ctx):
        ctx = ctx.set_tag(self.tag_name, value[self.key])
        return (value, ctx)


@attr.s
class SetTagValue(Instruction):
    tag_name = attr.ib()
    value = attr.ib()

    def perform(self, value, ctx):
        ctx = ctx.set_tag(self.tag_name, self.value)
        return (value, ctx)


@attr.s
class AllowUnknown(Instruction):
    allow_unknown = attr.ib()

    def perform(self, value, ctx):
        return (value, ctx.set_allow_unknown(self.allow_unknown))


@attr.s
class ModifyContext(Instruction):
    func = attr.ib()

    def perform(self, value, ctx):
        # I *think* it might be possible to move the function lookup to compile
        # time instead of validate-time...
        if isinstance(self.func, six.string_types):
            func = ctx.resolve_modify_context(self.func)
        else:
            func = self.func
        return (value, func(value, ctx))


@attr.s
class BranchWhenTagIs(Instruction):
    tag = attr.ib()
    default_choice = attr.ib()
    branches = attr.ib()  # dict of tag-value to list of instructions.

    def perform(self, value, ctx):
        chosen = ctx.get_tag(self.tag, self.default_choice)
        if chosen not in self.branches:
            raise E.DisallowedValue(chosen, self.choices.keys(), ctx.stack)
        instructions = self.branches[chosen]
        return PerformMore(instructions, value, ctx)


@attr.s
class ApplyDynamicSchema(Instruction):
    func = attr.ib()
    def perform(self, value, ctx):
        new_schema = self.func(value, ctx)
        from .compiler import compile
        from .interpreter import interpret
        # TODO: handle pre-compiled schemas
        instructions = compile(new_schema)
        return PerformMore(instructions, value, ctx)


@attr.s
class CheckElements(Instruction):
    instructions = attr.ib()

    def perform(self, value, ctx):
        idx = 0

        def merge(element_value):
            nonlocal idx
            new_value = value[:]
            new_value[idx] = element_value
            idx += 1
            return new_value

        from .interpreter import interpret

        # TODO: TCO
        value = [
            interpret(self.instructions, el, ctx.push_stack(idx))
            for idx, el in enumerate(value)
        ]
        return (value, ctx)


@attr.s
class CheckField(Instruction):
    field = attr.ib()
    instructions = attr.ib()
    required = attr.ib()
    default = attr.ib()

    def perform(self, value, ctx):
        def merge_field_value(field_value):
            new_value = value.copy()
            new_value[self.field] = field_value
            return new_value

        if self.field in value:
            return PerformMore(
                self.instructions,
                value[self.field],
                ctx.push_stack(self.field),
                merge=merge_field_value,
            )
        elif self.default is not _marker:
            value = value.copy()
            value[self.field] = self.default
            return (value, ctx)
        elif self.required:
            raise E.DictFieldNotFound(self.field, value, ctx.stack)
        else:
            return (value, ctx)


## Validation Directives


@attr.s
class CheckType(Instruction):
    type_name = attr.ib()

    def perform(self, value, ctx):
        types = TYPES[self.type_name]
        if not isinstance(value, types):
            raise E.BadType(value, self.type_name, ctx.stack)
        return (value, ctx)


@attr.s
class SkipIfNone(Instruction):
    def perform(self, value, ctx):
        if value is None:
            return _ShortCircuit(value)
        return (value, ctx)


@attr.s
class CheckAllowList(Instruction):
    allowed = attr.ib()

    def perform(self, value, ctx):
        if value not in self.allowed:
            raise E.DisallowedValue(value, self.allowed, ctx.stack)
        return (value, ctx)


## Coercion Directives


@attr.s
class Coerce(Instruction):
    func = attr.ib()

    def perform(self, value, ctx):
        try:
            return (self.func(value), ctx)
        except E.SureError:
            raise
        except Exception as e:
            raise E.CoerceUnexpectedError(value, e, ctx.stack)


@attr.s
class PerformMore(object):
    instructions = attr.ib()
    value = attr.ib()
    ctx = attr.ib()
    merge = attr.ib(default=None)

