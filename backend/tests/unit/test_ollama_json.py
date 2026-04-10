import json

import pytest

from app.services.ollama import _extract_json_object, _fix_invalid_escapes_inside_json_strings


def test_fix_underbrace_not_unicode_escape() -> None:
    raw = r'{"body": "Use \underbrace{x}_a"}'
    fixed = _fix_invalid_escapes_inside_json_strings(raw)
    data = json.loads(fixed)
    assert "underbrace" in data["body"]
    assert not data["body"].startswith("\\")


def test_extract_json_with_latex_underbrace() -> None:
    text = 'Here is JSON:\n{"title": "Eq", "body": "\\\\underbrace{a+b}"}'
    # Model might emit single backslash before underbrace inside string
    text_bad = 'Here is JSON:\n{"title": "Eq", "body": "\\underbrace{a+b}"}'
    out = _extract_json_object(text_bad)
    assert out["title"] == "Eq"
    assert "underbrace" in out["body"]


def test_valid_unicode_escape_preserved() -> None:
    raw = '{"x": "\\u00e9"}'
    fixed = _fix_invalid_escapes_inside_json_strings(raw)
    assert json.loads(fixed)["x"] == "é"


def test_valid_newline_escape_preserved() -> None:
    raw = '{"x": "a\\nb"}'
    fixed = _fix_invalid_escapes_inside_json_strings(raw)
    assert json.loads(fixed)["x"] == "a\nb"


def test_extract_plain_valid() -> None:
    out = _extract_json_object('prefix {"a": 1} suffix')
    assert out == {"a": 1}


def test_extract_raises_on_garbage() -> None:
    with pytest.raises(ValueError, match="No JSON object"):
        _extract_json_object("no braces here")
