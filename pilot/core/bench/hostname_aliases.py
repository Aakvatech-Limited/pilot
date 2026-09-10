from __future__ import annotations

from typing import TYPE_CHECKING

from pilot.config.central import HostnameAlias
from pilot.utils import normalize_host

if TYPE_CHECKING:
    from pilot.core.bench import Bench


def _matching(aliases: list[HostnameAlias], alias_type: str, target: str) -> list[HostnameAlias]:
    return [
        alias
        for alias in aliases
        if alias.type == alias_type and normalize_host(alias.target) == normalize_host(target)
    ]


def retarget(bench: "Bench", alias_type: str, old_target: str, new_target: str) -> bool:
    """Retarget Central aliases under the shared config lock."""
    from pilot.config.common import CommonConfig

    if normalize_host(old_target) == normalize_host(new_target):
        return False

    benches_root = bench.path.parent
    # The file is shared, so read and write in one transaction.
    with CommonConfig.open(benches_root) as common:
        saved = _matching(common.central.hostname_aliases, alias_type, old_target)
        if not saved:
            return False
        for alias in saved:
            alias.target = new_target

    # Keep the caller's in-memory config in sync for nginx rendering.
    for alias in _matching(bench.config.central.hostname_aliases, alias_type, old_target):
        alias.target = new_target
    return True
