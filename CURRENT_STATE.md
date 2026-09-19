# Current State

_Last updated: 2026-09-11. Overwritten each session — no history here. Full narrative in docs/BUILD_TRACKER_ARCHIVE.md._

## Done this session
- Re-verified working tree against HEAD (`5006cd0`, branch `feature/api-remediation-v0.2`) via `git diff --stat` + `git log -1` — no new commits, no code edits made this pass; state is unchanged from the prior session's writeup.
- Confirmed uncommitted diffs still present: `database.py` (post-commit safety probe), `clean_dish_names.py` (rollback-on-error fix), `.gitignore`/`CLAUDE.md`; plus carried-over Google Sign-In (`lib/useGoogleSignIn.ts`, `login.tsx`/`register.tsx`, `gdpr_consent` in `auth.ts`, real client ID in `eas.json`, `expo-auth-session` dep) and doctor MFA QR fix (`Settings.tsx` → local `qrcode.react` render, no more secret sent to `api.qrserver.com`).
- Confirmed `AUDIT_REPORT.md`, `.mcp.json`, `.ignore` still untracked; `scripts/drop_instructions.py` staged-renamed to `scripts/archive/`; `scripts/rename_dishes_gemini.py` staged-deleted.

## Blockers / pending
- `AUDIT_REPORT.md` C1 still open: `doctor.py:1409` `swap_weekly_combo` — `TypeError` on every call (`_fill_slot_dishes` missing `user_diet` param), feature dead in prod.
- `AUDIT_REPORT.md` itself still uncommitted; only the `scripts/` batch of findings has been triaged/fixed, `app/` Major findings (architecture) not yet started.
- Google sign-in + MFA QR fix (uncommitted) not yet committed or device-tested.
- CI fix `27a8577` (quoted `SECRET_KEY`) landed Aug 7; not reconfirmed green this session. `/meal-plan/week` selectinload cost still unaddressed.

## Next action
Fix C1 (`swap_weekly_combo`) in `doctor.py`, then commit `AUDIT_REPORT.md` plus the outstanding `database.py`/`clean_dish_names.py`/`.gitignore`/`CLAUDE.md` diffs and the Google sign-in/MFA fix; triage remaining `app/` Major findings next.
