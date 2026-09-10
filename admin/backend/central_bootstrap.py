from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from flask import Flask

from pilot.integrations.central import CentralClientError

_POLL_SECONDS = 0.1
# Provisioning writes the credential within seconds of boot, so every real
# bootstrap lands inside this window and is picked up at the rate above.
_FAST_POLL_WINDOW_SECONDS = 120.0
# Past it nothing is arriving on a schedule, and polling ten times a second
# forever is waste - but a credential put in place by hand is still picked up.
_IDLE_POLL_SECONDS = 5.0


class CentralBootstrapWatcher:
    """Poll instance metadata and apply the Central credential when available."""

    def __init__(
        self,
        bench_root: Path,
        interval: float = _POLL_SECONDS,
        fast_window: float = _FAST_POLL_WINDOW_SECONDS,
        idle_interval: float = _IDLE_POLL_SECONDS,
    ) -> None:
        self.bench_root = bench_root
        self.interval = interval
        self.fast_window = fast_window
        self.idle_interval = idle_interval

    def install(self, app: Flask) -> None:
        threading.Thread(
            target=self._watch,
            name="central-bootstrap-watcher",
            daemon=True,
        ).start()

    def check_once(self) -> bool:
        """True once the credential has been written to this host's config."""
        from pilot.core.bench import Bench
        from pilot.integrations.central import apply_central_config

        try:
            return apply_central_config(Bench(self.bench_root))
        except CentralClientError as exc:
            # The cloud can still fix the attribute in place, so keep waiting.
            logging.error("Central bootstrap rejected the instance metadata: %s", exc)
            return False

    def _watch(self) -> None:
        # One short interval for as long as a credential could still plausibly be
        # on its way, never backing off within it: a host waiting on its
        # credential is a signup waiting on it, so pickup must not be delayed by a
        # poll that has slowed itself down. Only once nothing is arriving on any
        # schedule does it idle, rather than read metadata forever at that rate.
        fast_until = time.monotonic() + self.fast_window
        while not self.check_once():
            time.sleep(self.interval if time.monotonic() < fast_until else self.idle_interval)
        logging.info("Central bootstrap applied; this host is configured.")


def install_central_bootstrap_watcher(app: Flask, bench_root: Path) -> CentralBootstrapWatcher | None:
    """Start the watcher only on a host still awaiting its credential."""
    from pilot.config import BenchConfig

    try:
        config = BenchConfig.read(bench_root)
    except Exception as exc:
        logging.debug("Could not read bench.toml to decide the Central bootstrap watcher: %s", exc)
        return None

    if not config.central.is_awaiting_bootstrap:
        return None

    existing = app.extensions.get("central_bootstrap_watcher")
    if existing is not None:
        return existing

    watcher = CentralBootstrapWatcher(bench_root)
    app.extensions["central_bootstrap_watcher"] = watcher
    watcher.install(app)
    return watcher
