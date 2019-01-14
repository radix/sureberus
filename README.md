# Sureberus

This is an implementation of the [Cerberus](https://github.com/pyeve/cerberus/)
schema format. It doesn't implement all of the features of that library, and
where it does implement a feature it doesn't always implement it in the exact
same way.

The main reason it exists is to support some of the things that Cerberus doesn't
do

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
