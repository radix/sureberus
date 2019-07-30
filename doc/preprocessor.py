import html
import json
import re
import sys
import textwrap
from xml.etree import ElementTree as XML

import yaml

from sureberus import errors as E, normalize_schema


_debug_f = open("mdbook-debug.log", "w")


def dbg(*args):
    print(*args, file=_debug_f)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "supports":
        if sys.argv[2] == "html":
            sys.exit(0)
        else:
            sys.exit(1)

    context, book = json.load(sys.stdin)
    # print(context.keys(), file=debug)
    # print(json.dumps(book, indent=2, sort_keys=True), file=debug)

    book["sections"] = list(map(handle_section, book["sections"]))
    print(json.dumps(book, sort_keys=True, indent=2))


def handle_section(section):
    if "Chapter" in section:
        section["Chapter"] = handle_chapter(section["Chapter"])
    return section


def handle_chapter(chapter):
    if "sub_items" in chapter:
        chapter["sub_items"] = list(map(handle_section, chapter["sub_items"]))
    if "content" in chapter:
        chapter["content"] = process_content(chapter["content"])
    return chapter


example_re = re.compile("<example>.*?</example>", re.DOTALL)


def process_content(content):
    return example_re.sub(replace_example, content)


def replace_example(example):
    xml = XML.fromstring(example.group())
    assert xml.tag == "example"

    schema = None
    schema_type = None
    tests = []
    for child in xml:
        if child.tag == "yaml-schema":
            schema_type = "yaml"
            schema = child.text
        if child.tag == "test":
            test = {}
            for test_child in child:
                if test_child.tag == "valid-input":
                    test["input"] = test_child.text
                    test["valid"] = True
                if test_child.tag == "input":
                    test["input"] = test_child.text
                if test_child.tag == "output":
                    test["output"] = test_child.text
                if test_child.tag == "error":
                    test["error"] = test_child.text
            tests.append(test)

    return handle_example(schema_type, schema, tests)


def handle_example(schema_type, raw_schema, tests):
    if schema_type == "yaml":
        schema = yaml.safe_load(raw_schema)
    dbg("What's the schema?", schema)
    for test in tests:
        input_doc = yaml.safe_load(test["input"])
        if test.get("valid"):
            test_normalize(schema, input_doc, input_doc)
        elif "output" in test:
            test_normalize(schema, input_doc, yaml.safe_load(test["output"]))
        elif "error" in test:
            error_expr = "errors." + test["error"]
            expected_error = eval(error_expr, {"errors": E})
            test["expected_error"] = expected_error
            try:
                received = normalize_schema(schema, input_doc)
            except E.SureError as sure_error:
                if sure_error != expected_error:
                    dbg("[ERROR IN EXAMPLE - ERROR NOT MATCHED")
                    dbg("received:", sure_error)
                    dbg("expected:", expected_error)
                    raise Exception("no good")
            else:
                dbg("[ERROR IN EXAMPLE - ERROR NOT RAISED]")
                dbg("received:", received)
                dbg("expected:", expected_error)
                raise Exception("no good")

    return render_examples(schema_type, raw_schema, tests)


def test_normalize(schema, input_doc, expected):
    received = normalize_schema(schema, input_doc)
    if received != expected:
        dbg("[ERROR IN EXAMPLE]")
        dbg("received:", received)
        dbg("expected:", expected)
        raise Exception("no good")


def render_examples(schema_type, raw_schema, tests):

    raw_schema = raw_schema.strip()
    tests = [
        test_template.format(
            input=test["input"],
            input_type="Valid input" if "valid" in test else "Input",
            output_or_error=format_output(test),
        )
        for test in tests
    ]

    tests = "".join(tests)
    output = template.format(
        schema_type=schema_type, raw_schema=html.escape(raw_schema), tests=tests
    )
    dbg(output)
    return output


def format_output(test):
    if "output" in test:
        return output_template.format(output=html.escape(test["output"]))
    elif "error" in test:
        return error_template.format(error=html.escape(str(test["expected_error"])))
    elif test.get("valid"):
        return ""
    else:
        raise Exception("Unknown output type for {}".format(test))


template = textwrap.dedent(
    """
    <div class="sureberus-example">
    <div class="sureberus-schema">
        <header>{schema_type} schema</header>
        <div class="sureberus-code-content">{raw_schema}</div>
    </div>
    <div class="sureberus-tests">{tests}</div>
    </div>
    """
)

test_template = textwrap.dedent(
    """
    <div class="sureberus-test">
    <div class="sureberus-input">
        <header>{input_type}</header>
        <div class="sureberus-code-content">{input}</div>
    </div>
    {output_or_error}
    </div>
    """
)

output_template = textwrap.dedent(
    """
    <div class="sureberus-output">
        <header>Output</header>
        <div class="sureberus-code-content">{output}</div>
    </div>
    """
)

error_template = textwrap.dedent(
    """
    <div class="sureberus-error">
        <header>Error</header>
        <div class="sureberus-code-content">{error}</div>
    </div>
    """
)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        dbg("Oh no!", e)
        import traceback

        traceback.print_exc(file=_debug_f)
        sys.exit(3)
