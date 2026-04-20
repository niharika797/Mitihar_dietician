"""
One-off admin utility: wipe all patient data for a clean start.
Keeps doctors, admins, food items, and meal templates intact.
Resets all subscription codes back to available.

Usage:
  python -m scripts.clean_patients
"""
import asyncio
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def clean() -> None:
    async with AsyncSessionLocal() as session:
        print("Starting clean...")

        # Delete child tables first (FK order)
        await session.execute(text("DELETE FROM meal_logs"))
        print("  ✓ meal_logs cleared")

        await session.execute(text("DELETE FROM progress_logs"))
        print("  ✓ progress_logs cleared")

        await session.execute(text("DELETE FROM recommendations"))
        print("  ✓ recommendations cleared")

        await session.execute(text("DELETE FROM patient_visits"))
        print("  ✓ patient_visits cleared")

        await session.execute(text("DELETE FROM patient_requests"))
        print("  ✓ patient_requests cleared")

        # Email verification tokens
        try:
            await session.execute(text("DELETE FROM email_verification_tokens"))
            print("  ✓ email_verification_tokens cleared")
        except Exception:
            print("  - email_verification_tokens not found, skipping")

        # Clinical notes linked to patients
        try:
            await session.execute(text("DELETE FROM clinical_notes"))
            print("  ✓ clinical_notes cleared")
        except Exception:
            print("  - clinical_notes not found, skipping")

        # Audit logs linked to patients
        try:
            await session.execute(text("DELETE FROM audit_logs"))
            print("  ✓ audit_logs cleared")
        except Exception:
            print("  - audit_logs not found, skipping")

        # Reset subscription codes BEFORE deleting patients
        # (subscription_codes.used_by_patient_id has a FK to patients)
        await session.execute(text("""
            UPDATE subscription_codes
            SET is_used = FALSE,
                used_at = NULL,
                used_by_patient_id = NULL
        """))
        print("  ✓ subscription_codes reset to available")

        # Now safe to delete patients
        await session.execute(text("DELETE FROM patients"))
        print("  ✓ patients cleared")

        # Reset patient ID sequence so IDs start from 1
        await session.execute(text("ALTER SEQUENCE patients_id_seq RESTART WITH 1"))
        print("  ✓ patients ID sequence reset to 1")

        await session.commit()
        print("\nDone! Clean start ready.")


if __name__ == "__main__":
    asyncio.run(clean())
