# Sureberus

Sureberus is a data validation and transformation tool that is useful for validating and normalizing "documents" (nested data structures of basic Python data-types). You provide a schema which describes the expected structure of an object (and optionally, various directives that modify that structure), along with a document to validate and transform, and it returns the new version.

Sureberus's schema format is based on [Cerberus](https://github.com/pyeve/cerberus/). It doesn't implement all of the features of that library, and where it does implement a feature it doesn't always implement it in the exact same way.

Sureberus exists because Cerberus wasn't flexible enough for my use. Most importantly, Cerberus strictly separates transformation (what the Cerberus documentation calls "Normalization") from validation; if you want to transform a document, you can't also make sure it's valid at the same time. This can lead to some surprising limitations, some of which are documented below.

## Unique features in Sureberus

These are the features that exist in Sureberus but not in Cerberus.

### transformation inside of *of-rules

Sureberus allows you to use so-called *transformation* directives, such as `default` and `coerce`, while also validating the document. Most critically, Cerberus considers the [*of-rule](http://docs.python-cerberus.org/en/stable/validation-rules.html#of-rules) to be a *validation*-only directive. This means that in Cerberus, it's impossible to say: "this thing can either be a dict with an `x` key that defaults to None, or a string". This is probably one of the biggest limitations of Cerberus.

