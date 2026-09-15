// Gate G8: working tree is clean (everything committed) on the feature branch.
import { spawnSync } from 'node:child_process';

const branch = spawnSync('git', ['branch', '--show-current'], {
  cwd: process.cwd(),
  encoding: 'utf8',
}).stdout.trim();

if (branch !== 'feature/product-tour-doctor-web') {
  console.error(`expected branch feature/product-tour-doctor-web, got "${branch}"`);
  process.exit(1);
}

const status = spawnSync('git', ['status', '--short'], {
  cwd: process.cwd(),
  encoding: 'utf8',
}).stdout;

// GATES.md and scripts/gate-check-*.mjs are unlazy verification tooling for
// this session, not part of the shipped feature — deliberately left
// untracked rather than committed into the product repo.
const IGNORED = [/^\?\? GATES\.md$/, /^\?\? scripts\/gate-check-.*\.mjs$/, /^\?\? scripts\/$/];
const dirty = status
  .split('\n')
  .filter(line => line.trim().length > 0)
  .filter(line => !IGNORED.some(re => re.test(line.trim())));

if (dirty.length > 0) {
  console.error('Uncommitted changes present:\n' + dirty.join('\n'));
  process.exit(1);
}

console.log('TREE_CLEAN');
