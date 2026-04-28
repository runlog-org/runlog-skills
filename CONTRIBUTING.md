# Contributing to runlog-skills

Thanks for considering a contribution. This repo ships **drop-in MCP client skills** for nine agent frameworks; the bar for changes is "does it preserve the cross-vendor contract and stay aligned with the canonical bodies?"

## Adding a new vendor adapter

1. **Read the contracts first.** Every adapter MUST honour:
   - [`common/four-point-client-contract.md`](./common/four-point-client-contract.md) — read+write client invariants (team-memory-first, external-only, route learnings, dependency manifest).
   - [`common/runlog-author-contract.md`](./common/runlog-author-contract.md) — write-side submission-flow rules.
2. **Use the reference adapter as a template.** Start from [`claude-code/SKILL.md`](./claude-code/SKILL.md) for the read side and [`runlog-author/SKILL.md`](./runlog-author/SKILL.md) for the write side. Vendor-specific glue (MCP config shape, rules-file path, tool-use API) lives in the **Setup** section and a few "VERIFY against current vendor docs" callouts; the rest of the body is deliberately ~80% identical across vendors.
3. **Create three files** under `<vendor>/`:
   - `SKILL.md` — read-side body
   - `runlog-author.md` — write-side body
   - `README.md` — Quickstart, install path, and links back to the two `common/` contracts
4. **Register it** in the top-level [`README.md`](./README.md) vendor matrix and in [`installer/index.js`](./installer/index.js).

## Updating the cross-vendor contract

When `common/four-point-client-contract.md` or `common/runlog-author-contract.md` changes, re-sync each vendor's `SKILL.md` / `runlog-author.md` so the per-vendor wrappers stay in lockstep. Then re-sync the plugin-loader mirrors:

```sh
cp claude-code/SKILL.md skills/runlog/SKILL.md
cp runlog-author/SKILL.md skills/runlog-author/SKILL.md
```

(CIFS doesn't allow symlinks, so they're plain copies — see [`README.md`](./README.md) §Maintenance pattern.)

## Local checks before opening a PR

CI runs markdown-lint and a dead-link checker on every push and pull request — see [`.github/workflows/ci.yml`](./.github/workflows/ci.yml). To run them locally:

```sh
# Markdown lint (matches CI config)
npx markdownlint-cli2 "**/*.md" "!skills/**" "!**/node_modules/**"

# Dead-link check (requires lychee installed locally)
lychee --exclude-path skills './**/*.md'
```

The `installer/` package is checked too — `cd installer && npm pack --dry-run && node --check index.js`.

## Commit + PR

- Atomic, focused commits. One vendor adapter per commit when adding new vendors.
- Reference the relevant `[F##]` / `[B##]` backlog item in the message body when applicable.
- Sign-off / Co-Authored-By lines are not required.
