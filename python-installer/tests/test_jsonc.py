"""Tests for runlog_install.jsonc — stdlib-only JSONC round-trip helper."""

from runlog_install.jsonc import parse, add_to_object, remove_from_object


# ---------------------------------------------------------------------------
# 1. parse — line comments
# ---------------------------------------------------------------------------

def test_parse_line_comment():
    text = '// this is a comment\n{"a": 1}'
    assert parse(text) == {"a": 1}


def test_parse_line_comment_inline():
    text = '{\n  "a": 1 // inline comment\n}'
    assert parse(text) == {"a": 1}


# ---------------------------------------------------------------------------
# 2. parse — block comments
# ---------------------------------------------------------------------------

def test_parse_block_comment():
    text = '/* block */\n{"b": 2}'
    assert parse(text) == {"b": 2}


def test_parse_block_comment_multiline():
    text = '{\n  /* multi\n     line */\n  "c": 3\n}'
    assert parse(text) == {"c": 3}


# ---------------------------------------------------------------------------
# 3. parse — does NOT strip // inside a string
# ---------------------------------------------------------------------------

def test_parse_comment_marker_inside_string_preserved():
    text = '{"url": "https://example.com/path"}'
    result = parse(text)
    assert result["url"] == "https://example.com/path"


def test_parse_comment_slash_slash_inside_string_preserved():
    text = '{"note": "a // b"}'
    result = parse(text)
    assert result["note"] == "a // b"


# ---------------------------------------------------------------------------
# 4. parse — trailing commas
# ---------------------------------------------------------------------------

def test_parse_trailing_comma_object():
    text = '{"x": 1,}'
    assert parse(text) == {"x": 1}


def test_parse_trailing_comma_array():
    text = '[1, 2, 3,]'
    assert parse(text) == [1, 2, 3]


def test_parse_trailing_comma_nested():
    text = '{"a": [1, 2,], "b": {"c": 3,},}'
    assert parse(text) == {"a": [1, 2], "b": {"c": 3}}


# ---------------------------------------------------------------------------
# 5. parse — round-trips a JSONC fixture with comments to a plain dict
# ---------------------------------------------------------------------------

def test_parse_jsonc_fixture():
    fixture = """\
// Claude Code MCP server config
{
  /* servers section */
  "mcpServers": {
    "runlog": {
      "command": "npx", // launch via npx
      "args": ["runlog-mcp"]
    }
  }
}
"""
    result = parse(fixture)
    assert result == {
        "mcpServers": {
            "runlog": {
                "command": "npx",
                "args": ["runlog-mcp"],
            }
        }
    }


# ---------------------------------------------------------------------------
# 6. add_to_object — adds a key to an empty top-level object
# ---------------------------------------------------------------------------

def test_add_to_empty_object():
    text = '{}'
    result = add_to_object(text, (), "name", "runlog")
    assert '"name"' in result
    assert '"runlog"' in result
    assert parse(result) == {"name": "runlog"}


# ---------------------------------------------------------------------------
# 7. add_to_object — adds a key to a nested object (path length ≥ 2)
# ---------------------------------------------------------------------------

def test_add_to_nested_object():
    text = '{\n  "mcpServers": {\n    "existing": {}\n  }\n}'
    result = add_to_object(text, ("mcpServers",), "runlog", {"command": "npx"})
    parsed = parse(result)
    assert "runlog" in parsed["mcpServers"]
    assert parsed["mcpServers"]["runlog"] == {"command": "npx"}
    # existing key must still be present
    assert "existing" in parsed["mcpServers"]


# ---------------------------------------------------------------------------
# 8. add_to_object — preserves a // comment above the modified object
# ---------------------------------------------------------------------------

def test_add_to_object_preserves_comments():
    text = """\
// top-level comment
{
  // servers below
  "mcpServers": {}
}
"""
    result = add_to_object(text, ("mcpServers",), "runlog", {"command": "npx"})
    assert "// top-level comment" in result
    assert "// servers below" in result
    assert parse(result)["mcpServers"]["runlog"] == {"command": "npx"}


# ---------------------------------------------------------------------------
# 9. remove_from_object — removes a key, keeping siblings and comments intact
# ---------------------------------------------------------------------------

def test_remove_from_object_keeps_siblings():
    text = """\
{
  "mcpServers": {
    "keep": {"command": "keep-cmd"},
    "remove": {"command": "remove-cmd"}
  }
}
"""
    result = remove_from_object(text, ("mcpServers",), "remove")
    parsed = parse(result)
    assert "keep" in parsed["mcpServers"]
    assert "remove" not in parsed["mcpServers"]


def test_remove_from_object_preserves_comment():
    text = """\
// header comment
{
  "mcpServers": {
    "a": {},
    "b": {}
  }
}
"""
    result = remove_from_object(text, ("mcpServers",), "b")
    assert "// header comment" in result
    parsed = parse(result)
    assert "a" in parsed["mcpServers"]
    assert "b" not in parsed["mcpServers"]


# ---------------------------------------------------------------------------
# 10. remove_from_object — idempotent when key is absent
# ---------------------------------------------------------------------------

def test_remove_from_object_idempotent_absent_key():
    text = '{\n  "mcpServers": {\n    "a": {}\n  }\n}'
    result = remove_from_object(text, ("mcpServers",), "nonexistent")
    assert result == text


def test_remove_from_object_idempotent_absent_path():
    text = '{"other": {}}'
    result = remove_from_object(text, ("mcpServers",), "runlog")
    assert result == text


# ---------------------------------------------------------------------------
# 11. Round trip: parse(add_to_object(...)) reflects the change
# ---------------------------------------------------------------------------

def test_round_trip_add():
    text = '{\n  "mcpServers": {}\n}'
    result = add_to_object(text, ("mcpServers",), "runlog", {"command": "npx", "args": []})
    parsed = parse(result)
    assert parsed["mcpServers"]["runlog"] == {"command": "npx", "args": []}


# ---------------------------------------------------------------------------
# 12. Round trip: parse(remove_from_object(...)) no longer contains removed key
# ---------------------------------------------------------------------------

def test_round_trip_remove():
    text = """\
{
  "mcpServers": {
    "runlog": {"command": "npx"},
    "other": {"command": "cmd"}
  }
}
"""
    result = remove_from_object(text, ("mcpServers",), "runlog")
    parsed = parse(result)
    assert "runlog" not in parsed["mcpServers"]
    assert "other" in parsed["mcpServers"]


# ---------------------------------------------------------------------------
# 13. add_to_object — replace existing value in-place
# ---------------------------------------------------------------------------

def test_add_to_object_replaces_existing_key():
    text = '{\n  "mcpServers": {\n    "runlog": {"command": "old"}\n  }\n}'
    result = add_to_object(text, ("mcpServers",), "runlog", {"command": "new"})
    parsed = parse(result)
    assert parsed["mcpServers"]["runlog"]["command"] == "new"
    # Should appear only once
    assert result.count('"runlog"') == 1


# ---------------------------------------------------------------------------
# 14. add_to_object — creates missing top-level key_path segment
# ---------------------------------------------------------------------------

def test_add_to_object_creates_missing_top_level_segment():
    text = '{\n  "other": 1\n}'
    result = add_to_object(text, ("mcpServers",), "runlog", {"command": "npx"})
    parsed = parse(result)
    assert parsed["mcpServers"]["runlog"] == {"command": "npx"}
    assert parsed["other"] == 1
