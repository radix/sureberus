from abc import ABC, abstractmethod

import attr
import six

from . import errors as E
from . import _ShortCircuit


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
        return (value, self.func(value, ctx))


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
        for instr in instructions:
            # TODO: maybe we should have a way to *return* instructions
            # from a perform so that we don't deeply recurse
            value, ctx = instr.perform(value, ctx)
        return (value, ctx)


@attr.s
class CheckFields(Instruction):
    fields = attr.ib()

    def perform(self, value, ctx):
        raise NotImplementedError()

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
