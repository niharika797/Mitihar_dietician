"""
One-off admin utility: reset a burned subscription code and optionally unblock
the patient that was stranded by the early-consumption bug.

Usage:
  # Reset the code only
  python -m scripts.reset_invite_code GSD82B7X3PC6

  # Reset the code AND reset the stranded patient's subscription state
  python -m scripts.reset_invite_code GSD82B7X3PC6 demo@gmail.com
"""
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal
from app.models.db_models import SubscriptionCode, Patient


async def reset(code: str, patient_email: str | None = None) -> None:
    async with AsyncSessionLocal() as session:
        # ── 1. Reset the code ─────────────────────────────────────────────
        result = await session.execute(
            update(SubscriptionCode)
            .where(SubscriptionCode.code == code)
            .values(is_used=False, used_at=None, used_by_patient_id=None)
            .returning(SubscriptionCode.id)
        )
        row = result.fetchone()
        if row is None:
            print(f"Code '{code}' not found in DB — nothing changed.")
            return
        print(f"Code '{code}' reset → is_used=False, used_at=NULL, used_by_patient_id=NULL")

        # ── 2. Optionally reset the stranded patient ───────────────────────
        if patient_email:
            pat_result = await session.execute(
                select(Patient).where(Patient.email == patient_email)
            )
            patient = pat_result.scalars().first()
            if patient is None:
                print(f"Patient '{patient_email}' not found — skipping patient reset.")
            else:
                await session.execute(
                    update(Patient)
                    .where(Patient.id == patient.id)
                    .values(subscription_status="inactive")
                )
                print(
                    f"Patient '{patient_email}' (id={patient.id}) reset → "
                    f"subscription_status=inactive. "
                    f"They can now retry /patients/activate with a fresh code."
                )

        await session.commit()
        print("Done.")


if __name__ == "__main__":
    code_arg = sys.argv[1] if len(sys.argv) > 1 else "GSD82B7X3PC6"
    email_arg = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(reset(code_arg, email_arg))
