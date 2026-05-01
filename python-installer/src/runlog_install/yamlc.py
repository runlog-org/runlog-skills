"""
yamlc.py — stdlib-only YAML list-of-dicts helper.

Public API:
  add_to_list(text, list_key, identifying_key, identifying_value, item) -> str
  remove_from_list(text, list_key, identifying_key, identifying_value)  -> str

Both functions perform surgical string-splice edits that preserve user
comments, blank lines, and formatting outside the touched item.  They
assume YAML files where one top-level key maps to a sequence of mapping
items (e.g. Continue.dev ``~/.continue/config.yaml`` or Aider
``~/.aider.conf.yml``).

Supported leaf value types: str, int, bool, and one level of nested dict
whose own values are str/int/bool.

Stdlib-only — no PyYAML, no ruamel.  Uses ``re`` and ``json`` (for
string escaping only).
"""

from __future__ import annotations

import json
import re
from typing import Any


# ---------------------------------------------------------------------------
# Internal: locate the list block for list_key
# ---------------------------------------------------------------------------

def _find_list_block(text: str, list_key: str) -> re.Match | None:
    """Return a match for the ``list_key:`` header line, or None if absent.

    Matches the key at column 0 with nothing after the colon except optional
    whitespace/newline.  An inline ``[]`` value is treated as absent.
    """
    pattern = re.compile(
        r'^' + re.escape(list_key) + r'\s*:\s*$',
        re.MULTILINE,
    )
    return pattern.search(text)


def _list_block_span(text: str, key_match: re.Match) -> tuple[int, int]:
    """Return (block_start, block_end) covering all item lines after the key.

    ``block_start`` is the character index of the first character after the
    newline that ends the ``list_key:`` header line.  ``block_end`` is the
    index of the first character that belongs to a non-blank line at column 0
    (a sibling top-level key or EOF), or EOF if no such line exists.

    The returned span may be empty (block_start == block_end) if no indented
    lines follow the key.
    """
    # Start immediately after the newline that ends the key header.
    after_key = key_match.end()
    # Eat the trailing newline of the key line itself if present.
    if after_key < len(text) and text[after_key] == '\n':
        after_key += 1
    elif after_key < len(text) and text[after_key] == '\r':
        after_key += 1
        if after_key < len(text) and text[after_key] == '\n':
            after_key += 1

    block_start = after_key

    # Walk lines forward until we hit a non-blank line at column 0.
    pos = block_start
    n = len(text)
    while pos < n:
        # Find end of this line.
        eol = text.find('\n', pos)
        if eol == -1:
            eol = n - 1
        line = text[pos:eol + 1] if eol < n else text[pos:]

        stripped = line.lstrip('\r\n')
        if stripped == '' or stripped == '\n' or stripped == '\r\n':
            # Blank line — still part of the block.
            pos = eol + 1
            continue

        # Non-blank: check if it starts at column 0.
        if line[0] not in (' ', '\t', '\r', '\n'):
            # Column-0 non-blank line — end of this list block.
            break

        pos = eol + 1

    block_end = pos
    return block_start, block_end


# ---------------------------------------------------------------------------
# Internal: split block into item spans
# ---------------------------------------------------------------------------

def _item_indent(block: str) -> str:
    """Return the indent string (leading spaces) used by item ``- `` lines."""
    m = re.search(r'^( +)- ', block, re.MULTILINE)
    return m.group(1) if m else '  '


def _split_items(block: str) -> list[tuple[int, int]]:
    """Return a list of (start, end) char-offsets within *block* for each item.

    Each item starts at its ``- `` line and ends just before the next sibling
    ``- `` line (at the same indent) or at the end of *block*.

    If *block* is empty or has no ``- `` lines, returns an empty list.
    """
    if not block.strip():
        return []

    indent = _item_indent(block)
    # Pattern for a line that starts a new item at the discovered indent.
    item_start_pat = re.compile(
        r'^' + re.escape(indent) + r'- ',
        re.MULTILINE,
    )

    starts = [m.start() for m in item_start_pat.finditer(block)]
    if not starts:
        return []

    spans: list[tuple[int, int]] = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(block)
        spans.append((s, e))
    return spans


# ---------------------------------------------------------------------------
# Internal: extract identifying value from an item body
# ---------------------------------------------------------------------------

def _item_identifying_value(item_body: str, identifying_key: str) -> str | None:
    """Return the string value of ``identifying_key`` within *item_body*, or None."""
    pat = re.compile(
        r'^\s*(?:- )?' + re.escape(identifying_key) + r':\s*(.+?)\s*$',
        re.MULTILINE,
    )
    m = pat.search(item_body)
    if m is None:
        return None
    val = m.group(1)
    # Strip outer quotes (single or double).
    if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
        val = val[1:-1]
    elif len(val) >= 2 and val[0] == "'" and val[-1] == "'":
        val = val[1:-1]
    return val


# ---------------------------------------------------------------------------
# Internal: render a dict item as YAML lines
# ---------------------------------------------------------------------------

def _render_value(v: Any) -> str:
    """Render a scalar value as a YAML-compatible string (no trailing newline)."""
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, int):
        return str(v)
    # String: always double-quoted using JSON escaping.
    return json.dumps(v)


def _render_item(item: dict, indent: str = '  ') -> str:
    """Render *item* as YAML lines for insertion into the list block.

    Returns a string that starts with ``{indent}- `` and ends with a newline.
    The *indent* should match the indentation used by sibling items.

    Top-level item:
        {indent}- key1: value1
        {indent}  key2: value2
    Nested dict value:
        {indent}  nested_key:
        {indent}    sub_key: value
    """
    child_indent = indent + '  '  # two additional spaces for continuation lines
    nested_indent = child_indent + '  '  # another two for nested dict values

    lines: list[str] = []
    first = True
    for k, v in item.items():
        if isinstance(v, dict):
            if first:
                lines.append(f'{indent}- {k}:\n')
                first = False
            else:
                lines.append(f'{child_indent}{k}:\n')
            for sk, sv in v.items():
                lines.append(f'{nested_indent}{sk}: {_render_value(sv)}\n')
        else:
            if first:
                lines.append(f'{indent}- {k}: {_render_value(v)}\n')
                first = False
            else:
                lines.append(f'{child_indent}{k}: {_render_value(v)}\n')
    return ''.join(lines)


# ---------------------------------------------------------------------------
# Public: add_to_list
# ---------------------------------------------------------------------------

def add_to_list(
    text: str,
    list_key: str,
    identifying_key: str,
    identifying_value: str,
    item: dict,
) -> str:
    """Add or replace an item in a YAML list at top-level key ``list_key``.

    The list is a sequence of mapping items.  An "item" matches the target if
    item[identifying_key] == identifying_value (string equality).  If a match
    exists, replace it in place.  Otherwise append the new item to the end of
    the list.

    If ``list_key`` is not present in ``text``, append a new top-level block::

        list_key:
          - <rendered item>

    The new block is appended to the end of the file (with a leading blank
    line if the file isn't already terminated by one).

    Item rendering: dict values may be strings, ints, bools, or one level of
    nested dicts whose values are strings/ints/bools.  Strings are emitted
    double-quoted with standard JSON escapes.  Indentation uses 2 spaces per
    level.  Item ordering inside the rendered dict matches insertion order
    of the ``item`` dict.

    The function preserves text outside the touched item byte-for-byte
    (comments, blank lines, other top-level sections).
    """
    key_match = _find_list_block(text, list_key)

    if key_match is None:
        # Append a new top-level block.
        rendered = _render_item(item, indent='  ')
        separator = '' if (not text or text.endswith('\n\n')) else (
            '\n' if text.endswith('\n') else '\n\n'
        )
        tail = f'{list_key}:\n{rendered}'
        return text + separator + tail

    block_start, block_end = _list_block_span(text, key_match)
    block = text[block_start:block_end]

    indent = _item_indent(block) if block.strip() else '  '
    rendered = _render_item(item, indent=indent)

    item_spans = _split_items(block)

    # Look for an existing item with the matching identifying value.
    for span_start, span_end in item_spans:
        item_body = block[span_start:span_end]
        val = _item_identifying_value(item_body, identifying_key)
        if val == identifying_value:
            # Replace this item in place.
            new_block = block[:span_start] + rendered + block[span_end:]
            return text[:block_start] + new_block + text[block_end:]

    # No match — append after the last item (i.e. at the end of block).
    # Trim trailing blank lines from the block before appending so we don't
    # accumulate extra blank lines on repeated calls.
    trimmed_block = block.rstrip('\n')
    new_block = (trimmed_block + '\n' if trimmed_block else '') + rendered
    return text[:block_start] + new_block + text[block_end:]


# ---------------------------------------------------------------------------
# Public: remove_from_list
# ---------------------------------------------------------------------------

def remove_from_list(
    text: str,
    list_key: str,
    identifying_key: str,
    identifying_value: str,
) -> str:
    """Remove an item from a YAML list at top-level key ``list_key``.

    Locates the item where item[identifying_key] == identifying_value and
    deletes it (start of ``- `` line through the line before the next
    sibling list item, or end of the list block if it was the last item).
    Returns text unchanged if ``list_key`` is absent or no item matches.

    If removing the item leaves the list empty, the ``list_key:`` line is
    kept (with empty value) — callers can decide whether to also drop the
    key.  Trailing newlines are preserved.
    """
    key_match = _find_list_block(text, list_key)
    if key_match is None:
        return text

    block_start, block_end = _list_block_span(text, key_match)
    block = text[block_start:block_end]

    item_spans = _split_items(block)
    if not item_spans:
        return text

    for i, (span_start, span_end) in enumerate(item_spans):
        item_body = block[span_start:span_end]
        val = _item_identifying_value(item_body, identifying_key)
        if val != identifying_value:
            continue

        # Found — remove this item's span from block.
        new_block = block[:span_start] + block[span_end:]
        return text[:block_start] + new_block + text[block_end:]

    # No match.
    return text
