# Sureberus

Sureberus is a data validation and transformation tool that is useful for validating and normalizing "documents" (nested data structures of basic Python data-types). You provide a schema which describes the expected structure of an object (and optionally, various directives that modify that structure), along with a document to validate and transform, and it returns the new version.

Sureberus's schema format is based on [Cerberus](https://github.com/pyeve/cerberus/). It doesn't implement all of the features of that library, and where it does implement a feature it doesn't always implement it in the exact same way.

## Documentation

There is relatively complete documentation at <a href="https://radix.github.io/sureberus/">radix.github.io/sureberus</a>.
