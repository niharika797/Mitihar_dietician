// Gate G7: `git diff main --stat` touches only files inside the plan's
// declared File Structure — no admin/, no mitihar-patient-app/, no Admin/
// Patient model files.
import { spawnSync } from 'node:child_process';

const result = spawnSync('git', ['diff', 'main', '--name-only'], {
  cwd: process.cwd(),
  encoding: 'utf8',
});

if (result.status !== 0) {
  console.error(result.stderr);
  process.exit(1);
}

const files = result.stdout.split('\n').map(f => f.trim()).filter(Boolean);

const allowedExact = new Set([
  'app/models/db_models.py',
  'app/routers/doctor.py',
  'app/schemas/doctor.py',
  'mitihar-frontend/apps/src/lib/doctorApi.ts',
  'mitihar-frontend/apps/src/app/pages/doctor/DoctorShell.tsx',
  'mitihar-frontend/apps/src/app/pages/doctor/Overview.tsx',
  'mitihar-frontend/apps/src/app/pages/doctor/Patients.tsx',
  'mitihar-frontend/apps/src/app/pages/doctor/Requests.tsx',
  'mitihar-frontend/apps/src/app/pages/doctor/Recipes.tsx',
  'mitihar-frontend/apps/src/app/pages/doctor/Settings.tsx',
  'mitihar-frontend/apps/src/app/hooks/useProductTour.ts',
  'mitihar-frontend/apps/package.json',
  'mitihar-frontend/apps/pnpm-lock.yaml',
  'tests/full_backend_test.py',
]);

const allowedPrefixes = [
  'alembic/versions/c6d7e8f9a0b1_',
];

const forbiddenPrefixes = [
  'mitihar-patient-app/',
  'mitihar-frontend/apps/src/app/pages/admin/',
  'app/routers/admin.py',
];

const violations = [];
for (const f of files) {
  const isAllowed =
    allowedExact.has(f) || allowedPrefixes.some(p => f.startsWith(p));
  const isForbidden = forbiddenPrefixes.some(p => f.startsWith(p));
  if (isForbidden || !isAllowed) {
    violations.push(f);
  }
}

if (violations.length > 0) {
  console.error('Out-of-scope diffs found:\n' + violations.join('\n'));
  process.exit(1);
}

if (files.length === 0) {
  console.error('git diff main --name-only returned no files — nothing to verify against');
  process.exit(1);
}

console.log(`DIFF_SCOPE_CLEAN (${files.length} files, all in scope)`);
