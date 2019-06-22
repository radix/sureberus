# Directives

This chapter provides a reference of all Sureberus schema directives.


## allow_unknown

**Validation Directive**<br>
**type**: `bool`

When **True**, extra keys in a dictionary are passed through silently.

When **False**, keys that are found in a dictionary but which aren't specified in a fields schema will cause an error to be raised.

## allowed

**Validation Directive**<br>
**type**: `list` of arbitrary Python objects

The object being validated must be equal to one of the objects in the list in order to pass validation.

## *of (anyof, oneof)

**Validation & Transformation Directive**<br>
**type** `list` of Sureberus schemas

Try applying schemas in sequence to the current value.

<div class="sureberus-alert">

These directives should be avoided, and [`choose_schema`](#choose_schema) should be strongly preferred, if possible.
These directives are generally inefficient and result in hard-to-read error messages.

</div>

When `anyof` is used, then as soon as any schema applies successfully, its result is returned.

When `oneof` is used, ALL schemas are checked, and if more than one can be applied successfully, an exception is raised
(this is very unlikely to be useful, you should probably just use `anyof`).

In either case, if none of the schemas can be applied without error, then a validation error will be raised.

<div class="sureberus-info">

Unlike Cerberus, these directives allow Transformation Directives to do their work as well.
If a schema can be applied successfully, the transformations it applies will be returned.

</div>

## choose_schema

**Meta Directive**<br>
**type** `dict` described below

Choose a schema based on different factors of the input document and the current Context.
See [Dynamically selecting schemas](./schema-selection.md) for more information.

The directive value is a dictionary which must contain one of the following keys.

* **when_key_is**

  **type** `dict` containing `key`, `choices`, and optionally `default_choice`<br>
  **example**<br>
  ```yaml
  choose_schema:
    when_key_is:
      key: "type"
      choices:
        "type1": ...
        "type2": ...
  ```

  Dynamically selects a schema based on the value of a specific key, specified by the `key` sub-directive.
  For example, if you have a value like `{"type": "foo", "foo_specific": "bar"}`,
  where the `foo` part determines which other keys might exist in the dict (like `foo_specific`),
  then this directive can help you choose a specific schema to validate with.

  When this directive is applied, it determines a schema to apply by accessing the key named by the `key` sub-directive in the value (which we'll call the "choice").
  If it's not found, then `default_choice` is used.
  It then looks up the schema to use by looking for that "choice" in the `choices` sub-directive.

* **when_key_exists**

  **type** `dict` (described below)<br>
  **example**
  ```yaml
  choose_schema:
    when_key_exists:
      "keyA": ...
      "keyB": ...
  ```

  Dynamically selects a schema based on whether a certain dict key exists.

  The directive should be provided a dictionary, where each **key** can potentially match a key in the value dictionary.
  Each **value** in the directive dictionary should be a Sureberus schema to apply to the dictionary **if** the key exists in the dictionary.

* **when_tag_is**

  **type** `dict` containing `tag`, `choices`, and optionally `default_choice`<br>
  **example**
  ```yaml
  choose_schema:
    when_tag_is:
      tag: mytag
      choices:
        "choiceA": ...
        "choiceB": ...
  ```

  This is very similar to `when_key_is`, but instead of choosing a schema based on the value of a dictionary key, it does it by using the context.
  It goes hand-in-hand with the [`set_tag`](#set_tag) or [`modify_context`](#modify_context) directives.

  When this directive is applied, it determines the schema to apply by looking up a tag named by the `tag` sub-directive (which we'll call the "choice").
  It then looks up the schema to use by looking for that "choice" in the `choices` sub-directive.

* **function**

  **type** Python callable `(value, context) -> Sureberus schema

  Dynamically choose a schema to use based on the current value and the Context object.
  The schema returned by the Python function will be applied to the value.

## coerce

**Transformation Directive**<br>
**type** Python callable `(value) -> new value`

Call a Python function with the value to get a new one to use.
It's important to note that this function is called *before* all other directives that might reject a value.
This is a good directive to use if you want to normalize invalid documents to a form that can be considered valid.

## coerce_post

**Transformation Directive**<br>
**type** Python callable `(value) -> new value`

Call a Python function with the value to get a new one to use.
Unlike `coerce`, this function is applied *after* all other directives,
so it's allowed to return values that wouldn't validate according to other directives in your schema.

## modify_context

**Meta Directive**<br>
**type** Python callable `(value, Context) -> Context`

Run a Python function to allow it to modify the current Context.
The Python function will be passed the value and the current Context, and must return a new Context.
This is most often used to call `context.set_tag(key, value)` to add a new tag to the Context,
to later be used with [`choose_schema`](#choose_schema).

See [Dynamically selecting schemas](./schema-selection.md) for more information.


## keyschema

**Validation & Transformation Directive**<br>
**type** Sureberus schema

Specify a schema to be applied to all keys in a dictionary.

## max

**Validation Directive**<br>
**type** Number (or anything that supports the comparison operators)

Raises an exception if the value is greater than the given number.

## maxlength

**Validation Directive**<br>
**type** Number

Raises an exception if the length of the value is greater than the given number.

## min

**Validation Directive**<br>
**type** Number (or anything that supports the comparison operators)

Raises an exception if the value is less than the given number.

## nullable

**Validation Directive**<br>
**type** `bool`

Specifically allows None, even if it would conflict with other validation directives.
If the value is None, no other directives are applied.

<div class="sureberus-info">

This directive slightly differs Cerberus's implementation, which doesn't honor `nullable` when a `*of` directive is present.
See [cerberus#373](https://github.com/pyeve/cerberus/issues/373).

</div>

## regex

**Validation Directive**<br>
**type** string (a regex)

*If* the value is a string, and it does not match the given regex, an exception will be raised.

## registry

**Meta Directive**<br>
**type** `dict` of schema names (strings) to Sureberus schemas

Registers named Sureberus schemas that can be referred to anywhere inside this schema.
This can be useful simply for factoring and schema reuse, but also enables recursive schemas.
To *use* a registered schema, simply put its name (as a string) any place where you would otherwise have a Sureberus schema.
`schema_ref` can also be useful for invoking registered schemas in certain situations.

See [Schema registries](./schema-registries.md) for more information.

See also the [schema_ref](#schema_ref) directive.

## schema_ref

**Meta Directive**<br>
**type** string (naming a registered schema)

Applies the named schema (defined in a registry) to the current value.
This can be useful if you want to register a schema and use it at the same "level".
Most of the time you don't need this, and instead just refer to the named schema by putting the schema name (as a string) anywhere you would normally specify a Sureberus schema.

See [Schema registries](./schema-registries.md) for more information.


## schema

**Meta Directive**<br>
**type** Varies

The meaning of a `schema` key inside a schema changes based on the type of the *value*. This is strange, but it's how Cerberus did things.

When the value is a list, the directive is interpreted as a Sureberus schema to apply to each element of the list.

When the value is a dict, the keys of the dict are looked up in the directive, and used to find a Sureberus schema to apply to the associated value.

<div class="sureberus-alert">

The weird thing is that, e.g., it is possible to define a schema like `{'schema': {'type': 'integer'}}`.
Note that there is no `type` specified along with this schema, so you can try to apply it to lists or dicts.
Since we check the value at runtime, if it is a list, it validates each element of the list with that sub-schema.
If it is a dict, it *tries* to apply the schema directly as the field-schema, which leads to a runtime error when it tries to interpret the string `integer` as a Sureberus schema!

While originally Sureberus tried to match Cerberus bug-for-bug, this behavior is just too strange.
Sureberus will be introducing more specific directives to indicate element-schemas and field-schemas in the future.

</div>

### schema (for lists)

The `schema` directive, when applied to a list, is very straightforward. It simply applies the schema to each element in the list.

### schema (for dicts)

The `schema` directive on dicts is more complicated.

Each key matches a key that can potentially be found in the dictionary.

Each value is a Sureberus schema that can have a few **extra** directives, specific to dict fields.

* `rename`: (string) If this is specified, then the dict key will be renamed to the specified key in the result.
* `required`: (`bool`) Indicates whether the field must be present.
* `excludes`: (`list of strings`) Specifies a list of keys which *must not exist* on the dictionary for this schema to validate.
* `default`: (object) A value to associate with the key in the resulting dict if the key was not present in the input.
* `default_setter`: (Python callable of `(dict) -> value`) A Python function to call if the key was not present in the input.
  It is passed the dictionary, and its return value will be used as the default.


## set_tag

**Meta Directive**<br>
**type** `dict` or string (described below)

Set a tag on the context. This directive can take various forms:

* `"set_tag": {"tag_name": "my-tag", "key": "foo"}`

  This sets the tag named `my-tag` with the value of `value["foo"]`.
  So it assumes that the value that the schema is being applied to is a dict.

* `"set_tag": "foo"`

  This sets the tag named `foo` with the value of `value["foo"]`.
  It's a shorthand for `{"tag_name": "foo", "key": "foo"}`.

* `"set_tag": {"tag_name": "my-tag", "value": "bar"}`

  This sets the tag named `my-tag` with a value of `"bar"` -- that is, a hardcoded value specified in the schema.
  This is very rarely useful, but is a convenient shorthand if you are referring to a schema that relies on a tag,
  in a context where the tag doesn't vary based on anything.

## type

**Validation Directive**<br>
**type** string

Raises an exception if the type of the value does not match the directive.

These are the types available:

```python
{
    "none": type(None),
    "integer": six.integer_types,
    "float": (float,) + six.integer_types,
    "number": (float,) + six.integer_types,
    "dict": dict,
    "list": list,
    "string": six.string_types,
    "boolean": bool,
}
```

## validator

**Validation Directive**<br>
**type** Python callable `(field, value, error_func) -> None`

Invokes a Python function to validate the value.
The function should return None if the value is valid, otherwise it should call
`error_func(field, "error message")`.


## valueschema

**Validation & Transformation Directive**<br>
**type** Sureberus schema

Applies the given Sureberus schema to all values in the dictionary (requires the value to be a dictionary).

