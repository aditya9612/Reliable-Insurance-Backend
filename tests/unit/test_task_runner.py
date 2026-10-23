"""
Unit tests for app/tasks/runner.py — CLI Task Runner.
Tests task dispatch, allowlist validation, session lifecycle,
rollback behavior, overlap locking, and CLI exit codes.
"""
import pytest
import os
import time
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

from app.tasks.runner import (
    TASK_REGISTRY,
    TaskLock,
    run_task,
    main,
    EXIT_SUCCESS,
    EXIT_TASK_FAILURE,
    EXIT_LOCKED,
    EXIT_INVALID_TASK,
    EXIT_INVALID_ARGS,
)


# ---------------------------------------------------------------------------
# 1. Allowlist Validation Tests
# ---------------------------------------------------------------------------

def test_task_registry_allowlist():
    expected_tasks = {
        "daily_renewal_expiry_check",
        "daily_payment_report",
        "enforce_overdue_cheque_locks",
        "dispatch_birthday_greetings",
        "cleanup_stale_wallet_locks",
        "cleanup_ephemeral_storage",
    }
    assert set(TASK_REGISTRY.keys()) == expected_tasks
    assert "arbitrary_eval" not in TASK_REGISTRY
    assert "os_system" not in TASK_REGISTRY


@pytest.mark.asyncio
async def test_run_task_rejects_unregistered_task():
    with pytest.raises(KeyError, match="Task 'unregistered_task' is not registered"):
        await run_task("unregistered_task", enforce_lock=False)


# ---------------------------------------------------------------------------
# 2. Session Lifecycle & Rollback Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_task_success_session_lifecycle():
    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session
    mock_session_factory.return_value.__aexit__.return_value = None

    result = await run_task(
        "cleanup_stale_wallet_locks",
        enforce_lock=False,
        session_factory=mock_session_factory,
    )
    assert result is not None
    assert result["task_name"] == "stale_wallet_lock_cleanup"

    # Verify commit was invoked and rollback was not
    mock_session.commit.assert_awaited_once()
    mock_session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_task_exception_rolls_back_session():
    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session
    mock_session_factory.return_value.__aexit__.return_value = None

    # Patch the task callable to simulate an unhandled exception
    with patch.dict(TASK_REGISTRY, {"failing_task": AsyncMock(side_effect=RuntimeError("DB crashed"))}):
        with pytest.raises(RuntimeError, match="DB crashed"):
            await run_task(
                "failing_task",
                enforce_lock=False,
                session_factory=mock_session_factory,
            )

    # Verify rollback was invoked on error, commit was not
    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_awaited()


# ---------------------------------------------------------------------------
# 3. Overlap Protection & TaskLock Tests
# ---------------------------------------------------------------------------

def test_task_lock_acquire_and_release():
    with tempfile.TemporaryDirectory() as tmp_dir:
        lock1 = TaskLock("test_task", lock_dir=tmp_dir)
        lock2 = TaskLock("test_task", lock_dir=tmp_dir)

        # First lock succeeds
        assert lock1.acquire() is True
        assert os.path.exists(lock1.lock_path)

        # Second lock fails (already held)
        assert lock2.acquire() is False

        # Release first lock
        lock1.release()
        assert not os.path.exists(lock1.lock_path)

        # Second lock can now be acquired
        assert lock2.acquire() is True
        lock2.release()


@pytest.mark.asyncio
async def test_run_task_blocks_on_lock_contention():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Pre-acquire lock
        active_lock = TaskLock("cleanup_ephemeral_storage", lock_dir=tmp_dir)
        assert active_lock.acquire() is True

        try:
            with pytest.raises(BlockingIOError, match="is already running"):
                await run_task(
                    "cleanup_ephemeral_storage",
                    enforce_lock=True,
                    lock_dir=tmp_dir,
                )
        finally:
            active_lock.release()


def test_task_lock_live_owner_never_overridden():
    """
    Verifies that a lock owned by a live process is NEVER overridden,
    even if the lock file is older than the 4-hour stale threshold.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        lock = TaskLock("long_running_task", lock_dir=tmp_dir)
        # Manually create a lock file with current PID (alive) and backdate mtime by 5 hours
        live_pid = os.getpid()
        with open(lock.lock_path, "w", encoding="utf-8") as f:
            f.write(f"{live_pid}:2026-10-23T00:00:00\n")
        five_hours_ago = time.time() - (5 * 3600)
        os.utime(lock.lock_path, (five_hours_ago, five_hours_ago))

        # Attempt to acquire lock should fail because owner PID is alive
        new_lock = TaskLock("long_running_task", lock_dir=tmp_dir)
        assert new_lock.acquire() is False
        assert os.path.exists(lock.lock_path)


def test_task_lock_dead_owner_abandoned_lock_overridden():
    """
    Verifies that an abandoned lock from a terminated/dead process PID
    is safely overridden without having to wait 4 hours.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        lock = TaskLock("crashed_task", lock_dir=tmp_dir)
        # Write dead PID (999999) with recent timestamp (10 seconds old)
        with open(lock.lock_path, "w", encoding="utf-8") as f:
            f.write("999999:2026-10-23T08:00:00\n")

        new_lock = TaskLock("crashed_task", lock_dir=tmp_dir)
        # Should detect dead PID, clear abandoned lock, and acquire
        assert new_lock.acquire() is True
        assert new_lock.acquired is True
        new_lock.release()
        assert not os.path.exists(lock.lock_path)


# ---------------------------------------------------------------------------
# 4. CLI Argument Parsing & Exit Codes Tests
# ---------------------------------------------------------------------------

def test_cli_invalid_task_exit_code():
    code = main(["non_existent_task"])
    assert code == EXIT_INVALID_TASK


def test_cli_invalid_arguments_exit_code():
    code = main(["daily_payment_report", "--report_date=not-a-date"])
    assert code == EXIT_INVALID_ARGS


def test_cli_help_exit_code():
    code = main(["--help"])
    assert code == EXIT_SUCCESS


def test_cli_execution_success(monkeypatch):
    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session
    mock_session_factory.return_value.__aexit__.return_value = None

    # Patch session factory and engine disposal
    monkeypatch.setattr("app.tasks.runner.AsyncSessionLocal", mock_session_factory)
    monkeypatch.setattr("app.tasks.runner.close_engine", AsyncMock())

    code = main(["cleanup_ephemeral_storage", "--no-lock"])
    assert code == EXIT_SUCCESS
