from .instructions import PerformMore, SchemaReference
from . import _ShortCircuit


def _interpret(transformer, value, ctx):
    if isinstance(transformer, str):
        transformer = ctx.find_schema(transformer)
    for instruction in transformer.instructions:
        result = instruction.perform(value, ctx)
        if isinstance(result, PerformMore):
            # TODO *actually* implement TCE
            subvalue, ctx = _interpret(result.transformer, result.value, result.ctx)
            if result.merge is not None:
                value = result.merge(subvalue)
            else:
                value = subvalue
        elif isinstance(result, _ShortCircuit):
            return result.value, ctx
        else:
            value, ctx = result
    return value, ctx


def interpret(transformer, value, ctx):
    return _interpret(transformer, value, ctx)[0]
