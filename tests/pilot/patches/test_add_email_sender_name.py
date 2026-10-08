from __future__ import annotations

import json
from pathlib import Path

from pilot.patches.add_email_sender_name import run


def _site(bench: Path, name: str, **config) -> Path:
    site = bench / "sites" / name
    site.mkdir(parents=True)
    (site / "site_config.json").write_text(json.dumps(config))
    return site / "site_config.json"


def _bench(tmp_path: Path) -> Path:
    bench = tmp_path / "benches" / "one"
    bench.mkdir(parents=True)
    (bench / "bench.toml").write_text('[bench]\nname = "one"\n')
    return bench


def test_a_site_without_a_sender_name_gets_its_first_label(tmp_path: Path) -> None:
    config = _site(_bench(tmp_path), "acme.example.com", db_name="acme")

    run(tmp_path / "benches")

    assert json.loads(config.read_text()) == {"db_name": "acme", "email_sender_name": "acme"}


def test_an_existing_sender_name_is_kept(tmp_path: Path) -> None:
    config = _site(_bench(tmp_path), "acme.example.com", email_sender_name="Acme Support")

    run(tmp_path / "benches")

    assert json.loads(config.read_text())["email_sender_name"] == "Acme Support"


def test_a_rename_link_is_skipped(tmp_path: Path) -> None:
    bench = _bench(tmp_path)
    _site(bench, "new.example.com")
    (bench / "sites" / "old.example.com").symlink_to(bench / "sites" / "new.example.com")

    run(tmp_path / "benches")

    config = json.loads((bench / "sites" / "new.example.com" / "site_config.json").read_text())
    assert config["email_sender_name"] == "new"
