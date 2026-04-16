"""Utility functions for AKR.

Provides disk space checking for large artifact commits.
"""

from __future__ import annotations

import shutil

# Content length (in bytes/chars) above which a disk space check is performed
LARGE_ARTIFACT_THRESHOLD = 10240  # 10 KB

# Minimum free disk space required for large artifact commits (in bytes)
MIN_FREE_SPACE = 104857600  # 100 MB


def disk_space_check(path: str) -> int:
    """Check free disk space on the partition containing *path*.

    Uses :func:`shutil.disk_usage` to query the filesystem.

    Returns the number of free bytes available on the partition.
    """
    usage = shutil.disk_usage(path)
    return usage.free
