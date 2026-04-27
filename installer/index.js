#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

const RAW_BASE = 'https://raw.githubusercontent.com/runlog-org/runlog-skills/main';

const VENDORS = {
  'claude-code': {
    source: 'claude-code/SKILL.md',
    target: '.claude/skills/runlog/SKILL.md',
    globalTarget: '~/.claude/skills/runlog/SKILL.md',
    note: 'For Claude Code, prefer the plugin marketplace:\n  /plugin marketplace add runlog-org/runlog-skills\n  /plugin install runlog\nThe plugin also auto-registers the Runlog MCP server.',
  },
  cursor: {
    source: 'cursor/SKILL.md',
    target: '.cursor/rules/runlog.mdc',
    globalTarget: '~/.cursor/rules/runlog.mdc',
  },
  cline: {
    source: 'cline/SKILL.md',
    target: '.clinerules/runlog.md',
  },
  continue: {
    source: 'continue/SKILL.md',
    target: '.continue/rules/runlog.md',
  },
  windsurf: {
    source: 'windsurf/SKILL.md',
    target: '.windsurfrules',
    shared: true,
    note: 'Windsurf shares one .windsurfrules file across all your project rules. Merge the printed content with your existing file rather than overwriting it.',
  },
  aider: {
    source: 'aider/SKILL.md',
    target: 'CONVENTIONS.md',
    shared: true,
    note: 'Aider shares CONVENTIONS.md or accepts files via --read. Merge the printed content with your existing CONVENTIONS.md, or save it as a separate file and pass via --read.',
  },
  copilot: {
    source: 'copilot/SKILL.md',
    target: '.github/copilot-instructions.md',
    shared: true,
    note: 'Copilot uses a single .github/copilot-instructions.md. Append the printed content to your existing file.',
  },
  jetbrains: {
    source: 'jetbrains/SKILL.md',
    target: null,
    shared: true,
    note: 'JetBrains AI Assistant configuration lives in IDE Settings → AI Assistant. Paste the printed content into your AI Assistant guidelines.',
  },
  zed: {
    source: 'zed/SKILL.md',
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

Default: prints the SKILL.md content and the MCP server config snippet for
manual install. Safe for vendors that share a single rules file with your
existing content (windsurf, copilot, zed, aider, jetbrains).

Flags:
  --write    Write the SKILL.md to the vendor's rules path (only for vendors
             with a dedicated rules directory: cursor, cline, continue,
             claude-code).
  --global   Use the user-global path (cursor, claude-code) instead of the
             project-local path.
  --force    Overwrite existing target file when used with --write.

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

function printSkillBlock(vendor, target, content, note) {
  process.stdout.write(`\n# Runlog skill — ${vendor}\n\n`);
  if (target) process.stdout.write(`Target path: ${target}\n\n`);
  if (note) process.stdout.write(`${note}\n\n`);
  process.stdout.write(`--- BEGIN SKILL.md ---\n${content}\n--- END SKILL.md ---\n\n`);
  process.stdout.write(`--- MCP server config (add to your vendor's MCP config) ---\n${MCP_SNIPPET}\n\n`);
  process.stdout.write(`Set RUNLOG_API_KEY (get one at https://runlog.org/register).\n`);
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

  let content;
  try {
    content = await fetchSource(config.source);
  } catch (err) {
    process.stderr.write(`${err.message}\n`);
    process.exit(1);
  }

  const target = expandHome(useGlobal ? config.globalTarget : config.target);

  if (config.shared || !target) {
    printSkillBlock(vendor, target, content, config.note);
    return;
  }

  if (!useWrite) {
    printSkillBlock(vendor, target, content, config.note);
    process.stdout.write(`Re-run with --write to write the file to ${target} instead of printing.\n`);
    return;
  }

  if (fs.existsSync(target) && !useForce) {
    process.stderr.write(`Target already exists: ${target}\n`);
    process.stderr.write('Re-run with --force to overwrite, or drop --write to print the content instead.\n');
    process.exit(1);
  }

  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, content);
  process.stdout.write(`Wrote ${target}\n\n`);
  process.stdout.write(`Now register the Runlog MCP server. Add this to your vendor's MCP config:\n\n${MCP_SNIPPET}\n\n`);
  process.stdout.write(`Then set RUNLOG_API_KEY (get one at https://runlog.org/register).\n`);
  if (config.note) process.stdout.write(`\n${config.note}\n`);
}

main().catch((err) => {
  process.stderr.write(`${err.stack || err.message || err}\n`);
  process.exit(1);
});
