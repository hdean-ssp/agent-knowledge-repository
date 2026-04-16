"""Unit tests for akr.locking – FileLockManager and FileLock."""

from __future__ import annotations

import fcntl
import os
import threading

import pytest

from akr.errors import LockTimeoutError
from akr.locking import FileLockManager


@pytest.fixture
def db_path(tmp_path):
    """Return a fake database path inside a temporary directory."""
    return str(tmp_path / "knowledge.db")


class TestFileLockManager:
    """Tests for FileLockManager.acquire_write_lock."""

    def test_lock_acquired_and_released(self, db_path):
        """Lock can be acquired and then released without error."""
        mgr = FileLockManager()
        lock = mgr.acquire_write_lock(db_path, timeout=2.0)
        # Lock is held — release it via context manager exit
        lock.__exit__(None, None, None)

    def test_lock_file_created(self, db_path):
        """The lock file is created at <db_path>.lock."""
        mgr = FileLockManager()
        with mgr.acquire_write_lock(db_path, timeout=2.0):
            assert os.path.exists(db_path + ".lock")

    def test_context_manager_usage(self, db_path):
        """FileLock works as a context manager via `with` statement."""
        mgr = FileLockManager()
        with mgr.acquire_write_lock(db_path, timeout=2.0) as lock:
            # lock should be the FileLock instance
            assert lock is not None

    def test_lock_timeout_with_competing_lock(self, db_path):
        """LockTimeoutError is raised when a competing lock is held."""
        mgr = FileLockManager()

        # Acquire the lock in the main thread and keep it held.
        first_lock = mgr.acquire_write_lock(db_path, timeout=2.0)

        # A second acquisition with a short timeout should fail.
        with pytest.raises(LockTimeoutError):
            mgr.acquire_write_lock(db_path, timeout=0.2)

        # Clean up the first lock.
        first_lock.__exit__(None, None, None)

    def test_reacquire_after_release(self, db_path):
        """After releasing a lock it can be re-acquired."""
        mgr = FileLockManager()

        with mgr.acquire_write_lock(db_path, timeout=2.0):
            pass  # lock released on exit

        # Should succeed without timeout.
        with mgr.acquire_write_lock(db_path, timeout=2.0):
            pass

    def test_lock_timeout_from_another_thread(self, db_path):
        """LockTimeoutError raised when another thread holds the lock."""
        mgr = FileLockManager()
        barrier = threading.Barrier(2, timeout=5)
        errors: list[BaseException] = []

        def hold_lock():
            with mgr.acquire_write_lock(db_path, timeout=2.0):
                barrier.wait()  # signal that lock is held
                barrier.wait()  # wait for main thread to finish its attempt

        t = threading.Thread(target=hold_lock)
        t.start()

        barrier.wait()  # wait until the thread holds the lock

        with pytest.raises(LockTimeoutError):
            mgr.acquire_write_lock(db_path, timeout=0.2)

        barrier.wait()  # let the thread release the lock
        t.join()
