from .instructions import PerformMore, SchemaReference


def _interpret(transformer, value, ctx):
    if isinstance(transformer, SchemaReference):
        transformer = ctx.find_schema(transformer.schema_name)
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
