from .instructions import PerformMore

def _interpret(instructions, value, ctx):
    for instruction in instructions:
        result = instruction.perform(value, ctx)
        if isinstance(result, PerformMore):
            # TODO *actually* implement TCE
            value, ctx = _interpret(result.instructions, result.value, result.ctx)
        else:
            value, ctx = result
    return value, ctx

def interpret(instructions, value, ctx):
    return _interpret(instructions, value, ctx)[0]
