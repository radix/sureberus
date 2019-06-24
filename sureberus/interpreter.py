from .instructions import PerformMore

def interpret(instructions, value, ctx):
    for instruction in instructions:
        result = instruction.perform(value, ctx)
        if isinstance(result, PerformMore):
            # TODO *actually* implement TCE
            value, ctx = interpret(result)
        else:
            value, ctx = result
    return value