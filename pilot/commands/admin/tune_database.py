from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from pilot.commands import BenchMode, Command
from pilot.config.common import CommonConfig
from pilot.core.server import Server
from pilot.managers.database.mariadb import MariaDBManager


@dataclass(kw_only=True)
class TuneDatabaseCommand(Command):
    name: ClassVar[str] = "database-tune"
    group: ClassVar[str] = "admin"
    help: ClassVar[str] = "Size Pilot's MariaDB config and service memory limits for this host."
    # One MariaDB serves every bench on the host, configured in common_config.toml.
    bench_mode: ClassVar[BenchMode] = BenchMode.NONE

    def run(self) -> None:
        config = CommonConfig.read(Server().benches_dir)
        manager = MariaDBManager(config.mariadb)
        sizing = manager.tune_to_host()
        self.report(
            f"Sized MariaDB for {sizing.total_memory_mb} MiB: "
            f"buffer pool {sizing.innodb_buffer_pool_mb} MiB, MemoryMax {sizing.memory_max_mb} MiB."
        )
        if manager.is_running():
            self.report("MariaDB is running. Restart it to apply the new sizing.")
