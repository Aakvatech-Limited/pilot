from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from flask import Flask

from admin.backend.central_bootstrap import (
    CentralBootstrapWatcher,
    install_central_bootstrap_watcher,
)
from admin.backend.watchdog import AdminProcessOwner
from pilot.config import BenchConfig
from pilot.config.common import CommonConfig
from pilot.integrations.central import CentralClientError
from tests.pilot.integrations.test_central_client import _bench
from tests.pilot.integrations.test_central_metadata import _ATTRIBUTE


class _FakeOwner(AdminProcessOwner):
    """Records the stop instead of signalling this test process."""

    def __init__(self) -> None:
        super().__init__(pid=0, parent_owned=False)
        self.terminated = False

    def terminate(self) -> bool:
        self.terminated = True
        return True


def _awaiting_host(tmp_path: Path) -> Path:
    bench = _bench(tmp_path)
    common = CommonConfig.read(bench.path.parent)
    common.central.enabled = True
    common.write(bench.path.parent)
    return bench.path


def _staged(value: str | None):
    """The raw attribute, so the real parsing still runs."""
    return patch(
        "pilot.integrations.central.metadata.InstanceMetadata.get_attribute",
        return_value=value,
    )


def test_a_pass_without_the_attribute_keeps_waiting(tmp_path: Path) -> None:
    owner = _FakeOwner()
    watcher = CentralBootstrapWatcher(_awaiting_host(tmp_path), owner)

    with _staged(None):
        assert watcher.check_once() is False

    assert owner.terminated is False


def test_the_attribute_arriving_writes_config_and_stops_the_admin(tmp_path: Path) -> None:
    bench_root = _awaiting_host(tmp_path)
    owner = _FakeOwner()

    with _staged(json.dumps(_ATTRIBUTE)):
        assert CentralBootstrapWatcher(bench_root, owner).check_once() is True

    assert owner.terminated is True
    saved = BenchConfig.read(bench_root)
    assert saved.central.bootstrapped is True
    assert saved.admin.jwks_audience == "vm-boot-1"


def test_a_malformed_attribute_is_logged_and_retried(tmp_path: Path) -> None:
    owner = _FakeOwner()
    watcher = CentralBootstrapWatcher(_awaiting_host(tmp_path), owner)

    with patch(
        "pilot.integrations.central.metadata.InstanceMetadata.get_credentials",
        side_effect=CentralClientError("bad attribute"),
    ):
        assert watcher.check_once() is False

    assert owner.terminated is False


def test_the_watcher_starts_only_while_a_host_is_awaiting_bootstrap(tmp_path: Path) -> None:
    bench_root = _awaiting_host(tmp_path)
    app = Flask(__name__)

    with patch.object(CentralBootstrapWatcher, "install") as install:
        assert install_central_bootstrap_watcher(app, bench_root) is not None
    install.assert_called_once()


def test_the_watcher_does_not_start_on_a_bootstrapped_host(tmp_path: Path) -> None:
    bench_root = _awaiting_host(tmp_path)
    common = CommonConfig.read(bench_root.parent)
    common.central.bootstrapped = True
    common.write(bench_root.parent)

    assert install_central_bootstrap_watcher(Flask(__name__), bench_root) is None


def test_the_watcher_does_not_start_on_a_self_hosted_bench(tmp_path: Path) -> None:
    bench = _bench(tmp_path)  # central.enabled is False

    assert install_central_bootstrap_watcher(Flask(__name__), bench.path) is None


def test_bootstrap_reports_pending_while_the_host_waits(tmp_path: Path) -> None:
    from admin.backend.app import create_app

    bench_root = _awaiting_host(tmp_path)
    body = create_app(bench_root).test_client().get("/api/v1/bootstrap").get_json()

    assert body == {"mode": "pending", "name": bench_root.name, "enabled": True}


def test_bootstrap_leaves_pending_once_the_credential_lands(tmp_path: Path) -> None:
    from admin.backend.app import create_app

    bench_root = _awaiting_host(tmp_path)
    with _staged(json.dumps(_ATTRIBUTE)):
        CentralBootstrapWatcher(bench_root, _FakeOwner()).check_once()

    body = create_app(bench_root).test_client().get("/api/v1/bootstrap").get_json()

    assert body["mode"] != "pending"
