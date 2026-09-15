# Gates: Product Tour Phase 2 (Doctor Web) — Tasks 7 finish, 8, 9

OWNS: mitihar-frontend/apps/src/app/hooks/useProductTour.ts, mitihar-frontend/apps/src/app/pages/doctor/**, app/routers/doctor.py, app/schemas/doctor.py, app/models/db_models.py, alembic/versions/c6d7e8f9a0b1_*.py, mitihar-frontend/apps/src/lib/doctorApi.ts, tests/full_backend_test.py, scripts/gate-check-*.mjs, GATES.md

Scope: Finish Task 7's deferred manual smoke test (cross-route attach + skip + reload), extend the tour to all 5 steps (Task 8), and complete the full acceptance pass (Task 9) per the approved plan at C:\Users\Lenovo\.claude\plans\must-use-skill-for-pure-babbage.md.

- [x] G1: Doctor dashboard PATCH /doctor/tour-complete is idempotent and returns 200 on repeated calls
  CHECK: node scripts/gate-check-tour-complete.mjs
  EXPECT: TOUR_COMPLETE_IDEMPOTENT_OK
  EVIDENCE: automatic-evidence=v1; definition-sha256=63c778f90b10df75f022615813f9c90de3ae8049cbb86488367dee1578603644; exit=0; EXPECT=matched; output-sha256=c46ea302dd9e3a23343a6ef155552bf05471cb368b104f4167825df20782ace3; output-bytes=28; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\Lenovo\Desktop\Code\2026\Nutria\mitihar-product-tour-doctor; path=94c3e15e86a2/46 entries

- [x] G2: 2-step smoke test (Task 7) — clicking Next on Overview navigates to /doctor/patients and the "Your Patients" tooltip correctly attaches to [data-tour="tour-patients"] (not blank, not misplaced, not stuck on old route)
  EVIDENCE: 2026-09-14 live browser test (Claude Browser pane). Found and fixed a real bug first: default react-joyride 3.2.0 scroll-into-view logic deadlocks at the `scroll:start` event inside DoctorShell's `overflow-y-auto` main container (confirmed via onEvent debug logging — event stream stopped dead at scroll:start, target never measured, tooltip never rendered). Fixed with the documented `options.skipScroll: true` flag (not a library swap — a supported react-joyride 3.x option; our dashboard targets never need scrolling). After the fix: onEvent stream showed tour:start -> step:before -> tooltip -> step:after(next) -> tour:start(index 1) -> tooltip, in order. location.pathname became /doctor/patients, tooltip innerText read "Your Patients / Every patient assigned to you shows up here.", and [data-tour="tour-patients"] resolved to the real <h1>Patients</h1>.

- [x] G3: Skip button (tested from the Overview step, since the last step of the 2-step smoke test hides Skip by Joyride convention) closes the tour, fires PATCH /doctor/tour-complete (200), and a page reload afterward does not reopen the tour
  EVIDENCE: 2026-09-14 live browser test. Clicked Skip on step 0 (Overview); read_network_requests showed `PATCH http://localhost:8001/api/v1/doctor/tour-complete -> 200 OK`; tooltip closed. Hard-reloaded to localhost:5173 (bounces to login per the plan's known no-refresh-recovery gap on /doctor/*), re-logged in as the same test doctor, landed back on /doctor/overview with no tooltip present — tour did not reopen.

- [x] G4: TOUR_STEPS extended to all 5 steps (Overview, Patients, Requests, Recipes, Settings) in useProductTour.ts, SMOKE TEST comment removed, and `pnpm tsc --noEmit` passes with zero new errors
  CHECK: node ../../scripts/gate-check-tsc.mjs
  EXPECT: TSC_CLEAN
  CWD: mitihar-frontend/apps
  EVIDENCE: automatic-evidence=v1; definition-sha256=690304c0647ebbbb27290effff522be889d4b3bf2c41553ac663de2cd3715c17; exit=0; EXPECT=matched; output-sha256=154d4d31d0e548c1141415fb10f4fc0d2e631702e3b12a31878bee095af0de7c; output-bytes=275; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\Lenovo\Desktop\Code\2026\Nutria\mitihar-product-tour-doctor\mitihar-frontend\apps; path=94c3e15e86a2/46 entries

- [x] G5: Full 5-step manual sequence verified — every step attaches after its route change in order, and Skip works when tested from at least 3 different steps (e.g. step 1, 3, 5), each firing exactly one tour-complete PATCH
  EVIDENCE: 2026-09-14 live browser test, clicking Next through all 5 steps in order. Confirmed each step's tooltip title + route via location.pathname + tooltip innerText: (1) /doctor/overview "Welcome to Mitihar", (2) /doctor/patients "Your Patients", (3) /doctor/requests "Patient Requests", (4) /doctor/recipes "Recipe Library", (5) /doctor/settings "Settings" ("Back"/"Last" buttons — no Skip on the final step, which is react-joyride's standard last-step convention, also observed on the earlier 2-step smoke test's last step, not a defect). Natural completion via "Last" on step 5 fired exactly one new PATCH /doctor/tour-complete (200 in read_network_requests). Skip tested separately from step 1 (Overview, see Task 7 G3 evidence above) and step 3 (Requests) in fresh reset+relogin runs — both fired exactly one new PATCH /doctor/tour-complete (200), verified via read_network_requests showing one new entry each run. Skip from step 5 is not applicable since Joyride hides Skip on the tour's final step by design.

- [x] G6: Regression check — dashboard loads normally with tour already completed (flag non-null): no tour popup, no console errors, Sidebar/TopBar/CommandPalette unaffected
  EVIDENCE: 2026-09-14 — after the natural 5-step completion, hard-reloaded and re-logged in. Landed on /doctor/overview with tooltip null (no popup), sidebar (`nav`) and topbar (`header`) both present and rendering. read_console_messages(onlyErrors) showed only two pre-existing unrelated 404 errors from an earlier manual navigation to a nonexistent /doctor/login URL made at the start of this session — no new errors from this run.

- [x] G7: Zero diffs outside declared scope — `git diff main --stat` touches only the files listed in the plan's File Structure section (nothing under mitihar-patient-app/, no Admin/Patient model changes, nothing under app/routers/admin.py or mitihar-frontend/apps/src/app/pages/admin/)
  CHECK: node scripts/gate-check-diff-scope.mjs
  EXPECT: DIFF_SCOPE_CLEAN
  EVIDENCE: automatic-evidence=v1; definition-sha256=06a96dddd91d6052f20c9f302b59ec28180e0d4c0620caa2699d998bd0ab5840; exit=0; EXPECT=matched; output-sha256=1225591f30c57d2a40b51890e2853b130c5d71d0651ca25672bf72a45cfd26b2; output-bytes=42; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\Lenovo\Desktop\Code\2026\Nutria\mitihar-product-tour-doctor; path=94c3e15e86a2/46 entries

- [x] G8: All work committed on feature/product-tour-doctor-web with a clean working tree (no uncommitted changes) after Task 8/9 work lands
  CHECK: node scripts/gate-check-clean-tree.mjs
  EXPECT: TREE_CLEAN
  EVIDENCE: automatic-evidence=v1; definition-sha256=03122b33c21c20a89d832985da064b3b4aab387b6450065c9b7d844bd30846a9; exit=0; EXPECT=matched; output-sha256=aae759e7feba7044a7768be621e4903bc475dc06185d754ee91c532cd54ad749; output-bytes=11; shell=C:\WINDOWS\system32\cmd.exe; cwd=C:\Users\Lenovo\Desktop\Code\2026\Nutria\mitihar-product-tour-doctor; path=94c3e15e86a2/46 entries
