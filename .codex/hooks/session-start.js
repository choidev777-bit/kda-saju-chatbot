#!/usr/bin/env node
const fs = require('node:fs');
const path = require('node:path');

function readInput() {
  try {
    const text = fs.readFileSync(0, 'utf8');
    return text ? JSON.parse(text) : {};
  } catch {
    return {};
  }
}

function existsFrom(cwd, file) {
  return fs.existsSync(path.join(cwd, file));
}

const input = readInput();
const cwd = input.cwd || process.cwd();
const required = ['AGENTS.md', 'HARNESS_PLAN.md', 'RATCHET_LOG.md', '.harness/config.json'];
const missing = required.filter((file) => !existsFrom(cwd, file));

const additionalContext = missing.length === 0
  ? 'Harness active: follow AGENTS.md, HARNESS_PLAN.md, and record repeated failures in RATCHET_LOG.md.'
  : `Harness files missing: ${missing.join(', ')}. Recommend running harness init before implementation.`;

process.stdout.write(JSON.stringify({
  hookSpecificOutput: {
    hookEventName: 'SessionStart',
    additionalContext
  }
}));

