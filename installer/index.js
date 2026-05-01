#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

const RAW_BASE = 'https://raw.githubusercontent.com/runlog-org/runlog-skills/main';

// Each vendor ships three skills: the read SKILL, the runlog-author write
// skill, and the runlog-harvest skill. For non-shared vendors each lands at
// its own target path. For shared vendors (single rules file) all three
// bodies are concatenated with section headers and printed for the user to
// merge.
const SKILL_LABELS = {
  read: 'Read skill (runlog)',
  author: 'Author skill (runlog-author)',
  harvest: 'Harvest skill (runlog-harvest)',
};

const VENDORS = {
  'claude-code': {
    sources: [
      {
        kind: 'read',
        source: 'claude-code/SKILL.md',
        target: '.claude/skills/runlog/SKILL.md',
        globalTarget: '~/.claude/skills/runlog/SKILL.md',
      },
      {
        kind: 'author',
        source: 'claude-code/runlog-author.md',
        target: '.claude/skills/runlog-author/SKILL.md',
        globalTarget: '~/.claude/skills/runlog-author/SKILL.md',
      },
      {
        kind: 'harvest',
        source: 'claude-code/runlog-harvest.md',
        target: '.claude/skills/runlog-harvest/SKILL.md',
        globalTarget: '~/.claude/skills/runlog-harvest/SKILL.md',
      },
    ],
    note: 'For Claude Code, prefer the plugin marketplace:\n  /plugin marketplace add runlog-org/runlog-skills\n  /plugin install runlog\nThe plugin also auto-registers the Runlog MCP server.',
  },
  cursor: {
    sources: [
      {
        kind: 'read',
        source: 'cursor/SKILL.md',
        target: '.cursor/rules/runlog.mdc',
        globalTarget: '~/.cursor/rules/runlog.mdc',
      },
      {
        kind: 'author',
        source: 'cursor/runlog-author.md',
        target: '.cursor/rules/runlog-author.mdc',
        globalTarget: '~/.cursor/rules/runlog-author.mdc',
      },
      {
        kind: 'harvest',
        source: 'cursor/runlog-harvest.md',
        target: '.cursor/rules/runlog-harvest.mdc',
        globalTarget: '~/.cursor/rules/runlog-harvest.mdc',
      },
    ],
  },
  cline: {
    sources: [
      { kind: 'read', source: 'cline/SKILL.md', target: '.clinerules/runlog.md' },
      { kind: 'author', source: 'cline/runlog-author.md', target: '.clinerules/runlog-author.md' },
      { kind: 'harvest', source: 'cline/runlog-harvest.md', target: '.clinerules/runlog-harvest.md' },
    ],
  },
  continue: {
    sources: [
      { kind: 'read', source: 'continue/SKILL.md', target: '.continue/rules/runlog.md' },
      { kind: 'author', source: 'continue/runlog-author.md', target: '.continue/rules/runlog-author.md' },
      { kind: 'harvest', source: 'continue/runlog-harvest.md', target: '.continue/rules/runlog-harvest.md' },
    ],
  },
  windsurf: {
    sources: [
      { kind: 'read', source: 'windsurf/SKILL.md' },
      { kind: 'author', source: 'windsurf/runlog-author.md' },
      { kind: 'harvest', source: 'windsurf/runlog-harvest.md' },
    ],
    target: '.windsurfrules',
    shared: true,
    note: 'Windsurf shares one .windsurfrules file across all your project rules. Merge the printed content with your existing file rather than overwriting it.',
  },
  aider: {
    sources: [
      { kind: 'read', source: 'aider/SKILL.md' },
      { kind: 'author', source: 'aider/runlog-author.md' },
      { kind: 'harvest', source: 'aider/runlog-harvest.md' },
    ],
    target: 'CONVENTIONS.md',
    shared: true,
    note: 'Aider shares CONVENTIONS.md or accepts files via --read. Merge the printed content with your existing CONVENTIONS.md, or save it as a separate file and pass via --read.',
  },
  copilot: {
    sources: [
      { kind: 'read', source: 'copilot/SKILL.md' },
      { kind: 'author', source: 'copilot/runlog-author.md' },
      { kind: 'harvest', source: 'copilot/runlog-harvest.md' },
    ],
    target: '.github/copilot-instructions.md',
    shared: true,
    note: 'Copilot uses a single .github/copilot-instructions.md. Append the printed content to your existing file.',
  },
  jetbrains: {
    sources: [
      { kind: 'read', source: 'jetbrains/SKILL.md' },
      { kind: 'author', source: 'jetbrains/runlog-author.md' },
      { kind: 'harvest', source: 'jetbrains/runlog-harvest.md' },
    ],
    target: null,
    shared: true,
    note: 'JetBrains AI Assistant configuration lives in IDE Settings → AI Assistant. Paste the printed content into your AI Assistant guidelines.',
  },
  zed: {
    sources: [
      { kind: 'read', source: 'zed/SKILL.md' },
      { kind: 'author', source: 'zed/runlog-author.md' },
      { kind: 'harvest', source: 'zed/runlog-harvest.md' },
    ],
    target: '.rules',
    shared: true,
    note: 'Zed uses a single .rules file. Append the printed content to your existing file.',
  },
};

const MCP_SNIPPET = `{
  "mcpServers": {
    "runlog": {
      "type": "http",
      "url": "https://api.runlog.org/mcp",
      "headers": {
        "Authorization": "Bearer \${RUNLOG_API_KEY}"
      }
    }
  }
}`;

function printHelp() {
  process.stdout.write(`Usage: npx @runlog/install <vendor> [--write] [--global] [--force]

Vendors:
  claude-code, cursor, cline, continue, windsurf, aider, copilot, jetbrains, zed

Default: prints all three Runlog skill bodies (read, runlog-author, runlog-harvest)
and the MCP server config snippet for manual install. Safe for vendors that share
a single rules file with your existing content (windsurf, copilot, zed, aider, jetbrains).

Flags:
  --write    Write all three skill files (read, runlog-author, runlog-harvest) to
             the vendor's rules paths (only for vendors with a dedicated rules
             directory: cursor, cline, continue, claude-code).
  --global   Use the user-global paths (cursor, claude-code) instead of the
             project-local paths.
  --force    Overwrite existing target files when used with --write.

For Claude Code, prefer the plugin marketplace:
  /plugin marketplace add runlog-org/runlog-skills
  /plugin install runlog

After installing, register the Runlog MCP server (the installer prints the
config snippet) and set RUNLOG_API_KEY (get one at https://runlog.org/register).
`);
}

async function fetchSource(sourcePath) {
  const url = `${RAW_BASE}/${sourcePath}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Fetch failed: ${url} → HTTP ${res.status}`);
  }
  return res.text();
}

function expandHome(p) {
  if (p && p.startsWith('~/')) return path.join(os.homedir(), p.slice(2));
  return p;
}

function buildSharedBody(bodies) {
  // bodies: [{kind, content}, ...] in read/author/harvest order
  const parts = [];
  for (const { kind, content } of bodies) {
    const label = SKILL_LABELS[kind] || kind;
    parts.push(`---\n## ${label}\n---\n${content}`);
  }
  return parts.join('\n\n');
}

function printSharedBlock(vendor, target, combinedBody, note) {
  process.stdout.write(`\n# Runlog skills — ${vendor}\n\n`);
  if (target) process.stdout.write(`Target path: ${target}\n\n`);
  if (note) process.stdout.write(`${note}\n\n`);
  process.stdout.write(`--- BEGIN runlog skills (3 sections: read, author, harvest) ---\n${combinedBody}\n--- END runlog skills ---\n\n`);
  process.stdout.write(`--- MCP server config (add to your vendor's MCP config) ---\n${MCP_SNIPPET}\n\n`);
  process.stdout.write(`Set RUNLOG_API_KEY (get one at https://runlog.org/register).\n`);
}

function printPerSourceBlock(vendor, sourceEntry, target, content) {
  const label = SKILL_LABELS[sourceEntry.kind] || sourceEntry.kind;
  process.stdout.write(`\n# Runlog ${label} — ${vendor}\n\n`);
  if (target) process.stdout.write(`Target path: ${target}\n\n`);
  process.stdout.write(`--- BEGIN ${sourceEntry.source} ---\n${content}\n--- END ${sourceEntry.source} ---\n\n`);
}

async function main() {
  const args = process.argv.slice(2);

  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    printHelp();
    process.exit(args.length === 0 ? 1 : 0);
  }

  const vendor = args[0];
  const useGlobal = args.includes('--global');
  const useForce = args.includes('--force');
  const useWrite = args.includes('--write');

  const config = VENDORS[vendor];
  if (!config) {
    process.stderr.write(`Unknown vendor: ${vendor}\n`);
    process.stderr.write(`Supported: ${Object.keys(VENDORS).join(', ')}\n`);
    process.exit(1);
  }

  // Fetch all three skill bodies up front.
  let bodies;
  try {
    bodies = await Promise.all(
      config.sources.map(async (s) => ({
        kind: s.kind,
        entry: s,
        content: await fetchSource(s.source),
      })),
    );
  } catch (err) {
    process.stderr.write(`${err.message}\n`);
    process.exit(1);
  }

  // Shared-file vendors: concatenate + print regardless of --write.
  if (config.shared) {
    const combined = buildSharedBody(bodies.map(({ kind, content }) => ({ kind, content })));
    printSharedBlock(vendor, config.target, combined, config.note);
    return;
  }

  // Non-shared vendors. Resolve per-source targets up front.
  const resolved = bodies.map(({ kind, entry, content }) => ({
    kind,
    entry,
    content,
    target: expandHome(useGlobal ? entry.globalTarget : entry.target),
  }));

  // Print mode (default): emit all three section blocks + MCP snippet once.
  if (!useWrite) {
    for (const r of resolved) {
      printPerSourceBlock(vendor, r.entry, r.target, r.content);
    }
    if (config.note) process.stdout.write(`${config.note}\n\n`);
    process.stdout.write(`--- MCP server config (add to your vendor's MCP config) ---\n${MCP_SNIPPET}\n\n`);
    process.stdout.write(`Set RUNLOG_API_KEY (get one at https://runlog.org/register).\n`);
    process.stdout.write(`\nRe-run with --write to write the files to disk instead of printing.\n`);
    return;
  }

  // --write mode: refuse if any target exists without --force.
  if (!useForce) {
    const existing = resolved.filter((r) => r.target && fs.existsSync(r.target));
    if (existing.length > 0) {
      for (const r of existing) {
        process.stderr.write(`Target already exists: ${r.target}\n`);
      }
      process.stderr.write('Re-run with --force to overwrite, or drop --write to print the content instead.\n');
      process.exit(1);
    }
  }

  for (const r of resolved) {
    if (!r.target) continue;
    fs.mkdirSync(path.dirname(r.target), { recursive: true });
    fs.writeFileSync(r.target, r.content);
    process.stdout.write(`Wrote ${r.target}\n`);
  }
  process.stdout.write(`\nNow register the Runlog MCP server. Add this to your vendor's MCP config:\n\n${MCP_SNIPPET}\n\n`);
  process.stdout.write(`Then set RUNLOG_API_KEY (get one at https://runlog.org/register).\n`);
  if (config.note) process.stdout.write(`\n${config.note}\n`);
}

main().catch((err) => {
  process.stderr.write(`${err.stack || err.message || err}\n`);
  process.exit(1);
});
