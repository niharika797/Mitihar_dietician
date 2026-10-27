"""
seed_test_accounts.py — creates or syncs the admin account named by TEST_ADMIN_EMAIL / TEST_ADMIN_PASSWORD
(the account tests/full_backend_test.py and tests/security_verification_test.py log in with). If that
account already exists with a different password, the password is RESET to TEST_ADMIN_PASSWORD.
Point TEST_ADMIN_EMAIL at a dedicated test admin, not at an admin you use for real.

LOCAL DEV ONLY: refuses to run unless DATABASE_URL points at localhost / 127.0.0.1.
Test-only credentials, overridable via TEST_ADMIN_EMAIL / TEST_ADMIN_PASSWORD.

Usage:  python -m scripts.seed_test_accounts
"""
import asyncio
import os
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

TEST_ADMIN_EMAIL = os.getenv("TEST_ADMIN_EMAIL", "autotest.admin@mityahar.test")
TEST_ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "AutoTest@2026-local")

host = urlparse(os.environ.get("DATABASE_URL", "")).hostname
if host not in ("localhost", "127.0.0.1"):
    raise SystemExit(f"Refusing to seed test accounts: DATABASE_URL host is {host!r}, not local.")

from sqlalchemy import select, update  # noqa: E402

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.security import get_password_hash, verify_password  # noqa: E402
from app.models.db_models import Admin, Doctor  # noqa: E402


async def seed() -> None:
    async with AsyncSessionLocal() as s:
        admin = (await s.execute(select(Admin).where(Admin.email == TEST_ADMIN_EMAIL))).scalars().first()
        if admin is None:
            s.add(Admin(email=TEST_ADMIN_EMAIL, hashed_password=get_password_hash(TEST_ADMIN_PASSWORD), name="Autotest Admin"))
            print(f"Created test admin {TEST_ADMIN_EMAIL}")
        elif not verify_password(TEST_ADMIN_PASSWORD, admin.hashed_password):
            await s.execute(update(Admin).where(Admin.id == admin.id).values(
                hashed_password=get_password_hash(TEST_ADMIN_PASSWORD),
                failed_login_attempts=0, locked_until=None, is_active=True))
            print(f"Reset test admin password {TEST_ADMIN_EMAIL}")
        else:
            print(f"Test admin already set up: {TEST_ADMIN_EMAIL}")
        # The security suite deliberately locks its doctors out (T1-6); clear that so the next run starts clean.
        await s.execute(update(Doctor).where(Doctor.email.like("security.test.%")).values(failed_login_attempts=0, locked_until=None))
        await s.commit()
        print("Cleared lockout on security.test.* doctors")


asyncio.run(seed())
