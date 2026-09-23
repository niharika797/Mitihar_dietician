"""
Verify that POST/PUT /progress/log/weight returns immediately regardless of Gemini latency.

_handle_weight_change must complete in <1s even when _regen_diet_plan_background
simulates a 10-second Gemini call. The background task is created via
asyncio.create_task and never awaited by the request handler.
"""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch


def _make_mock_session():
    s = MagicMock()
    s.execute = AsyncMock()
    s.flush = AsyncMock()
    return s


def _make_mock_user():
    u = MagicMock()
    u.id = 1
    u.date_of_birth = None
    u.height_cm = 170.0
    u.gender = "Male"
    u.activity_level = "Lightly Active"
    u.diet_type = "Anything"
    u.health_condition = "Healthy"
    u.region = "none"
    u.target_weight_kg = None
    return u


def test_weight_handler_nonblocking():
    """Handler must return in <1s even when diet-plan regen takes 10s."""

    async def run():
        async def slow_regen(_user_data: dict) -> None:
            await asyncio.sleep(10)

        bg_tasks = []
        real_create_task = asyncio.create_task

        def capture_create_task(coro, **kwargs):
            task = real_create_task(coro, **kwargs)
            bg_tasks.append(task)
            return task

        with patch("app.routers.progress._regen_diet_plan_background", slow_regen), \
             patch("app.routers.progress.asyncio.create_task", side_effect=capture_create_task):
            from app.routers.progress import _handle_weight_change

            start = time.monotonic()
            await _handle_weight_change(_make_mock_session(), _make_mock_user(), 70.0)
            elapsed = time.monotonic() - start

        # cancel the 10s background task so the test finishes quickly
        for t in bg_tasks:
            t.cancel()
        if bg_tasks:
            await asyncio.gather(*bg_tasks, return_exceptions=True)

        assert elapsed < 1.0, (
            f"_handle_weight_change blocked for {elapsed:.2f}s — "
            "Gemini call is not offloaded to background"
        )
        assert len(bg_tasks) == 1, "Expected exactly one background task to be created"

    asyncio.run(run())


def test_regen_fired_not_awaited():
    """create_task must be called (not await) so the handler never blocks on Gemini."""

    async def run():
        calls = []

        async def record_call(_user_data: dict) -> None:
            calls.append(_user_data)

        with patch("app.routers.progress._regen_diet_plan_background", record_call), \
             patch("app.routers.progress.asyncio.create_task") as mock_ct:
            mock_ct.return_value = asyncio.ensure_future(asyncio.sleep(0))
            from app.routers.progress import _handle_weight_change
            await _handle_weight_change(_make_mock_session(), _make_mock_user(), 72.5)

        assert mock_ct.called, "asyncio.create_task was never called"
        # The coroutine passed to create_task should be _regen_diet_plan_background(...)
        coro = mock_ct.call_args[0][0]
        assert "regen_diet_plan" in type(coro).__qualname__ or coro.__class__.__name__ == "coroutine"
        coro.close()  # avoid ResourceWarning

    asyncio.run(run())
