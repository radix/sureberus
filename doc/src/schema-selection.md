# Dynamically selecting schemas

Sureberus has a directive for *selecting* schemas to apply based on various aspects of the input value, called [`choose_schema`](./directives.md#choose_schema). This directive is meant to be passed a dict, which must include a single sub-directive.

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

Then you would use `when_key_is` in your schema like this (in YAML syntax):

```yaml
type: dict
choose_schema:
  when_key_is:
    key: "type"
    choices:
      "elephant":
        schema:
          "trunk_length": {"type": "integer"}
      "eagle":
        schema:
          "wingspan": {"type": "integer"}
```

When the value contains a `type` key of `elephant`, Sureberus will choose the schema that contains `trunk_length`.
When the type is `eagle`, it will choose the schema containing `wingspan`.

### when_key_exists

Use this when you have dictionaries where you must choose the schema based on keys that exist in the data exclusively for their type of data.
For example, if you have data that can look like this:

```json
{"image_url": "foo.jpg", "width": 30}
{"color": "red"}
```

Then you would use `when_key_exists`, like this (in YAML):

```yaml
type: dict
choose_schema:
  when_key_exists:
    "image_url":
      schema:
        "image_url": {"type": "string"}
        "width": {"type": "integer"}
    "color":
      schema:
        "color": {"type": "string"}
```

Sureberus looks at the keys in the dictionary, and if one of the keys that are listed in `choices` are there, it will choose the corresponding schema.


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

* [`set_tag`](./directives.md#set_tag) - save a tag (a key/value pair) in the Context,
* [`choose_schema`](./directives.md#choose_schema) with `when_tag_is` - select a schema based on a saved tag found in the Context,
* [`modify_context`](./directives.md#modify_context) - run an arbitrary Python function that can manipulate the Context (including the tags),
* [`choose_schema`](./directives.md#choose_schema) with `function` - run an arbitrary Python function that can select a schema based on the Context.

The latter two, `modify_context` and `choose_schema` are generalizations of the first, and they
don't often need to be used.

Here's an example of a schema that can parse our sample data, using the Python schema syntax.

```python
schema = S.Dict(
  set_tag="type",
  schema={
    "type": S.String(),
    "common": S.Dict(),
    "data_service": S.Dict(
      schema={
        "renderers": S.List(
          schema=S.Dict(
            choose_schema=S.when_tag_is(
              "type",
              {
                "foo": S.Dict(schema={"foo_specific": S.String()}),
                "bar": S.Dict(schema={"bar_specific": S.Integer()}),
              })))})})
```

Here we're using the `set_tag` directive with its shorthand for specifying a tag name that will be equivalent to the name of the key to look up in the dict.
When Sureberus applies this schema to the top-level `dict`, it looks for the key named `type`, and stores its value in the Context under a tag named `type`.
Then, deeper inside this schema, we make use of the `choose_schema` directive with the `when_tag_is` sub-directive.
We pass the tag name `type` here, so it looks up the value associated with the `type` tag in the Context, and uses that to select the corresponding schema defined in the choices passed to `when_tag_is`.
Thus, when the top-level dict has `"type": "foo"`, Sureberus will ultimately select the schema containing `"foo_specific"`.
