"""Tests for runlog_install.yamlc — stdlib-only YAML list-of-dicts helper."""

from __future__ import annotations

from runlog_install.yamlc import add_to_list, remove_from_list


# ---------------------------------------------------------------------------
# Shared fixtures (plain dicts / strings, no pytest fixtures library)
# ---------------------------------------------------------------------------

RUNLOG_ITEM = {
    "name": "runlog",
    "url": "https://api.runlog.org/mcp",
    "headers": {"Authorization": "Bearer sk-test-key"},
}


# ---------------------------------------------------------------------------
# 1. add_to_list — no list_key present → key block appended at end
# ---------------------------------------------------------------------------

def test_add_creates_new_key_block_when_absent():
    text = "rules:\n  - do not lie\n"
    result = add_to_list(text, "mcpServers", "name", "runlog", RUNLOG_ITEM)
    assert "mcpServers:" in result
    assert "runlog" in result
    assert "https://api.runlog.org/mcp" in result
    # Original content preserved byte-for-byte.
    assert result.startswith("rules:\n  - do not lie\n")


def test_add_creates_new_key_block_at_end_of_file_no_trailing_newline():
    text = "rules:\n  - do not lie"
    result = add_to_list(text, "mcpServers", "name", "runlog", {"name": "runlog", "url": "u"})
    assert "mcpServers:" in result
    assert result.index("rules:") < result.index("mcpServers:")


def test_add_creates_new_key_block_on_empty_file():
    result = add_to_list("", "mcpServers", "name", "runlog", {"name": "runlog"})
    assert "mcpServers:" in result
    assert "runlog" in result


# ---------------------------------------------------------------------------
# 2. add_to_list — list_key exists with empty list → first item appears beneath
# ---------------------------------------------------------------------------

def test_add_first_item_to_empty_list():
    text = "mcpServers:\n\nrules:\n  - something\n"
    result = add_to_list(text, "mcpServers", "name", "runlog", {"name": "runlog", "url": "u"})
    assert "- name:" in result or '- name: ' in result
    assert "runlog" in result
    # rules section preserved.
    assert "rules:" in result


def test_add_first_item_to_list_key_with_no_following_content():
    text = "mcpServers:\n"
    result = add_to_list(text, "mcpServers", "name", "runlog", {"name": "runlog"})
    assert "mcpServers:" in result
    assert "runlog" in result
    assert "- name:" in result or "- name: " in result


# ---------------------------------------------------------------------------
# 3. add_to_list — sibling item with different name → new item appended; sibling preserved
# ---------------------------------------------------------------------------

def test_add_appends_when_sibling_has_different_name():
    text = (
        "mcpServers:\n"
        "  - name: \"other-tool\"\n"
        "    url: \"https://other.example.com/mcp\"\n"
    )
    result = add_to_list(text, "mcpServers", "name", "runlog", {"name": "runlog", "url": "https://api.runlog.org/mcp"})
    assert "other-tool" in result
    assert "https://other.example.com/mcp" in result
    assert "runlog" in result
    assert "https://api.runlog.org/mcp" in result
    # sibling preserved byte-for-byte — its lines still appear verbatim.
    assert '  - name: "other-tool"' in result
    assert '    url: "https://other.example.com/mcp"' in result


def test_add_with_sibling_name_appears_after_sibling():
    text = (
        "mcpServers:\n"
        "  - name: \"other-tool\"\n"
        "    url: \"https://other.example.com/mcp\"\n"
    )
    result = add_to_list(text, "mcpServers", "name", "runlog", {"name": "runlog", "url": "u"})
    sibling_pos = result.index("other-tool")
    runlog_pos = result.index("runlog")
    assert sibling_pos < runlog_pos


# ---------------------------------------------------------------------------
# 4. add_to_list — item with same name already exists → replaced in place; siblings unchanged
# ---------------------------------------------------------------------------

def test_add_replaces_existing_item_in_place():
    text = (
        "mcpServers:\n"
        "  - name: \"other-tool\"\n"
        "    url: \"https://other.example.com/mcp\"\n"
        "  - name: \"runlog\"\n"
        "    url: \"https://old.runlog.org/mcp\"\n"
    )
    new_item = {"name": "runlog", "url": "https://api.runlog.org/mcp"}
    result = add_to_list(text, "mcpServers", "name", "runlog", new_item)

    # Old URL gone, new URL present.
    assert "https://old.runlog.org/mcp" not in result
    assert "https://api.runlog.org/mcp" in result

    # Sibling preserved byte-for-byte.
    assert '  - name: "other-tool"' in result
    assert '    url: "https://other.example.com/mcp"' in result

    # "runlog" appears exactly once as a name value.
    assert result.count('"runlog"') == 1


def test_add_idempotent_same_item_twice():
    text = "mcpServers:\n"
    item = {"name": "runlog", "url": "u"}
    result1 = add_to_list(text, "mcpServers", "name", "runlog", item)
    result2 = add_to_list(result1, "mcpServers", "name", "runlog", item)
    assert result1 == result2


# ---------------------------------------------------------------------------
# 5. add_to_list — preserves YAML comments in the file
# ---------------------------------------------------------------------------

def test_add_preserves_comment_between_items():
    text = (
        "# this is the rules section\n"
        "rules:\n"
        "  - do not lie\n"
        "\n"
        "mcpServers:\n"
        "  - name: \"other-tool\"\n"
        "    url: \"https://other.example.com/mcp\"\n"
    )
    result = add_to_list(text, "mcpServers", "name", "runlog", {"name": "runlog", "url": "u"})
    assert "# this is the rules section" in result
    assert "rules:" in result


def test_add_preserves_comment_after_list():
    text = (
        "mcpServers:\n"
        "  - name: \"other-tool\"\n"
        "    url: \"https://other.example.com/mcp\"\n"
        "\n"
        "# end of file marker\n"
    )
    result = add_to_list(text, "mcpServers", "name", "runlog", {"name": "runlog", "url": "u"})
    assert "# end of file marker" in result


# ---------------------------------------------------------------------------
# 6. add_to_list — nested dict value renders as nested mapping
# ---------------------------------------------------------------------------

def test_add_renders_nested_dict_as_yaml_mapping():
    text = "mcpServers:\n"
    item = {
        "name": "runlog",
        "url": "https://api.runlog.org/mcp",
        "headers": {"Authorization": "Bearer sk-abc"},
    }
    result = add_to_list(text, "mcpServers", "name", "runlog", item)

    # The nested dict should render as a sub-mapping, not inline.
    assert "headers:" in result
    assert "Authorization:" in result
    assert "Bearer sk-abc" in result
    # Nested key should NOT appear on the same line as "headers:".
    headers_line = next(
        line for line in result.splitlines() if "headers:" in line
    )
    assert "Authorization" not in headers_line


def test_add_nested_dict_authorization_value_correct():
    text = "mcpServers:\n"
    item = {
        "name": "runlog",
        "headers": {"Authorization": "Bearer sk-abc"},
    }
    result = add_to_list(text, "mcpServers", "name", "runlog", item)
    assert '"Bearer sk-abc"' in result


# ---------------------------------------------------------------------------
# 7. add_to_list — 2-space indent canonical output
# ---------------------------------------------------------------------------

def test_add_uses_two_space_indent_canonical():
    text = "mcpServers:\n"
    item = {"name": "runlog", "url": "https://api.runlog.org/mcp"}
    result = add_to_list(text, "mcpServers", "name", "runlog", item)

    lines = result.splitlines()
    item_line = next(l for l in lines if "- name:" in l)
    # Should be indented with exactly 2 spaces before the dash.
    assert item_line.startswith("  - "), repr(item_line)

    url_line = next(l for l in lines if "url:" in l)
    # Continuation lines indented 4 spaces (2 for list indent + 2 for "- " width).
    assert url_line.startswith("    "), repr(url_line)


def test_add_respects_existing_4space_indent():
    text = (
        "mcpServers:\n"
        "    - name: \"existing\"\n"
        "      url: \"https://existing.example.com/mcp\"\n"
    )
    item = {"name": "runlog", "url": "https://api.runlog.org/mcp"}
    result = add_to_list(text, "mcpServers", "name", "runlog", item)
    item_line = next(l for l in result.splitlines() if "- name:" in l and "runlog" in l)
    assert item_line.startswith("    - "), repr(item_line)


# ---------------------------------------------------------------------------
# 8. remove_from_list — only item → list_key line remains, empty list
# ---------------------------------------------------------------------------

def test_remove_only_item_leaves_key_line():
    text = (
        "mcpServers:\n"
        "  - name: \"runlog\"\n"
        "    url: \"https://api.runlog.org/mcp\"\n"
    )
    result = remove_from_list(text, "mcpServers", "name", "runlog")
    assert "mcpServers:" in result
    assert "runlog" not in result
    assert "https://api.runlog.org/mcp" not in result


# ---------------------------------------------------------------------------
# 9. remove_from_list — multi-item list; siblings preserved with indent intact
# ---------------------------------------------------------------------------

def test_remove_from_multi_item_preserves_sibling():
    text = (
        "mcpServers:\n"
        "  - name: \"runlog\"\n"
        "    url: \"https://api.runlog.org/mcp\"\n"
        "  - name: \"other-tool\"\n"
        "    url: \"https://other.example.com/mcp\"\n"
    )
    result = remove_from_list(text, "mcpServers", "name", "runlog")
    assert "runlog" not in result
    assert "https://api.runlog.org/mcp" not in result
    # Sibling preserved byte-for-byte including its leading indent.
    assert '  - name: "other-tool"' in result
    assert '    url: "https://other.example.com/mcp"' in result


def test_remove_sibling_indent_regression():
    """Regression: removing an item must not corrupt leading indent on the next sibling."""
    text = (
        "mcpServers:\n"
        "  - name: \"remove-me\"\n"
        "    url: \"https://remove.example.com/mcp\"\n"
        "  - name: \"keep-me\"\n"
        "    url: \"https://keep.example.com/mcp\"\n"
    )
    result = remove_from_list(text, "mcpServers", "name", "remove-me")
    # The remaining sibling must still start with "  - " (2-space indent + dash).
    sibling_line = next(l for l in result.splitlines() if "keep-me" in l)
    assert sibling_line.startswith("  - "), repr(sibling_line)
    # url continuation must also have its indent intact.
    url_line = next(l for l in result.splitlines() if "keep.example.com" in l)
    assert url_line.startswith("    "), repr(url_line)


# ---------------------------------------------------------------------------
# 10. remove_from_list — list_key absent → text unchanged
# ---------------------------------------------------------------------------

def test_remove_when_key_absent_returns_unchanged():
    text = "rules:\n  - do not lie\n"
    result = remove_from_list(text, "mcpServers", "name", "runlog")
    assert result == text


# ---------------------------------------------------------------------------
# 11. remove_from_list — identifying_value not present → text unchanged
# ---------------------------------------------------------------------------

def test_remove_when_value_not_found_returns_unchanged():
    text = (
        "mcpServers:\n"
        "  - name: \"other-tool\"\n"
        "    url: \"https://other.example.com/mcp\"\n"
    )
    result = remove_from_list(text, "mcpServers", "name", "nonexistent")
    assert result == text


# ---------------------------------------------------------------------------
# 12. remove_from_list — preserves top-level sibling section after list
# ---------------------------------------------------------------------------

def test_remove_preserves_sibling_top_level_section():
    text = (
        "mcpServers:\n"
        "  - name: \"runlog\"\n"
        "    url: \"https://api.runlog.org/mcp\"\n"
        "  - name: \"other-tool\"\n"
        "    url: \"https://other.example.com/mcp\"\n"
        "\n"
        "rules:\n"
        "  - do not lie\n"
    )
    result = remove_from_list(text, "mcpServers", "name", "runlog")
    assert "rules:" in result
    assert "do not lie" in result
    assert "runlog" not in result


# ---------------------------------------------------------------------------
# 13. Structural sanity after add_to_list (no PyYAML — assert via string search)
# ---------------------------------------------------------------------------

def test_structural_sanity_after_add():
    """After add_to_list, key fields and comment text survive — no YAML parser needed."""
    comment = "# my custom server config"
    text = (
        f"{comment}\n"
        "mcpServers:\n"
        "  - name: \"existing\"\n"
        "    url: \"https://existing.example.com/mcp\"\n"
    )
    item = {
        "name": "runlog",
        "url": "https://api.runlog.org/mcp",
        "headers": {"Authorization": "Bearer sk-test"},
    }
    result = add_to_list(text, "mcpServers", "name", "runlog", item)

    # Comment survives.
    assert comment in result
    # Sibling survives.
    assert "existing" in result
    # New item fields present.
    assert '"runlog"' in result
    assert "https://api.runlog.org/mcp" in result
    assert "Authorization" in result
    assert "Bearer sk-test" in result


def test_remove_then_add_equivalent_to_single_add():
    """remove_from_list + add_to_list is functionally equivalent to a single add_to_list."""
    base = (
        "mcpServers:\n"
        "  - name: \"runlog\"\n"
        "    url: \"https://old.runlog.org/mcp\"\n"
    )
    item = {"name": "runlog", "url": "https://api.runlog.org/mcp"}

    # Path A: single add (replace in place).
    result_a = add_to_list(base, "mcpServers", "name", "runlog", item)

    # Path B: remove then add.
    removed = remove_from_list(base, "mcpServers", "name", "runlog")
    result_b = add_to_list(removed, "mcpServers", "name", "runlog", item)

    # Both must contain the new URL and not the old one.
    assert "https://api.runlog.org/mcp" in result_a
    assert "https://old.runlog.org/mcp" not in result_a
    assert "https://api.runlog.org/mcp" in result_b
    assert "https://old.runlog.org/mcp" not in result_b


def test_add_idempotent_structural():
    """Calling add_to_list twice with the same args yields identical text."""
    text = (
        "mcpServers:\n"
        "  - name: \"existing\"\n"
        "    url: \"https://existing.example.com/mcp\"\n"
    )
    item = {"name": "runlog", "url": "https://api.runlog.org/mcp"}
    result1 = add_to_list(text, "mcpServers", "name", "runlog", item)
    result2 = add_to_list(result1, "mcpServers", "name", "runlog", item)
    assert result1 == result2
