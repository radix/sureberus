from .instructions import PerformMore


def _interpret(transformer, value, ctx):
    for instruction in transformer.instructions:
        result = instruction.perform(value, ctx)
        if isinstance(result, PerformMore):
            # TODO *actually* implement TCE
            subvalue, ctx = _interpret(result.transformer, result.value, result.ctx)
            if result.merge is not None:
                value = result.merge(subvalue)
        else:
            try:
                value, ctx = result
            except:
                print(instruction)
                raise
    return value, ctx


def interpret(transformer, value, ctx):
    return _interpret(transformer, value, ctx)[0]
