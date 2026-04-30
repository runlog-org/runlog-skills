"""
jsonc.py — stdlib-only JSONC (JSON-with-comments) round-trip helper.

Public API:
  parse(text)                          -> Any
  add_to_object(text, key_path, key, value) -> str
  remove_from_object(text, key_path, key)   -> str
"""

from __future__ import annotations

import json
import re
from typing import Any


# ---------------------------------------------------------------------------
# Token types produced by _tokenize
# ---------------------------------------------------------------------------
_STR   = "STR"    # JSON string (including delimiters)
_LINE  = "LINE"   # // comment
_BLOCK = "BLOCK"  # /* */ comment
_OTHER = "OTHER"  # anything else


def _tokenize(text: str):
    """Yield (kind, start, end) tuples covering every character of *text* exactly once."""
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        # String literal
        if c == '"':
            j = i + 1
            while j < n:
                if text[j] == '\\':
                    j += 2
                    continue
                if text[j] == '"':
                    j += 1
                    break
                j += 1
            yield (_STR, i, j)
            i = j
        # Line comment
        elif c == '/' and i + 1 < n and text[i + 1] == '/':
            j = text.find('\n', i)
            j = j + 1 if j != -1 else n
            yield (_LINE, i, j)
            i = j
        # Block comment
        elif c == '/' and i + 1 < n and text[i + 1] == '*':
            j = text.find('*/', i + 2)
            j = j + 2 if j != -1 else n
            yield (_BLOCK, i, j)
            i = j
        else:
            # Emit runs of plain characters for speed
            j = i + 1
            while j < n and text[j] not in ('"', '/'):
                j += 1
            yield (_OTHER, i, j)
            i = j


def _strip_comments(text: str) -> str:
    """Remove // and /* */ comments, preserving strings."""
    parts: list[str] = []
    for kind, start, end in _tokenize(text):
        if kind in (_LINE, _BLOCK):
            # Replace block comments with spaces to preserve position-independent
            # parsing; replace line comment with newline so line counting works.
            if kind == _LINE:
                parts.append('\n')
            else:
                # Preserve newlines inside block comments so line numbers stay valid.
                inner = text[start:end]
                parts.append(re.sub(r'[^\n]', ' ', inner))
        else:
            parts.append(text[start:end])
    return ''.join(parts)


def _strip_trailing_commas(text: str) -> str:
    """Remove trailing commas before } or ] that are not inside strings/comments."""
    # After comment stripping we only need to handle strings.
    # Pattern: comma, optional whitespace/newlines, then } or ]
    return re.sub(r',(\s*[}\]])', r'\1', text)


# ---------------------------------------------------------------------------
# Public: parse
# ---------------------------------------------------------------------------

def parse(text: str) -> Any:
    """Parse JSONC text (strips comments and trailing commas, then json.loads)."""
    stripped = _strip_comments(text)
    stripped = _strip_trailing_commas(stripped)
    return json.loads(stripped)


# ---------------------------------------------------------------------------
# Internal helpers for surgical text manipulation
# ---------------------------------------------------------------------------

def _find_object_end(text: str, start: int) -> int:
    """
    Given that text[start] == '{', return the index of the matching '}'.
    Handles nested objects/arrays and skips strings and comments.
    """
    depth = 0
    for kind, s, e in _tokenize(text[start:]):
        if kind == _OTHER:
            for rel, ch in enumerate(text[start + s:start + e]):
                abs_i = start + s + rel
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return abs_i
    raise ValueError("Unmatched '{' at position %d" % start)


def _find_object_start(text: str, start: int) -> int:
    """Return the index of the first '{' at or after *start* (skipping strings/comments)."""
    for kind, s, e in _tokenize(text[start:]):
        if kind == _OTHER:
            idx = text.find('{', start + s, start + e)
            if idx != -1:
                return idx
    raise ValueError("No '{' found after position %d" % start)


def _navigate_to_object(text: str, key_path: tuple[str, ...]) -> tuple[int, int]:
    """
    Walk key_path in *text* and return (obj_start, obj_end) of the target object.
    Raises KeyError if a path segment is missing.
    """
    # Start at the root object
    obj_start = _find_object_start(text, 0)
    obj_end   = _find_object_end(text, obj_start)

    for key in key_path:
        inner = text[obj_start:obj_end + 1]
        # Find `"key"` inside the object body
        pattern = re.compile(r'"' + re.escape(key) + r'"\s*:')
        m = pattern.search(inner)
        if m is None:
            raise KeyError(key)
        after_colon = obj_start + m.end()
        # Skip whitespace/comments to reach the nested object
        next_obj = _find_object_start(text, after_colon)
        if next_obj > obj_end:
            raise KeyError(key)
        obj_start = next_obj
        obj_end   = _find_object_end(text, obj_start)

    return obj_start, obj_end


def _detect_indent(text: str, obj_start: int, obj_end: int) -> str:
    """
    Detect the indentation used by sibling keys inside the object.
    Falls back to two spaces.
    """
    inner = text[obj_start + 1:obj_end]
    # Look for a newline followed by spaces/tabs before a quote
    m = re.search(r'\n([ \t]+)"', inner)
    return m.group(1) if m else '  '


# ---------------------------------------------------------------------------
# Public: add_to_object
# ---------------------------------------------------------------------------

def add_to_object(
    text: str,
    key_path: tuple[str, ...],
    key: str,
    value: Any,
) -> str:
    """
    Surgically insert or replace "key": value inside the object at key_path.

    - Preserves all comments and whitespace outside the modified section.
    - If the key already exists its value is replaced in-place.
    - If a top-level key_path segment is missing the object is created there;
      deeper missing parents raise KeyError.
    """
    # Ensure top-level object exists; if not, bootstrap it at the root level.
    try:
        obj_start, obj_end = _navigate_to_object(text, key_path)
    except KeyError as exc:
        # Only handle a missing top-level key path segment.
        missing_key = exc.args[0]
        if len(key_path) == 1 and key_path[0] == missing_key:
            # Insert the missing top-level key with an empty object, then retry.
            root_start = _find_object_start(text, 0)
            root_end   = _find_object_end(text, root_start)
            indent     = _detect_indent(text, root_start, root_end)
            empty_entry = ',\n%s"%s": {}' % (indent, missing_key)
            # Insert before root closing brace
            text = text[:root_end] + empty_entry + text[root_end:]
            obj_start, obj_end = _navigate_to_object(text, key_path)
        else:
            raise

    indent = _detect_indent(text, obj_start, obj_end)

    # Check whether the key already exists inside this object.
    inner = text[obj_start:obj_end + 1]
    key_pattern = re.compile(r'"' + re.escape(key) + r'"\s*:')
    m = key_pattern.search(inner)

    if m:
        # Replace existing value in-place.
        # Find the value start (after the colon, skip whitespace).
        val_start_rel = m.end()
        # Skip whitespace tokens to locate value span
        # We'll use the tokenizer on the inner text to find value boundaries.
        inner_offset = obj_start + val_start_rel
        val_start_abs = inner_offset
        # Skip whitespace
        while val_start_abs < obj_end and text[val_start_abs] in (' ', '\t', '\n', '\r'):
            val_start_abs += 1
        val_end_abs = _value_end(text, val_start_abs, obj_end)
        new_value_text = json.dumps(value, indent=2)
        text = text[:val_start_abs] + new_value_text + text[val_end_abs:]
    else:
        # Append new key before closing brace.
        new_value_text = json.dumps(value, indent=2)
        # Indent multi-line values
        new_value_text = new_value_text.replace('\n', '\n' + indent)
        # Determine whether we need a leading comma.
        inner_stripped = text[obj_start + 1:obj_end].strip()
        # Remove comments to check if object has existing entries
        inner_no_comments = _strip_comments(text[obj_start + 1:obj_end]).strip()
        leading_comma = ',' if inner_no_comments else ''
        insertion = '%s\n%s"%s": %s\n' % (leading_comma, indent, key, new_value_text)
        text = text[:obj_end] + insertion + text[obj_end:]

    return text


def _value_end(text: str, start: int, limit: int) -> int:
    """
    Return the index one past the end of the JSON value starting at text[start].
    Works for strings, objects, arrays, and primitives (numbers, booleans, null).
    """
    if start >= limit:
        return start
    ch = text[start]
    if ch == '"':
        # String
        i = start + 1
        while i < limit:
            if text[i] == '\\':
                i += 2
                continue
            if text[i] == '"':
                return i + 1
            i += 1
        return i
    if ch == '{':
        return _find_object_end(text, start) + 1
    if ch == '[':
        # Array — find matching ]
        depth = 0
        for kind, s, e in _tokenize(text[start:]):
            if kind == _OTHER:
                for rel, c in enumerate(text[start + s:start + e]):
                    abs_i = start + s + rel
                    if c == '[':
                        depth += 1
                    elif c == ']':
                        depth -= 1
                        if depth == 0:
                            return abs_i + 1
        return limit
    # Primitive: read until comma, }, ], whitespace
    i = start
    while i < limit and text[i] not in (',', '}', ']', ' ', '\t', '\n', '\r'):
        i += 1
    return i


# ---------------------------------------------------------------------------
# Public: remove_from_object
# ---------------------------------------------------------------------------

def remove_from_object(text: str, key_path: tuple[str, ...], key: str) -> str:
    """
    Surgically delete "key": value from the object at key_path.
    Idempotent — returns text unchanged if the key is absent.
    Cleans up surrounding commas and preserves comments/whitespace elsewhere.
    """
    try:
        obj_start, obj_end = _navigate_to_object(text, key_path)
    except KeyError:
        return text

    inner = text[obj_start:obj_end + 1]
    key_pattern = re.compile(r'"' + re.escape(key) + r'"\s*:')
    m = key_pattern.search(inner)
    if m is None:
        return text  # key absent — idempotent

    # Absolute positions
    key_abs_start = obj_start + m.start()
    val_start_rel = m.end()
    val_abs_start = obj_start + val_start_rel
    # Skip whitespace before value
    while val_abs_start < obj_end and text[val_abs_start] in (' ', '\t', '\n', '\r'):
        val_abs_start += 1
    val_abs_end = _value_end(text, val_abs_start, obj_end)

    # We need to remove: optional leading whitespace + key + colon + value + optional trailing comma
    # Walk back from key_abs_start to eat the preceding comma (or leading whitespace on the line)
    # Strategy: remove from just after the preceding comma (or from obj_start+1 if first entry)
    # to val_abs_end (+ optional trailing comma/whitespace).

    # Find the extent to remove: include surrounding comma and whitespace.
    # Case 1: there is a trailing comma after the value → remove entry + trailing comma
    # Case 2: there is a preceding comma → remove preceding comma + entry
    # Case 3: only entry → just remove content

    # Scan forward past val_abs_end skipping whitespace for a trailing comma
    scan = val_abs_end
    while scan < obj_end and text[scan] in (' ', '\t'):
        scan += 1
    has_trailing_comma = scan < obj_end and text[scan] == ','

    if has_trailing_comma:
        remove_end = scan + 1  # include the trailing comma
        # Also eat one newline/space after the comma if present
        if remove_end < obj_end and text[remove_end] in ('\n', '\r'):
            remove_end += 1
    else:
        remove_end = val_abs_end

    # Walk back from key_abs_start to find preceding comma or obj opening
    # eat whitespace backwards
    scan_back = key_abs_start - 1
    while scan_back > obj_start and text[scan_back] in (' ', '\t', '\n', '\r'):
        scan_back -= 1
    has_preceding_comma = scan_back > obj_start and text[scan_back] == ','

    if has_preceding_comma and not has_trailing_comma:
        remove_start = scan_back  # include the preceding comma
    else:
        # Include any leading whitespace/newline up to (but not past) prev newline
        remove_start = key_abs_start
        # back up over leading whitespace on the same line
        while remove_start > obj_start + 1 and text[remove_start - 1] in (' ', '\t'):
            remove_start -= 1
        # also eat the preceding newline
        if remove_start > obj_start + 1 and text[remove_start - 1] == '\n':
            remove_start -= 1

    text = text[:remove_start] + text[remove_end:]
    return text
