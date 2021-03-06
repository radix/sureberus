# Python schema syntax

If you want to construct a schema from Python code instead of storing it as
JSON or YAML, sureberus provides a more terse syntax for it.

Here's a standard dict-based schema, using an 80-character limit and strict
newline/indent-based line wrapping:

```python
myschema = {
    'type': 'dict',
    'anyof': [
        {'fields': {'gradient': {'type': 'string'}}},
        {
            'fields': {
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
from sureberus.schema import Dict, String, Integer
myschema = Dict(
    anyof=[
        dict(gradient=String()),
        dict(image=String(), opacity=Integer(default=100))
    ]
)
```
