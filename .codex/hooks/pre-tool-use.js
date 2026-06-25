#!/usr/bin/env node
const fs = require('node:fs');

function readInput() {
  try {
    const text = fs.readFileSync(0, 'utf8');
    return text ? JSON.parse(text) : {};
  } catch {
    return {};
  }
}

function detect(command) {
  const text = String(command || '');
  const blocked = [
    { pattern: /\brm\s+-(?:[a-zA-Z]*r[a-zA-Z]*f|[a-zA-Z]*f[a-zA-Z]*r)\b/i, message: 'Recursive force deletion is blocked.' },
    { pattern: /\bgit\s+reset\s+--hard\b/i, message: 'git reset --hard is blocked.' },
    { pattern: /\b(drop\s+database|drop\s+table|truncate\s+table)\b/i, message: 'Destructive database command is blocked.' },
    { pattern: /\b(--no-verify|skip-ci|ci skip)\b/i, message: 'Verification bypass is blocked.' }
  ];
  const approval = [
    { pattern: /\b(npm\s+(?:install|i)|pnpm\s+add|yarn\s+add|bun\s+add|pip\s+install|uv\s+add)\b/i, message: 'Dependency changes require explicit approval.' },
    { pattern: /\b(prisma\s+migrate|rails\s+db:migrate|alembic\s+upgrade)\b/i, message: 'Database migrations require explicit approval.' }
  ];
  for (const rule of blocked) {
    if (rule.pattern.test(text)) return { deny: true, message: rule.message };
  }
  for (const rule of approval) {
    if (rule.pattern.test(text)) return { deny: true, message: rule.message };
  }
  return { deny: false };
}

const input = readInput();
const command = input.tool_input && input.tool_input.command;
const decision = detect(command);

if (decision.deny) {
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason: decision.message
    }
  }));
}

