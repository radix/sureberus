# Dynamically selecting schemas

Sureberus has useful directives for *selecting* schemas to apply based on various aspects of the input value.
These directives should always be preferred over the [`anyof` or `oneof`](./directives.md#of-anyof-oneof) directives, since they provide much nicer error messages and represent the schema in a more principled way.

## Schema selection based on dict keys: when_key_is, when_key_exists

There are two options for selecting a schema based on dict keys.

* `when_key_is` is for when you have a dictionary that contains something like a `"type"` key, whose value lets you identify a specific schema to apply.
* `when_key_exists` is for when you have a dictionary where different keys appear, and the existence of specific keys allows you to choose a schema to apply.

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

You can also specify a `default_choice` inside of the `when_key_is` directive,
to specify which choice to use if the (e.g.) `type` key is elided from the
value being validated.

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


## Schema selection based on context

While `when_key_is` can work when you need to vary the way an object is validated or transformed
based on a key *existing in that same object*, sometimes the relationship of the schema specifier
and the content to be varied is not so tightly bound.

For example, let's take a look at the following data:

```json
{
    "type": "foo",
    "common": {},
    "data_service": {
        "renderers": [
            {"foo_specific": "bar"}
        ]
    }
}
```

Let's assume that this structure is mostly fixed. We have a `type` key in
the top-level dict, but the only part of the schema that we want to vary is inside the
`renderers` list. If all we have is `when_key_is`, then we need to end up duplicating the whole
`data_services` and `renderers` schemas inside the `choices` directive of the `when_key_is` construct.

Sureberus provides a mechanism that allows you to define schemas that vary based on context, even
if that context comes from much higher up in the object. We basically have a way to "remember" the
value of `type`, so that it can be used later when applying schemas to values nested arbitrarily
deeply in the object.

There are four directives that provide these mechanisms. For most cases, you only need to care
about the first two of them:

* `set_tag` - save a tag (a key/value pair) in the Context,
* `when_tag_is` - select a schema based on a saved tag found in the Context,
* `hook_context` - run an arbitrary Python function that can manipulate the Context (including
  the tags),
* `choose_schema` - run an arbitrary Python function that can select a schema based on the
  Context.

The latter two, `hook_context` and `choose_schema` are generalizations of the first, and they
don't often need to be used.

Here's an example of a schema that can parse our sample data, encoded as YAML:

```yaml
type: dict
set_tag: "type"
schema:
  type: foo
  common: {type: dict}
  data_service:
    type: dict
    schema:
      renderers:
        type: list
        schema:
          type: dict
          when_tag_is:
            tag: type
            choices:
              foo: {"type": dict, "schema": {foo_specific: {type: string}}
              bar: {"type": dict, "schema": {bar_specific: {type: integer}}
```
