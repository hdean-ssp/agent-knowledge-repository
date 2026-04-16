"""File-based locking for serializing writes to the SQLite database.

Uses ``fcntl.flock`` with a dedicated ``.lock`` file adjacent to the
database so that concurrent processes never corrupt the DB.
"""

from __future__ import annotations

import errno
import fcntl
import os
import time
from types import TracebackType
from typing import Optional, Type

from akr.errors import LockTimeoutError


class FileLock:
    """Context manager wrapping an acquired file lock.

    Holds the open file descriptor and releases the lock on exit.
    """

    def __init__(self, fd: int, lock_path: str) -> None:
        self._fd = fd
        self._lock_path = lock_path

    # -- context manager protocol ------------------------------------------

    def __enter__(self) -> "FileLock":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)


class FileLockManager:
    """Acquire exclusive file-system locks for database write operations."""

    def acquire_write_lock(
        self, db_path: str, timeout: float = 10.0
    ) -> FileLock:
        """Acquire an exclusive lock on ``<db_path>.lock``.

        Parameters
        ----------
        db_path:
            Path to the SQLite database file.  The lock file will be
            ``<db_path>.lock``.
        timeout:
            Maximum seconds to wait for the lock.  Defaults to 10.

        Returns
        -------
        FileLock
            A context-manager that releases the lock when exited.

        Raises
        ------
        LockTimeoutError
            If the lock cannot be acquired within *timeout* seconds.
        """
        lock_path = db_path + ".lock"

        # Open (or create) the lock file.
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)

        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return FileLock(fd, lock_path)
            except OSError as exc:
                if exc.errno not in (errno.EAGAIN, errno.EACCES):
                    os.close(fd)
                    raise
                if time.monotonic() >= deadline:
                    os.close(fd)
                    raise LockTimeoutError(path=lock_path) from exc
                time.sleep(0.05)
