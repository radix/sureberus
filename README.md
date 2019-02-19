# Sureberus

This is an implementation of the [Cerberus](https://github.com/pyeve/cerberus/)
schema format. It doesn't implement all of the features of that library, and
where it does implement a feature it doesn't always implement it in the exact
same way.

The main reason it exists is to support some of the things that Cerberus doesn't
do.

## Schema selection based on dict keys

Often times when `anyof` or `oneof` are used, what we really want to do is
*select* a schema based on dict keys.

There are two options for this:

### when_key_is

Use this when you have dictionaries that have a fixed key, such as `"type"`,
which specifies some specific format to use. For example, if you have data that
can look like this:

```json
{"type": "elephant", "trunk_length": 60}
{"type": "eagle", "wingspan": 50}
```

Then you would use `when_key_is`, like this:

```json
{
    "type": "dict",
    "when_key_is": {
        "key": "type",
        "choices": {
            "elephant": {
                "schema": {"trunk_length": {"type": "integer"}}
            },
            "eagle": {
                "schema": {"wingspan": {"type": "integer"}}
            },
        }
    }
}
```

### when_key_exists

Use this when you have dictionaries where you must choose the schema based on
keys that exist in the data exclusively for their type of data. For example, if
you have data that can look like this:

```json
{"image_url": "foo.jpg", "width": 30}
{"color": "red"}
```

Then you would use `when_key_exists`, like this:

```json
{
    "type": "dict",
    "when_key_exists": {
        "image_url": {
            "schema": {"image_url": {"type": "string"}, "width": {"type": "integer"}}
        },
        "color": {
            "schema": {"color": {"type": "string"}}
        },
    }
}
```


## normalization inside of *of-rules

The primary important difference is that you can use sureberus if you want to
use `default` or `coerce` inside of a
[*of-rule](http://docs.python-cerberus.org/en/stable/validation-rules.html#of-rules).

## Nullable in the face of *of-rules

Sureberus allows you to use `nullable` even if you have `*of-rules` that have
`type` constraints. A nullable schema always allows `None`.

## A slightly nicer schema syntax

If you want to construct a schema from Python code instead of storing it as
JSON, sureberus provides a more terse syntax for it:

Here's a standard dict-based schema, using an 80-character limit and strict
newline/indent-based line wrapping:

```python
myschema = {
    'type': 'dict',
    'anyof': [
        {'schema': {'gradient': {'type': 'string'}}},
        {
            'schema': {
                'image': {'type': 'string'},
                'opacity': {'type': 'integer', 'default': 100},
            }
        },
    ],
}
```

And here is a `sureberus.schema`-based schema, using the same line-wrapping
rules:

```python
from sureberus.schema import Dict, SubSchema, String, Integer
myschema = Dict(
    anyof=[
        SubSchema(gradient=String()),
        SubSchema(image=String(), opacity=Integer(default=100))
    ]
)
```
