# Sureberus

This is an implementation of the [Cerberus](https://github.com/pyeve/cerberus/)
schema format. It doesn't implement all of the features of that library.

The main reason it exists is to support some of the things that Cerberus doesn't
do

## normalization inside of *of-rules

You can use sureberus if you want to use `default` or `coerce` inside of a
[*of-rule](http://docs.python-cerberus.org/en/stable/validation-rules.html#of-rules).

## Nullable in the face of *of-rules

Sureberus allows you to use `nullable` even if you have `*of-rules` that have
`type` constraints.
