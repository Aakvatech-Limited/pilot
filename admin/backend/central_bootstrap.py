from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from flask import Flask

from admin.backend.watchdog import AdminProcessOwner
from pilot.integrations.central import CentralClientError

_POLL_SECONDS = 0.5


class CentralBootstrapWatcher:
    """Polls metadata for this host's Central credential. On arrival it writes the
    config and stops the admin, which its socket re-activates."""

    def __init__(
        self,
        bench_root: Path,
        owner: AdminProcessOwner,
        interval: float = _POLL_SECONDS,
    ) -> None:
        self.bench_root = bench_root
        self.owner = owner
        self.interval = interval

    def install(self, app: Flask) -> None:
        threading.Thread(
            target=self._watch,
            name="central-bootstrap-watcher",
            daemon=True,
        ).start()

    def check_once(self) -> bool:
        """True once the credential is written and the admin asked to stop."""
        from pilot.core.bench import Bench
        from pilot.integrations.central import apply_central_config

        try:
            if not apply_central_config(Bench(self.bench_root)):
                return False
        except CentralClientError as exc:
            # The cloud can still fix the attribute in place, so keep waiting.
            logging.error("Central bootstrap rejected the instance metadata: %s", exc)
            return False

        return self.owner.terminate()

    def _watch(self) -> None:
        while True:
            if self.check_once():
                return

            time.sleep(self.interval)


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

    watcher = CentralBootstrapWatcher(bench_root, AdminProcessOwner.current())
    app.extensions["central_bootstrap_watcher"] = watcher
    watcher.install(app)
    return watcher
