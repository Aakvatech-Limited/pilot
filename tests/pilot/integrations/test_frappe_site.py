from __future__ import annotations

import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

import pytest

from pilot.exceptions import RemoteSiteError
from pilot.integrations import frappe_site
from pilot.integrations.frappe_site import RemoteFrappeSite


class FakeFrappe(BaseHTTPRequestHandler):
    """Answers the few endpoints a remote restore uses, like a Frappe site does."""

    backups: ClassVar[dict] = {"database": "./old/private/backups/1-database.sql.gz", "public": None, "private": None}
    scheduled_for: ClassVar[list[str]] = []

    def do_POST(self) -> None:
        form = urllib.parse.parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
        is_right = form["pwd"] == ["right"]
        self._send(
            {"message": "Logged In" if is_right else "Incorrect password"},
            status=200 if is_right else 401,
            cookie="sid=abc" if is_right else "",
        )

    def do_GET(self) -> None:
        path, _, query = self.path.partition("?")
        params = urllib.parse.parse_qs(query)
        if "sid=abc" not in (self.headers.get("Cookie") or ""):
            self._send({}, status=403)
            return
        if path.startswith("/backups/"):
            self._send_bytes(f"content of {path.rsplit('/', 1)[1]}".encode())
            return
        method = path.removeprefix("/api/method/")
        if method == "frappe.client.get_value":
            self._send({"message": {"email": "admin@example.com"}})
            return
        if method == "frappe.desk.page.backups.backups.schedule_files_backup":
            FakeFrappe.scheduled_for.append(params["user_email"][0])
            FakeFrappe.backups = {
                "database": "./s/private/backups/2-database.sql.gz",
                "public": "./s/private/backups/2-files.tar",
                "private": "./s/private/backups/2-private-files.tar",
                "config": "./s/private/backups/2-site_config_backup.json",
            }
            self._send({"message": None})
            return
        if method == "frappe.utils.backups.fetch_latest_backups":
            self._send({"message": FakeFrappe.backups})
            return
        self._send({}, status=404)

    def _send(self, body: dict, status: int = 200, cookie: str = "") -> None:
        self.send_response(status)
        if cookie:
            self.send_header("Set-Cookie", f"{cookie}; Path=/")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def _send_bytes(self, data: bytes) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args) -> None:
        pass


@pytest.fixture
def remote_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeFrappe)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


def test_a_wrong_password_is_reported_before_any_work(remote_url: str) -> None:
    with pytest.raises(RemoteSiteError, match=r"password .* is wrong"):
        RemoteFrappeSite(remote_url, "wrong").login()


def test_a_fresh_backup_is_taken_and_downloaded(remote_url: str, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(frappe_site, "_BACKUP_POLL_SECONDS", 0)
    remote = RemoteFrappeSite(remote_url, "right")
    remote.login()

    backups = remote.take_backup()
    downloaded = remote.download_backup(backups["public"], tmp_path)

    assert FakeFrappe.scheduled_for == ["admin@example.com"]
    assert backups["database"].endswith("2-database.sql.gz")
    assert downloaded.read_text() == "content of 2-files.tar"


def test_an_unreachable_site_is_a_clear_error() -> None:
    with pytest.raises(RemoteSiteError, match="Could not reach"):
        RemoteFrappeSite("http://127.0.0.1:9", "right").login()


def test_files_from_different_runs_are_not_a_complete_backup() -> None:
    """Frappe picks the newest file of each kind on its own, so an older run's archives
    can sit beside a dump that is still being written."""
    mixed = {"database": "./s/2-database.sql.gz", "public": "./s/1-files.tar", "private": "./s/1-private-files.tar"}
    same = {"database": "./s/2-database.sql.gz", "public": "./s/2-files.tar", "private": "./s/2-private-files.tar"}

    assert RemoteFrappeSite.is_new_complete_run(mixed, previous="./s/1-database.sql.gz") is False
    assert RemoteFrappeSite.is_new_complete_run(same, previous="./s/1-database.sql.gz") is True
    assert RemoteFrappeSite.is_new_complete_run(same, previous="./s/2-database.sql.gz") is False
