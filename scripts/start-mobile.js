#!/usr/bin/env node
const { spawn } = require('child_process');
const path = require('path');

console.log('');
console.log('SmartStudy: starting Expo from mobile/ (SDK 54)');
console.log('Do NOT run "npx expo start" from the repo root.');
console.log('Use "npm start" from D:\\SmartStudy-app instead.');
console.log('');

const mobileDir = path.join(__dirname, '..', 'mobile');
const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';

const child = spawn(npmCmd, ['start'], {
  cwd: mobileDir,
  stdio: 'inherit',
  shell: process.platform === 'win32',
});

child.on('exit', (code) => process.exit(code ?? 0));
