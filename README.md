# Sureberus

Sureberus is a data validation and transformation tool that is useful for validating and normalizing "documents" (nested data structures of basic Python data-types). You provide a schema which describes the expected structure of an object (and optionally, various directives that modify that structure), along with a document to validate and transform, and it returns the new version.

Sureberus's schema format is based on [Cerberus](https://github.com/pyeve/cerberus/). It doesn't implement all of the features of that library, and where it does implement a feature it doesn't always implement it in the exact same way.

Sureberus exists because Cerberus wasn't flexible enough for my use. Most importantly, Cerberus strictly separates transformation ("coersion") from validation; if you want to transform a document, you can't also make sure it's valid at the same time. This can lead to some surprising limitations, some of which are documented below.

## Unique features in Sureberus

These are the features that exist in Sureberus but not in Cerberus.

### transformation inside of *of-rules

Sureberus allows you to use so-called *transformation* directives, such as `default` and `coerce`, while also validating the document. Most critically, Cerberus considers the [*of-rule](http://docs.python-cerberus.org/en/stable/validation-rules.html#of-rules) to be a *validation*-only directive. This means that in Cerberus, it's impossible to say: "this thing can either be a dict with an `x` key that defaults to None, or a string". This is probably one of the biggest limitations of Cerberus.

### Schema selection based on dict keys

Often times when [`anyof` or `oneof`](http://docs.python-cerberus.org/en/stable/validation-rules.html#of-rules) are used, what we really want to do is *select* a schema based on dict keys.

There are two options for this, which should be used in preference to `anyof` or `oneof`, when possible, as they provide much better error messages.

#### when_key_is

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

You can also specify a `default_choice` inside of the `when_key_is` directive,
to specify which choice to use if the (e.g.) `type` key is elided from the
value being validated.

#### when_key_exists

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


### In-line schema registries

Small, reusable "chunks" of schema can be defined in-line in the schema
specification, instead of requiring Python code to be written which sets up
registries. This allows for easy use of recursive schemas at any point in your
schema, or just a way to conveniently reuse some subschema in multiple places.
For example, here is a schema that validates any nested list of strings:

```json
{
    "registry": {
        "nested_list": {
            "type": "list",
            "schema": {
                "anyof": [
                    {"type": "string"},
                    "nested_list",
                ],
            }
        }
    },
    "type": "dict",
    "schema": {"things": "nested_list"},
}
```

This will validate data like `{"things": ["one", ["two", ["three"]]]}`.

Typically any place you can specify a schema, you can instead specify a string
which will be used to find a previously registered schema (references to
registered schemas are resolved lexically).

When you need to "merge in" a registered schema, you can use the `schema_ref`
directive. This can be useful if you want to register a schema and use it at
exactly the same level, for example:

```json
{
    "registry": {
        "nested_list": {
            "type": "list",
            "schema": {"anyof": [{"type": "integer"}, "nested_list"]}
        }
    },
    "schema_ref": "nested_list",
}
```

This will validate data like `["one", ["two", ["three"]]]`.


### Nullable in the face of *of-rules

Sureberus allows you to use `nullable` even if you have `*of-rules` that have
`type` constraints. A nullable schema always allows `None`.

### A slightly nicer schema syntax

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
