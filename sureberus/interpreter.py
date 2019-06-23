def interpret(instructions, value, ctx):
    for instruction in instructions:
        value, ctx = instruction.perform(value, ctx)
    return value
