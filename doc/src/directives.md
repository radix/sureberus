# Directives

This chapter provides a reference of all Sureberus schema directives.


## allow_unknown

**Validation Directive**<br>
**type**: `bool`

<example>
<yaml-schema>
type: dict
allow_unknown: true
fields:
  known: {type: integer}
</yaml-schema>
<test>
<valid-input>{"known": 3, "unknown": 4}</valid-input>
</test>
</example>

<example>
<yaml-schema>
type: dict
allow_unknown: false
fields:
  known: {type: integer}
</yaml-schema>
<test>
<input>{"known": 3, "unknown": 4}</input>
<error>UnknownFields(value={"known": 3, "unknown": 4}, fields={"unknown"}, stack=())</error>
</test>
</example>

When **True**, extra keys in a dictionary are passed through silently.

When **False**, keys that are found in a dictionary but which aren't specified in a fields schema will cause an error to be raised.

## allowed

**Validation Directive**<br>
**type**: `list` of arbitrary Python objects

<example>
<yaml-schema>
allowed: ["foo", 1, 2, 3]
</yaml-schema>

<test>
<valid-input>"foo"</valid-input>
</test>

<test>
<valid-input>2</valid-input>
</test>

<test>
<input>5</input>
<error>DisallowedValue(value=5, values=["foo", 1, 2, 3], stack=())</error>
</test>
</example>


The object being validated must be equal to one of the objects in the list in order to pass validation.

## *of (anyof, oneof)

**Meta Directive**<br>
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
**type** `dict` described below<br>
**Introduced in** Sureberus 0.8.0

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

* **when_type_is**

  **type** `dict` (described below)<br>
  **Introduced in** Sureberus 0.11<br>
  **example**
  ```yaml
  choose_schema:
    when_type_is:
      integer: ...
      dict: ...
      list: ...
  ```

  This directive is given a mapping of type names (using the same names that the [`type`](#type) directive takes) to schemas.
  A schema is chosen based on the type of the value.

* **function**

  **type** Python callable `(value, context)` -> Sureberus schema

  Dynamically choose a schema to use based on the current value and the Context object.
  The schema returned by the Python function will be applied to the value.

## coerce

**Transformation Directive**<br>
**type** Python callable `(value) -> new value`, OR a string naming a registered coerce function

Call a Python function with the value to get a new one to use.
Or, if the directive is a string, look up the [registered coerce function](#coerce_registry) to perform coercion.
By default, you can pass `"to_list"` or `"to_set"` to convert the value to a list or set, if the value is not already a list or set, respectively.

It's important to note that this function is called *before* all other directives that might reject a value.
This is a good directive to use if you want to normalize invalid documents to a form that can be considered valid.

## coerce_post

**Transformation Directive**<br>
**type** Python callable `(value) -> new value`, OR a string naming a registered coerce function

Call a Python function with the value to get a new one to use, *after* all other validation.
Or, if the directive is a string, look up the [registered coerce function](#coerce_registry) to perform coercion.
By default, you can pass `"to_list"` or `"to_set"` to convert the value to a list or set, if the value is not already a list or set, respectively.

<div class="sureberus-info">

Unlike `coerce`, this function is applied *after* all other directives,
so it's allowed to return values that wouldn't validate according to other directives in your schema.

</div>

## coerce_with_context

**Transformation Directive**<br>
**type** Python callable `(value, Context) -> new value`, OR a string naming a registered coerce function<br>
**Introduced in** Sureberus 0.12.0

Call a Python function with the value *and the Context* to calculate a replacement.
Or, if the directive is a string, look up the [registered coerce function](#coerce_registry) to perform coercion.

This can be used in tandem with [`set_tag`](#set_tag) or [`modify_context`](#modify_context) to pass data to transformers that are run on deeper parts of the document.
The function can access tags stored in the context with the `Context.get_tag(tag_name)` method.


## coerce_post_with_context

**Transformation Directive**<br>
**type** Python callable `(value, Context) -> new value`, OR a string naming a registered coerce function<br>
**Introduced in** Sureberus 0.12.0

Identical to [`coerce`](#coerce_with_context), but runs after all validation.


## coerce_registry

**Meta Directive**<br>
**type** `dict` of `str` (coerce names) to Python callables<br>
**Introduced in** Sureberus 0.9.0

This allows you to register functions with a name that can be used in the [`coerce`](#coerce) and [`coerce_post`](#coerce_post) directives.
Each key in the directive should be a name, and the value should be a Python function that takes a single argument and returns a new value,
just like the functions you would normally pass to `coerce`.
Then you can pass the name of the registered function to `coerce` or `coerce_post` to invoke the registered function.

## default_registry

**Meta Directive**<br>
**type** `dict` of `str` (setter names) to Python callables<br>
**Introduced in** Sureberus 0.9.0

This allows you to register functions with a name that can be used in the `default_setter` directive of [field schemas](#fields).
Each key in the directive should be a name, and the value should be a Python function that acts like a `default_setter` function.
Then you can pass the name of the registered function to `default_setter` to invoke the registered function.


## elements

**Meta Directive**<br>
**type** Sureberus schema<br>
**Introduced in** Sureberus 0.9.0

Apply the given schema to each element in a list or other iterable.


## fields

**Meta Directive**<br>
**type** `dict` of keys to Sureberus schemas<br>
**Introduced in** Sureberus 0.9.0

When applying a schema with `fields` to a dictionary, each key in the value is looked up in the `fields` directive,
and used to find a Sureberus schema to apply to the value associated with that key in the dictionary being validated.

Each value is a Sureberus schema that can have a few **extra** directives, specific to dict fields.

* `rename`: (string) If this is specified, then the dict key will be renamed to the specified key in the result.
* `required`: (`bool`) Indicates whether the field must be present.
* `excludes`: (`list of strings`) Specifies a list of keys which *must not exist* on the dictionary for this schema to validate.
* `default`: (object) A value to associate with the key in the resulting dict if the key was not present in the input.
  If you want to default a field to an empty list or dict, do *not* use `default: []`. Instead use `default_setter: "list"`.
* `default_setter`: (Python callable of `(dict) -> value`, OR a string)
  A Python function to call if the key was not present in the input.
  It is passed the dictionary, and its return value will be used as the default.
  If default_setter is given a string, then it will be used to look up a setter that has been registered with [`default_registry`](#default_registry).
  By default, you can pass `"list"`, `"dict"`, or `"set"` to set the default to empty lists, dicts, and sets.


## modify_context

**Meta Directive**<br>
**type** Python callable `(value, Context) -> Context`<br>
**Introduced in** Sureberus 0.8.0

Run a Python function to allow it to modify the current Context.
The Python function will be passed the value and the current Context, and must return a new Context.
This is most often used to call `context.set_tag(key, value)` to add a new tag to the Context,
to later be used with [`choose_schema`](#choose_schema).

See [Dynamically selecting schemas](./schema-selection.md) for more information.


## modify_context_registry

**Meta Directive**<br>
**type** `dict` of `str` (modify_context names) to Python callables<br>
**Introduced in** Sureberus 0.9.0

This allows you to register functions with a name that can be used in the [`modify_context`](#modify_context) directive.
Each key in the directive should be a name, and the value should be a Python function that acts like a `modify_context` function.
Then you can pass the name of the registered function to `modify_context` to invoke the registered function.


## keyschema

**Meta Directive**<br>
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

`schema_ref` can also be used as an "inheritance" mechanism: the referred-to schema will be merged in to the schema that has the `schema_ref` directive, with the `schema_ref` schema taking a lower precedence.
As of Sureberus 0.10, Fields defined in a `fields` directive are also merged together. For example:

```yaml
registry:
  "common":
    type: dict
    fields:
      "common_field": {"type": "string"}
type: dict
schema_ref: "common"
fields:
  "extra_field": {"type": "string"}
```

This schema is equivalent to one that defines both `common_field` and `field` in the same `fields` directive.

See [Schema registries](./schema-registries.md) for more information.


## schema

**Meta Directive**<br>
**type** Varies

The meaning of a `schema` key inside a schema changes based on the type of the *value*. This is strange, but it's how Cerberus did things.
Use of either the [`fields`](#fields) directive for dicts, or the [`elements`](#elements) directive for lists, is strongly preferred.

When the value is a list, the directive is interpreted as a Sureberus schema to apply to each element of the list.

When the value is a dict, the keys of the dict are looked up in the directive, and used to find a Sureberus schema to apply to the associated value.

<div class="sureberus-alert">

The weird thing is that, e.g., it is possible to define a schema like `{'schema': {'type': 'integer'}}`,
without a `type` specified along with the schema, so you can try to apply it to lists or dicts.
Since we check the value at runtime, if it is a list, it validates each element of the list with that sub-schema.
If it is a dict, it *tries* to apply the schema directly as the field-schema, which leads to a runtime error when it tries to interpret the string `integer` as a Sureberus schema!

While Sureberus tried to match Cerberus bug-for-bug, this behavior (and the naming of the `schema` directive) is just too strange.
This is why Sureberus has introduced [`fields`](#fields) and [`elements`](#elements) directives. Please use those instead.

</div>


## set_tag

**Meta Directive**<br>
**type** `dict` or string (described below)<br>
**Introduced in** Sureberus 0.8.0

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
**type** Python callable `(field, value, error_func) -> None`, OR a string naming a registered validator.

Invokes a Python function to validate the value.
Or, if the directive is a string, look up the [registered validator function](#validator_registry) to perform coercion.
The function should return None if the value is valid, otherwise it should call
`error_func(field, "error message")`.

## validator_registry

**Meta Directive**<br>
**type** `dict` of `str` (validator names) to Python callables<br>
**Introduced in** Sureberus 0.9.0

This allows you to register functions with a name that can be used in the [`validator`](#validator) directive.
Each key in the directive should be a name, and the value should be a Python function that acts like a `validator` function.
Then you can pass the name of the registered function to `validator` to invoke the registered function.

## valueschema

**Meta Directive**<br>
**type** Sureberus schema

Applies the given Sureberus schema to all values in the dictionary (requires the value to be a dictionary).

