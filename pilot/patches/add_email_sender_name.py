from __future__ import annotations

import json
from pathlib import Path

PATCH_NAME = Path(__file__).stem


def run(benches_root: Path) -> None:
    """Give each site the sender name that new sites get. A site that already has one keeps it."""
    from pilot.internal.patch_state import is_applied, mark_applied

    for bench_dir in sorted(benches_root.glob("*")):
        if not bench_dir.is_dir() or not (bench_dir / "bench.toml").exists():
            continue
        if is_applied(bench_dir, PATCH_NAME):
            continue
        for config_path in sorted((bench_dir / "sites").glob("*/site_config.json")):
            # A rename leaves a short-lived link under the old name.
            if not config_path.parent.is_symlink():
                add_email_sender_name(config_path)
        mark_applied(bench_dir, PATCH_NAME)


def add_email_sender_name(config_path: Path) -> None:
    from pilot.config.site import email_sender_name
    from pilot.internal.atomic_file import exclusive_file_lock, replace_private_text_locked

    with exclusive_file_lock(config_path):
        config = json.loads(config_path.read_text())
        if "email_sender_name" in config:
            return
        config["email_sender_name"] = email_sender_name(config_path.parent.name)
        replace_private_text_locked(config_path, json.dumps(config, indent=1))


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from pilot.utils import benches_dir

    run(benches_dir())
