// Gate G1: PATCH /doctor/tour-complete is idempotent (two calls, both 200,
// second timestamp >= first).
const BASE = process.env.TOUR_GATE_BASE || 'http://localhost:8001/api/v1';
const EMAIL = process.env.TEST_DOCTOR_EMAIL || 'dr.ashok.mehta@mitihar.test';
const PASSWORD = process.env.TEST_DOCTOR_PASSWORD || 'DoctorTest@2026';

async function login() {
  const res = await fetch(`${BASE}/auth/doctor/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username: EMAIL, password: PASSWORD }),
  });
  if (!res.ok) {
    throw new Error(`login failed: ${res.status} ${await res.text()}`);
  }
  const data = await res.json();
  return data.access_token;
}

async function patchTourComplete(token) {
  const res = await fetch(`${BASE}/doctor/tour-complete`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${token}` },
  });
  const body = await res.json();
  return { status: res.status, body };
}

async function main() {
  const token = await login();

  const first = await patchTourComplete(token);
  if (first.status !== 200) {
    throw new Error(`first PATCH expected 200, got ${first.status}: ${JSON.stringify(first.body)}`);
  }

  const second = await patchTourComplete(token);
  if (second.status !== 200) {
    throw new Error(`second PATCH expected 200, got ${second.status}: ${JSON.stringify(second.body)}`);
  }

  const t1 = new Date(first.body.completed_at).getTime();
  const t2 = new Date(second.body.completed_at).getTime();
  if (!(t2 >= t1)) {
    throw new Error(`second timestamp (${second.body.completed_at}) not >= first (${first.body.completed_at})`);
  }

  console.log('TOUR_COMPLETE_IDEMPOTENT_OK');
}

main().catch(err => {
  console.error(err.message || err);
  process.exit(1);
});
