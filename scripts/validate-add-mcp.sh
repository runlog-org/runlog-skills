#!/usr/bin/env bash
# Reproducible validation that `npx add-mcp` installs Runlog as a working
# MCP server across the hosts it supports natively (Claude Code, Cursor, Cline).
#
# Continue.dev is NOT covered by add-mcp — use the manual JSONC config in
# `continue/SKILL.md §Setup` for that host until M01-S02 extends our own
# installer to handle it.
#
# Usage:
#   ./validate-add-mcp.sh [--host claude-code|cursor|cline] [--global] [--check-only]
#
# Flags:
#   --host <h>      Target a specific host. If omitted, add-mcp auto-detects
#                   every installed supported host on the machine.
#   --global        Pass -g to add-mcp (write to global config rather than
#                   project-local).
#   --check-only    Skip the install — just print prereq + canonical-command
#                   checks. Useful for CI or pre-flight.
#
# Environment:
#   RUNLOG_API_KEY  Required for the post-install verification step. Get one
#                   at https://runlog.org/register.

set -euo pipefail

REGISTRY_URL="https://registry.modelcontextprotocol.io/v0/servers?search=org.runlog/runlog"
RUNLOG_MCP_URL="https://api.runlog.org/mcp"
SUPPORTED_HOSTS=(claude-code cursor cline)

host=""
global=0
check_only=0

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
warn() { printf 'warn:  %s\n' "$*" >&2; }
ok()   { printf 'ok:    %s\n' "$*"; }
step() { printf '\n--- %s ---\n' "$*"; }

usage() {
  sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)       host="${2:-}"; shift 2 ;;
    --global)     global=1; shift ;;
    --check-only) check_only=1; shift ;;
    -h|--help)    usage 0 ;;
    *)            usage 1 ;;
  esac
done

if [[ -n "$host" ]]; then
  matched=0
  for h in "${SUPPORTED_HOSTS[@]}"; do
    [[ "$h" == "$host" ]] && matched=1 && break
  done
  if [[ $matched -eq 0 ]]; then
    die "host '$host' is not in add-mcp's Runlog-supported set: ${SUPPORTED_HOSTS[*]}"
  fi
fi

step "Prereq checks"

command -v node >/dev/null 2>&1 || die "node not found in PATH (install Node.js 18+)"
ok "node: $(node --version)"

command -v npx >/dev/null 2>&1 || die "npx not found in PATH (ships with Node.js)"
ok "npx: $(npx --version)"

if [[ -z "${RUNLOG_API_KEY:-}" ]]; then
  warn "RUNLOG_API_KEY not set — needed for the post-install runlog_search check"
  warn "  set it with: export RUNLOG_API_KEY=sk-runlog-<your-key>"
  warn "  get one at:  https://runlog.org/register"
else
  if [[ "$RUNLOG_API_KEY" =~ ^sk-runlog-[a-z0-9]{12}-[a-z0-9]{32}$ ]]; then
    ok "RUNLOG_API_KEY: format matches sk-runlog-<id12>-<secret32>"
  else
    warn "RUNLOG_API_KEY is set but doesn't match the expected sk-runlog-<id12>-<secret32> shape"
  fi
fi

step "Registry liveness"

if command -v curl >/dev/null 2>&1; then
  if curl -fsS --max-time 10 "$REGISTRY_URL" -o /dev/null; then
    ok "Registry returns 200 for org.runlog/runlog"
  else
    die "Registry query failed: $REGISTRY_URL"
  fi
else
  warn "curl not installed; skipping Registry liveness check"
fi

cmd=(npx add-mcp "$RUNLOG_MCP_URL")
[[ -n "$host" ]] && cmd+=(-a "$host")
[[ $global -eq 1 ]] && cmd+=(-g)

step "Canonical install command"
printf '  %s\n' "${cmd[*]}"

if [[ $check_only -eq 1 ]]; then
  step "Check-only mode — skipping install"
  exit 0
fi

step "Run install (interactive)"

printf 'About to run: %s\n' "${cmd[*]}"
printf 'Continue? [y/N] '
read -r reply
case "$reply" in
  [yY]|[yY][eE][sS]) ;;
  *) die "aborted by user" ;;
esac

"${cmd[@]}"

step "Post-install verification (manual)"

cat <<EOF
add-mcp has written the Runlog config. Three things still need to be confirmed
by hand — these can't be checked from this script:

  1. Restart the target host(s) so the new MCP config is loaded:
     - Claude Code: \`claude mcp list\` should show \`runlog\` as connected.
     - Cursor:      Settings → Cursor Settings → MCP → expect \`runlog\` connected
                    with three tools (runlog_search, runlog_submit, runlog_report).
     - Cline:       MCP Servers panel in the Cline VS Code extension; same three
                    tools should appear.

  2. From the host's agent, ask:
       "Can you call runlog_search with the query 'stripe webhook'?"
     A connected server returns a list of hits. An auth error means RUNLOG_API_KEY
     is not propagating into the host's environment — re-source your shell rc
     before launching the host, or paste the literal key into the config.

  3. (Optional) Diff the host's MCP config against the canonical shape:
     - Claude Code: ~/.claude/settings.json
     - Cursor:      ~/.cursor/mcp.json (global) or .cursor/mcp.json (project)
     - Cline:       see SKILL.md §3 for the OS-specific globalStorage path
     Confirm the \`runlog\` block matches the manifest published at
     https://registry.modelcontextprotocol.io/v0/servers?search=org.runlog/runlog

If any of these fail, capture the symptom in \`.hv/KNOWLEDGE.md\` topic
*Build & Tooling* so subsequent runs of this script can warn about it.
EOF
