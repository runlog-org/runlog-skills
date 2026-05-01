---
description: End-of-session retrospective Runlog submission — scan the session for missed external-dependency findings and route picks through the verifier + runlog_submit pipeline.
argument-hint: (no arguments — scans the current session)
---

# /runlog:harvest

Load the `runlog-harvest` skill and run its four-step retrospective flow against the current Claude Code session.

The skill body lives at `runlog-harvest/SKILL.md` (canonical) and `claude-code/runlog-harvest.md` (Claude-Code-specific orchestration). Both must be honoured: the four-step flow (Scan → Score+Dedup → Pick → Route-to-author), the four-point classification check, the score floor (≥ 0.7), the comma-select picker grammar, and the MUST-NOT list are all inherited from the canonical body. The Claude Code adapter only swaps orchestration glue (Bash dispatch, draft persistence at `.runlog-harvest/`, slash-command invocation).

Selected candidates route through `runlog-author/SKILL.md` at its Step 2; harvest does not have its own verifier loop or submit path.
