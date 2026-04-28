# skills/common/ — Cross-Vendor Invariants

Cross-vendor contract documents that every per-vendor adapter (Claude Code, Cursor, Cline, Continue, Windsurf, Aider, Copilot via VS Code MCP, JetBrains AI, Zed) references rather than re-authors. The "edit eight skills when the contract changes" problem solved by having one canonical source per invariant.

## What lives here today

| File | Purpose |
|---|---|
| [`four-point-client-contract.md`](./four-point-client-contract.md) | The four rules every Runlog client skill MUST follow. Inherited by both read-side and write-side skills. |
| [`runlog-author-contract.md`](./runlog-author-contract.md) | Author-side cross-vendor invariants. Strict superset of the four-point contract. Read alongside [`../runlog-author/SKILL.md`](../runlog-author/SKILL.md). |

## What lands here next

Tracked as part of `[F25]` (multi-vendor MCP skill coverage):

- `dependency-manifest.md` — wire shape for `session_manifest` extracted from `runlog-schema/manifest.schema.yaml` + `runlog/server/src/runlog/manifest/spec.py`. Today's adapters reference the schema/Pydantic spec directly.
- `reporting-conventions.md` — how outcomes (success / failure / partial) map to `runlog_report` calls, including how each vendor's runtime / language / package signal flows into the manifest.

These extractions land when the second per-vendor adapter ships and the duplication becomes painful — not before.
