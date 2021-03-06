# Schema registries

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
            "elements": {
                "anyof": [
                    {"type": "string"},
                    "nested_list",
                ],
            }
        }
    },
    "type": "dict",
    "fields": {"things": "nested_list"},
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
            "elements": {"anyof": [{"type": "integer"}, "nested_list"]}
        }
    },
    "schema_ref": "nested_list",
}
```

This will validate data like `["one", ["two", ["three"]]]`.
