// Gate G4: `pnpm tsc --noEmit` passes with zero errors in mitihar-frontend/apps.
import { spawnSync } from 'node:child_process';

const result = spawnSync('pnpm', ['tsc', '--noEmit'], {
  cwd: process.cwd(),
  encoding: 'utf8',
  shell: true,
});

const output = `${result.stdout || ''}${result.stderr || ''}`;

if (result.status !== 0) {
  console.error(output);
  console.error(`tsc exited with status ${result.status}`);
  process.exit(1);
}

console.log('TSC_CLEAN');
