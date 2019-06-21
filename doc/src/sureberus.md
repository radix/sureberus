# Sureberus

Sureberus is a data validation and transformation tool that is useful for validating and normalizing "documents" (nested data structures of basic Python data-types). You provide a schema which describes the expected structure of an object (and optionally, various directives that modify that structure), along with a document to validate and transform, and it returns the new version.

Sureberus is a spiritual descendent of [Cerberus](https://github.com/pyeve/cerberus/), more-or-less uses the same schema format.
There are some differences, though, which you can read about in [Differences from Cerberus](./cerberus.md).
