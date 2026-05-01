---
description: Author and submit a Runlog entry from the most recent debugging finding — drives the local Ed25519-signed verifier, decodes typed rejection reasons, iterates to status:verified, then calls runlog_submit.
argument-hint: (no arguments — operates on the most recent third-party-system gotcha in the current session)
---

# /runlog:publish

Load the `runlog-author` skill and run its four-step author flow against the most recent external-dependency finding in the current Claude Code session.

The skill body lives at `runlog-author/SKILL.md` (canonical) and `claude-code/runlog-author.md` (Claude-Code-specific orchestration). Both must be honoured: the four-step flow (Classify+Search → Draft → Local verify loop → Sign+Submit), the four-point client contract, the retry cap on the verification loop, and the MUST-NOT list are all inherited from the canonical body. The Claude Code adapter only swaps orchestration glue (Bash dispatch for the local verifier, slash-command invocation).

If multiple findings are worth capturing at session-end rather than just the most recent one, prefer `/runlog:harvest` instead — it scans the whole session and routes selected candidates back through this same author flow.
