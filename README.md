# skills/ — MCP Client Skills

**Future repo:** `runlog-skills` — public, MIT (planned)
**Content:** Agent skill files and MCP client configs
**Implements:** [`../docs/07-mcp-interface.md`](../docs/07-mcp-interface.md), plus the manifest conventions from [`../docs/03-verification-and-provenance.md`](../docs/03-verification-and-provenance.md) §6

Drop-in skill files so agents running Claude Code, Cursor, Cline, and other MCP clients can use Runlog without writing their own MCP plumbing. Each skill wraps `runlog_search`, `runlog_submit`, and `runlog_report` with the right framework-specific glue.

Also standardises how each agent framework tracks `kb:<id>` entries in its working session so the server's failure-attribution engine gets clean dependency manifests.

## Layout

- `claude-code/SKILL.md`
- `cursor/.cursorrules` (and/or custom rule file)
- `cline/…`
- `common/dependency-manifest.md` — agent-framework-agnostic spec for how to record retrievals
- `common/reporting-conventions.md` — success/failure reporting contract

## Depends on

- `../schema/` — referenced in documentation only (not as a code dep)
