# Differences from Cerberus

## Transformation AND validation

Sureberus exists because Cerberus wasn't flexible enough for our use.
Most importantly, Cerberus strictly separates transformation (what the Cerberus documentation calls "Normalization") from validation;
if you want to transform a document with Cerberus, you can't also make sure it's valid at the same time.
This can lead to some surprising limitations.

For example,

```python
from sureberus import normalize_dict
from cerberus import Validator

schema = {
    "x": {
        "anyof": [
            {"type": "dict", "schema": {"y": {"type": "integer", "default": 0}}},
            {"type": "integer"},
        ]
    }
}
```

Here we have a schema that says:

* this is a dict
  * whose `x` field can either be
    * an integer,
    * or a dict,
      * containing a `y` field which defaults to 0.


Let's try using it with Sureberus.


```python
assert normalize_dict(schema, {"x": {}}) == {"x": {"y": 0}}
assert normalize_dict(schema, {"x": 5}) == {"x": 5}
```

These assertions run fine. Sureberus tries to normalize the value with each schema in turn, and returns the result of the first one that succeeds.

Now let's try with Cerberus.

```python
v = Validator(schema)
assert v.normalized({"x": {}}) == {"x": {"y": 0}} # This fails!
assert v.normalized({"x": 5}) == {"x": 5}
```

The first assertion fails, since Cerberus is returning `{'x': {}}` -- it seems to be completely disregarding our `default` directive. Why is this?

It's actually deeper than that, still. Let's see what happens when we pass something that obviously shouldn't even validate:

```python

# Sureberus:
with pytest.raises(E.NoneMatched):
    normalize_dict(schema, {"x": "foo"})

# Cerberus:
```

## Schema Selection

To improve upon the poor error messages that can occur when using "variable schemas" (the [`oneof` and `anyof`](./directives.md#of-anyof-oneof) directives) in Cerberus,
we've implemented facilities in Sureberus that make it much more clear how to choose schemas, with the [`choose_schema`](./directives.md#choose_schema) directive.

Not only does this make the schema easier to reason about, it makes error messages much nicer: with `anyof`, we have to say:

> "Sorry, your value didn't match this schema, or that schema, or that schema..."

But with the mechanisms available through `choose_schema`, we get to say:

> "I know you want to use THIS schema, because you had a field in your dictionary that indicated which schema to use. This is how it doesn't match..."

The `choose_schema` facility is documented more thoroughly in [Schema selection](./schema-selection.md).

## In-line schema registries

In Cerberus, you have to invoke Python code to register schemas.
This means you can't describe a recursive schema without writing custom Python code (as far as I have been able to figure out, anyway).
With Sureberus, you can take advanteg of the [`registry`](./directives.md#registry) directive which allows you to declare named schemas.
This means that recursive schemas are easy to define in Sureberus.
See [Schema registries](./schema-registries.md) for more information.
