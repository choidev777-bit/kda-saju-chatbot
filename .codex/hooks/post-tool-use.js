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

const input = readInput();
const cwd = input.cwd || process.cwd();
const event = {
  timestamp: new Date().toISOString(),
  hookEventName: input.hook_event_name || 'PostToolUse',
  toolName: input.tool_name || null,
  command: input.tool_input && input.tool_input.command ? input.tool_input.command : null
};

const logPath = path.join(cwd, '.harness', 'events.jsonl');
fs.mkdirSync(path.dirname(logPath), { recursive: true });
fs.appendFileSync(logPath, `${JSON.stringify(event)}\n`);

