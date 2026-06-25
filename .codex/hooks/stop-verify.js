#!/usr/bin/env node
const fs = require('node:fs');
const path = require('node:path');

function readJson(filePath, fallback) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return fallback;
  }
}

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
const config = readJson(path.join(cwd, '.harness', 'config.json'), {});
const latest = readJson(path.join(cwd, '.harness', 'verification', 'latest.json'), null);
const passed = latest && latest.status === 'passed';

if (!passed) {
  const message = 'No passing harness verification evidence found. Run `harness verify` or record why verification was skipped.';
  const output = config.harness && config.harness.enforceStopVerification
    ? { continue: false, stopReason: message, systemMessage: message }
    : { continue: true, systemMessage: message };
  process.stdout.write(JSON.stringify(output));
}

