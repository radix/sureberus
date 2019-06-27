from .instructions import PerformMore


def _interpret(instructions, value, ctx):
    for instruction in instructions:
        result = instruction.perform(value, ctx)
        if isinstance(result, PerformMore):
            # TODO *actually* implement TCE
            subvalue, ctx = _interpret(result.instructions, result.value, result.ctx)
            if result.merge is not None:
                value = result.merge(subvalue)
        else:
            try:
                value, ctx = result
            except:
                print(instruction)
                raise
    return value, ctx


def interpret(instructions, value, ctx):
    return _interpret(instructions, value, ctx)[0]
