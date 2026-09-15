from __future__ import annotations

import psutil

from pilot.exceptions import BenchError

BUILD_MEMORY_SHARE = 0.85
MIN_BUILD_MEMORY_MB = 512


def build_memory_limit_mb() -> int:
    """Memory one asset build may use before the kernel kills it. A share of what
    is free rather than of total, so the limit is one the host can honour and a
    runaway build dies instead of freezing the machine."""
    limit_mb = int(psutil.virtual_memory().available / (1024 * 1024) * BUILD_MEMORY_SHARE)
    if limit_mb < MIN_BUILD_MEMORY_MB:
        raise BenchError(
            f"Not enough free memory to build: only {limit_mb}MB available, "
            f"need at least {MIN_BUILD_MEMORY_MB}MB."
        )
    return limit_mb
