"""skill_writer.py — shared helper for placing the 3-skill Runlog bundle.

Each host adapter exposes a ``skill_sources`` list of
``(source_path, dest_path, section_label)`` tuples covering the three
Runlog skills (read, author, harvest).  This module centralises the logic
for both layouts:

  - **Separate-file layout** — every spec has a distinct ``dest_path``;
    each source file is copied to its own destination (e.g. claude-code's
    ``~/.claude/skills/runlog{,-author,-harvest}/SKILL.md``).
  - **Shared-file layout** — multiple specs share the same ``dest_path``;
    the source bodies are concatenated with section headers derived from
    ``section_label`` (e.g. windsurf's ``~/.codeium/windsurf/globalrules``).

The grouping happens here so each host's ``install`` / ``uninstall`` is a
two-line call into ``write_skills`` / ``remove_skills``.

Stdlib-only — no third-party imports.
"""

from __future__ import annotations

from pathlib import Path

# A skill spec: (source path on disk, destination path, human section label).
SkillSpec = tuple[Path, Path, str]


def _section_header(label: str) -> str:
    """Return the standard section header used in shared-file concatenation."""
    return f"# === Runlog {label} skill ===\n\n"


def _validate_sources(skill_sources: list[SkillSpec], host_name: str) -> None:
    """Raise FileNotFoundError if any source file is missing."""
    for src, _dst, _label in skill_sources:
        if not src.is_file():
            raise FileNotFoundError(
                f"Source skill file not found for {host_name}: {src}"
            )


def write_skills(skill_sources: list[SkillSpec], host_name: str) -> None:
    """Write all three Runlog skill bodies to their destinations.

    Separate-file layout (each spec's ``dest_path`` is unique): each source
    is copied verbatim to its destination.

    Shared-file layout (multiple specs share a destination): the source
    bodies are concatenated with section headers (``# === Runlog <label>
    skill ===``) and written to the shared path in a single pass.
    """
    _validate_sources(skill_sources, host_name)

    # Group specs by destination path so shared-file hosts collapse to one write.
    grouped: dict[Path, list[SkillSpec]] = {}
    for spec in skill_sources:
        grouped.setdefault(spec[1], []).append(spec)

    for dst, specs in grouped.items():
        dst.parent.mkdir(parents=True, exist_ok=True)
        if len(specs) == 1:
            src, _dst, _label = specs[0]
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            # Shared file — concatenate the bodies with section headers.
            parts: list[str] = []
            for src, _dst, label in specs:
                parts.append(_section_header(label))
                parts.append(src.read_text(encoding="utf-8"))
                if not parts[-1].endswith("\n"):
                    parts.append("\n")
            dst.write_text("".join(parts), encoding="utf-8")


def remove_skills(
    skill_sources: list[SkillSpec],
    *,
    rmdir_stop: Path | None = None,
) -> None:
    """Remove all skill destinations.

    For each unique destination path: ``unlink(missing_ok=True)``, then walk
    upward removing empty parent dirs until either (a) a non-empty dir is
    hit, (b) ``rmdir_stop`` is reached, or (c) the filesystem root is hit.

    ``rmdir_stop`` is the boundary that must NOT be removed (e.g.
    ``~/.config/zed`` for ZedHost).  Pass ``None`` to attempt rmdir on the
    immediate parent only (matches the ``try: parent.rmdir()`` pattern used
    by single-skill hosts pre-refactor).
    """
    seen: set[Path] = set()
    for _src, dst, _label in skill_sources:
        if dst in seen:
            continue
        seen.add(dst)

        dst.unlink(missing_ok=True)

        if rmdir_stop is None:
            # Single-shot rmdir of the immediate parent; ignore failures.
            try:
                dst.parent.rmdir()
            except OSError:
                pass
            continue

        # Walk up, stopping at rmdir_stop or the filesystem root.
        parent = dst.parent
        while parent != rmdir_stop and parent != parent.parent:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
