from __future__ import annotations

import psutil

from pilot.exceptions import BenchError

BUILD_MEMORY_SHARE = 0.85
MIN_BUILD_MEMORY_MB = 512


def build_memory_limit_mb() -> int:
    """How much memory one asset build is allowed to use, in MB.
    Kept under the free memory so a runaway build gets stopped
    on its own, instead of the machine running out and crashing.
    Each build sizes its own cap from free memory at that moment;
    builds running at the same time are not coordinated - a
    deliberate scope cut, not an oversight."""
    limit_mb = int(psutil.virtual_memory().available / (1024 * 1024) * BUILD_MEMORY_SHARE)
    if limit_mb < MIN_BUILD_MEMORY_MB:
        raise BenchError(
            f"Not enough free memory to build: only {limit_mb}MB available, "
            f"need at least {MIN_BUILD_MEMORY_MB}MB."
        )
    return limit_mb
