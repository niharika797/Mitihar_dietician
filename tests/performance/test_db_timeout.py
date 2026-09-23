"""
PostgreSQL statement_timeout verification test.

Confirms that the 30-second statement_timeout set in database.py kills runaway
queries instead of letting them hold a connection indefinitely.

Test method: execute SELECT pg_sleep(40) — intentionally 10s over the 30s limit.
Expected:    asyncpg raises QueryCanceledError (PostgreSQL error code 57014)
             within ~30 seconds.
Pass criteria: exception raised in < 35s, connection returned to pool (not leaked).

Run:
    python -m tests.performance.test_db_timeout
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def run() -> None:
    print("=== PostgreSQL statement_timeout Verification ===\n")
    print("Configured timeout: 30,000ms (30s) via connect_args server_settings")
    print("Test query:         SELECT pg_sleep(40)  — intentionally 10s over limit")
    print("Expected:           QueryCanceledError raised at ~30s\n")

    # Step 1: Confirm the setting is applied on this connection
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SHOW statement_timeout"))
        val = result.scalar()
        print(f"statement_timeout on connection: {val!r}")
        if val == "30s" or val == "30000":
            print("  Setting confirmed: 30s OK\n")
        else:
            print(f"  WARNING: expected '30s' or '30000', got {val!r}")
            print("  Check connect_args in database.py\n")

    # Step 2: Run the intentionally slow query and confirm it's killed
    print("Running SELECT pg_sleep(40)...")
    t0 = time.perf_counter()
    killed = False
    kill_elapsed = None

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT pg_sleep(40)"))
        print("ERROR: query completed without timeout — statement_timeout is NOT working!")
    except Exception as exc:
        kill_elapsed = round(time.perf_counter() - t0, 2)
        exc_name = type(exc).__name__
        exc_str = str(exc).lower()
        is_timeout = (
            "querycanceled" in exc_name.lower()
            or "canceling" in exc_str
            or "statement timeout" in exc_str
            or "57014" in exc_str
        )
        if is_timeout:
            killed = True
            print(f"Query killed after {kill_elapsed}s")
            print(f"Exception: {exc_name}")
            print(f"  {str(exc)[:120]}")
        else:
            print(f"Query raised unexpected error after {kill_elapsed}s: {exc_name}: {exc}")

    # Step 3: Confirm pool is still usable (connection was returned, not leaked)
    print("\nConfirming connection pool not leaked (running a simple query)...")
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1 AS ping"))
            ping_val = result.scalar()
            pool_ok = ping_val == 1
            print(f"  SELECT 1 = {ping_val} {'OK' if pool_ok else 'FAIL'}")
    except Exception as e:
        pool_ok = False
        print(f"  Pool query failed: {e}")

    # Result
    passed = killed and kill_elapsed is not None and kill_elapsed < 35 and pool_ok
    print(f"\n--- Summary ---")
    print(f"  Query killed by timeout:       {'YES' if killed else 'NO'}")
    print(f"  Time to kill:                  {kill_elapsed}s  (should be ~30s, < 35s)")
    print(f"  Connection pool still healthy: {'YES' if pool_ok else 'NO'}")
    print(f"\nOVERALL: {'PASS' if passed else 'FAIL'}")

    if not passed:
        if not killed:
            print("  Timeout did not fire — verify connect_args in app/core/database.py:")
            print("    connect_args={'server_settings': {'statement_timeout': '30000'}}")
        if kill_elapsed and kill_elapsed >= 35:
            print(f"  Timeout took {kill_elapsed}s — expected < 35s")


if __name__ == "__main__":
    asyncio.run(run())
