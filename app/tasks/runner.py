"""
CLI Task Runner for Scheduled Operational Background Jobs.
Usage:
    python -m app.tasks.runner <task_name> [--param=value]
Exit Codes:
    0: Success
    1: Task Failure / Unhandled Exception
    2: Task Already Running (Lock Contention)
    3: Invalid Task Name
    4: Argument Parsing Error
"""
import sys
import os
import time
import argparse
import asyncio
import logging
import tempfile
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime, date

from app.db.session import AsyncSessionLocal, engine
from app.tasks.renewal_tasks import daily_renewal_expiry_check, daily_payment_report
from app.tasks.operational_tasks import (
    enforce_overdue_cheque_locks_task,
    dispatch_birthday_greetings_task,
    cleanup_stale_wallet_locks_task,
    cleanup_ephemeral_storage_task,
)

logger = logging.getLogger("reliable_tasks.runner")

EXIT_SUCCESS = 0
EXIT_TASK_FAILURE = 1
EXIT_LOCKED = 2
EXIT_INVALID_TASK = 3
EXIT_INVALID_ARGS = 4

TASK_REGISTRY: Dict[str, Callable] = {
    "daily_renewal_expiry_check": daily_renewal_expiry_check,
    "daily_payment_report": daily_payment_report,
    "enforce_overdue_cheque_locks": enforce_overdue_cheque_locks_task,
    "dispatch_birthday_greetings": dispatch_birthday_greetings_task,
    "cleanup_stale_wallet_locks": cleanup_stale_wallet_locks_task,
    "cleanup_ephemeral_storage": cleanup_ephemeral_storage_task,
}


def _is_pid_alive(pid: int) -> bool:
    """Check if process with given PID is actively running (cross-platform)."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            exit_code = ctypes.c_ulong()
            STILL_ACTIVE = 259
            ret = kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            kernel32.CloseHandle(handle)
            return bool(ret and exit_code.value == STILL_ACTIVE)
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except Exception:
            return False


class TaskLock:
    """
    Cross-platform file-based lock guard to prevent overlapping executions
    of scheduled daily batch tasks.
    """
    def __init__(self, task_name: str, lock_dir: Optional[str] = None):
        self.task_name = task_name
        self.lock_dir = lock_dir or tempfile.gettempdir()
        self.lock_path = os.path.join(self.lock_dir, f"reliable_task_{task_name}.lock")
        self.acquired = False
        self._fd: Optional[int] = None

    def acquire(self) -> bool:
        try:
            self._fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            pid_info = f"{os.getpid()}:{datetime.utcnow().isoformat()}\n".encode("utf-8")
            os.write(self._fd, pid_info)
            self.acquired = True
            return True
        except FileExistsError:
            try:
                owner_pid: Optional[int] = None
                try:
                    with open(self.lock_path, "r", encoding="utf-8") as f:
                        first_line = f.readline().strip()
                        if first_line:
                            pid_part = first_line.split(":", 1)[0]
                            owner_pid = int(pid_part)
                except (OSError, ValueError):
                    pass

                # If owner PID is alive, task is actively running — NEVER override
                if owner_pid is not None and _is_pid_alive(owner_pid):
                    logger.warning(
                        f"Task '{self.task_name}' is currently running under active PID {owner_pid}. Lock retained."
                    )
                    return False

                # If owner process is confirmed dead, or orphaned lock without PID is >4h old
                mtime = os.path.getmtime(self.lock_path)
                is_stale_mtime = (time.time() - mtime) > (4 * 3600)
                is_dead_process = owner_pid is not None and not _is_pid_alive(owner_pid)

                if is_dead_process or is_stale_mtime:
                    reason = "abandoned by terminated process" if is_dead_process else ">4h old"
                    logger.warning(f"Overriding stale lock file ({reason}) at {self.lock_path}")
                    try:
                        os.remove(self.lock_path)
                    except FileNotFoundError:
                        pass
                    return self.acquire()
            except OSError:
                pass
            return False
        except OSError as e:
            logger.error(f"Failed to create lock file {self.lock_path}: {e}")
            return False

    def release(self) -> None:
        if self.acquired:
            if self._fd is not None:
                try:
                    os.close(self._fd)
                except OSError:
                    pass
                self._fd = None
            try:
                if os.path.exists(self.lock_path):
                    os.remove(self.lock_path)
            except OSError as e:
                logger.warning(f"Failed to delete lock file {self.lock_path}: {e}")
            self.acquired = False

    def __enter__(self) -> bool:
        return self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


async def run_task(
    task_name: str,
    task_kwargs: Optional[Dict[str, Any]] = None,
    enforce_lock: bool = True,
    session_factory: Callable = AsyncSessionLocal,
    lock_dir: Optional[str] = None,
) -> Any:
    """
    Executes a registered background task with structured logging,
    overlap protection, and deterministic session lifecycle management.
    """
    if task_name not in TASK_REGISTRY:
        logger.error(f"Task '{task_name}' is not in registered allowlist. Allowed: {list(TASK_REGISTRY.keys())}")
        raise KeyError(f"Task '{task_name}' is not registered.")

    task_func = TASK_REGISTRY[task_name]
    kwargs = task_kwargs or {}

    lock = TaskLock(task_name, lock_dir=lock_dir)
    if enforce_lock:
        if not lock.acquire():
            logger.warning(f"Task '{task_name}' is already running. Skipping execution.")
            raise BlockingIOError(f"Task '{task_name}' is already running.")

    start_time = time.time()
    logger.info(f"Task '{task_name}' started with kwargs: {kwargs}")

    try:
        async with session_factory() as session:
            try:
                result = await task_func(session, **kwargs)
                await session.commit()
                duration = time.time() - start_time
                logger.info(f"Task '{task_name}' completed successfully in {duration:.2f}s.")
                return result
            except Exception as e:
                await session.rollback()
                logger.exception(f"Task '{task_name}' failed with error: {e}")
                raise
    finally:
        if enforce_lock:
            lock.release()


async def close_engine() -> None:
    await engine.dispose()


def main(argv: Optional[List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Reliable Insurance Backend CLI Task Runner",
        prog="python -m app.tasks.runner",
    )
    parser.add_argument("task_name", help="Name of registered background task to execute")
    parser.add_argument("--days_ahead", type=int, help="Days ahead for renewal scanning")
    parser.add_argument("--threshold_days", type=int, help="Threshold days for overdue cheque locks")
    parser.add_argument("--report_date", type=str, help="Target date for payment report (YYYY-MM-DD)")
    parser.add_argument("--target_date", type=str, help="Target date for birthday greetings (YYYY-MM-DD)")
    parser.add_argument("--no-lock", action="store_true", help="Bypass overlapping execution lock")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return EXIT_INVALID_ARGS if e.code != 0 else EXIT_SUCCESS

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    if args.task_name not in TASK_REGISTRY:
        logger.error(f"Task '{args.task_name}' is not registered. Supported tasks: {list(TASK_REGISTRY.keys())}")
        return EXIT_INVALID_TASK

    raw_kwargs: Dict[str, Any] = {}
    if args.days_ahead is not None:
        raw_kwargs["days_ahead"] = args.days_ahead
    if args.threshold_days is not None:
        raw_kwargs["threshold_days"] = args.threshold_days
    if args.report_date is not None:
        try:
            raw_kwargs["report_date"] = datetime.strptime(args.report_date, "%Y-%m-%d").date()
        except ValueError:
            logger.error("Invalid --report_date format. Must be YYYY-MM-DD.")
            return EXIT_INVALID_ARGS
    if args.target_date is not None:
        try:
            raw_kwargs["target_date"] = datetime.strptime(args.target_date, "%Y-%m-%d").date()
        except ValueError:
            logger.error("Invalid --target_date format. Must be YYYY-MM-DD.")
            return EXIT_INVALID_ARGS

    async def _run() -> int:
        try:
            await run_task(
                args.task_name,
                task_kwargs=raw_kwargs,
                enforce_lock=not args.no_lock,
            )
            return EXIT_SUCCESS
        except BlockingIOError:
            return EXIT_LOCKED
        except KeyError:
            return EXIT_INVALID_TASK
        except Exception:
            return EXIT_TASK_FAILURE
        finally:
            await close_engine()

    return asyncio.run(_run())


if __name__ == "__main__":
    sys.exit(main())
