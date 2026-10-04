from __future__ import annotations

import http.client
import json
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
from typing import IO

from pilot.exceptions import RemoteSiteError

_REQUEST_TIMEOUT_SECONDS = 30
# Per socket read, so a large download may take as long as it needs but a stalled one ends.
_DOWNLOAD_READ_TIMEOUT_SECONDS = 300
_BACKUP_TIMEOUT_SECONDS = 60 * 60
_BACKUP_POLL_SECONDS = 10


class RemoteFrappeSite:
    """A Frappe site reached as its Administrator, to copy a fresh backup. Method calls
    use GET: a session-cookie POST needs a CSRF token that only Frappe's desk receives."""

    def __init__(self, site: str, password: str) -> None:
        site = site.strip().rstrip("/")
        self.url = site if site.startswith(("https://", "http://")) else f"https://{site}"
        self.password = password
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))

    def login(self) -> None:
        """Fail with a clear message for a wrong password, 2FA, or an unreachable site."""
        body = urllib.parse.urlencode({"usr": "Administrator", "pwd": self.password}).encode()
        try:
            response = self._json(self._open("/api/method/login", data=body))
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                raise RemoteSiteError(f"The Administrator password for {self.url} is wrong.") from error
            raise RemoteSiteError(f"{self.url} refused the login: HTTP {error.code}.") from error
        if "verification" in response:
            raise RemoteSiteError(f"{self.url} asks for two-factor authentication, which is not supported.")

    def take_backup(self) -> dict[str, str]:
        """Start a backup with files on the remote and wait until it is complete. The remote
        runs it on its long queue and mails its Administrator."""
        previous = self.get_latest_backups().get("database")
        user = self._call("frappe.client.get_value", doctype="User", filters="Administrator", fieldname="email")
        self._call(
            "frappe.desk.page.backups.backups.schedule_files_backup",
            user_email=user.get("email") or "Administrator",
        )
        deadline = time.monotonic() + _BACKUP_TIMEOUT_SECONDS
        sizes: dict[str, int] = {}
        while time.monotonic() < deadline:
            backups = self.get_latest_backups()
            if self.is_new_complete_run(backups, previous):
                # Frappe writes each file at its final path, so a file is done once it stops growing.
                current = {part: self.get_backup_size(backups[part]) for part in ("database", "public", "private")}
                if current == sizes:
                    return backups
                sizes = current
            time.sleep(_BACKUP_POLL_SECONDS)
        raise RemoteSiteError(f"{self.url} did not finish its backup. Check that its background workers run.")

    @staticmethod
    def is_new_complete_run(backups: dict, previous: str | None) -> bool:
        """The database and both file archives come from one run, newer than `previous`.
        Frappe picks the newest file of each kind on its own, so they can mix runs."""
        paths = [backups.get(part) for part in ("database", "public", "private")]
        if not all(paths) or backups["database"] == previous:
            return False
        return len({Path(path).name.split("-", 1)[0] for path in paths}) == 1

    def get_backup_size(self, path: str) -> int:
        with self.open_backup(path) as response:
            return int(response.headers.get("Content-Length") or -1)

    def get_latest_backups(self) -> dict[str, str]:
        """Paths of the remote's newest backup files, by part (database, public, private, config)."""
        return self._call("frappe.utils.backups.fetch_latest_backups")

    def open_backup(self, path: str) -> IO[bytes]:
        """A backup file as a stream. Frappe serves /backups/<name> to System Managers."""
        return self._open(f"/backups/{urllib.parse.quote(Path(path).name)}", timeout=_DOWNLOAD_READ_TIMEOUT_SECONDS)

    def download_backup(self, path: str, directory: Path) -> Path:
        target = directory / Path(path).name
        with self.open_backup(path) as source, target.open("wb") as destination:
            shutil.copyfileobj(source, destination)
        return target

    def _call(self, method: str, **params: str) -> dict:
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        try:
            return self._json(self._open(f"/api/method/{method}{query}")).get("message") or {}
        except urllib.error.HTTPError as error:
            raise RemoteSiteError(f"{self.url} rejected {method}: HTTP {error.code}.") from error

    def _open(self, path: str, data: bytes | None = None, timeout: float = _REQUEST_TIMEOUT_SECONDS):
        try:
            return self._opener.open(urllib.request.Request(f"{self.url}{path}", data=data), timeout=timeout)
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as error:
            raise RemoteSiteError(f"Could not reach {self.url}: {error}") from error

    def _json(self, response) -> dict:
        with response:
            try:
                return json.loads(response.read() or b"{}")
            except ValueError as error:
                raise RemoteSiteError(f"{self.url} did not answer like a Frappe site.") from error
