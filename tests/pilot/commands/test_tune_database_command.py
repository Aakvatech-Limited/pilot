from __future__ import annotations

from unittest.mock import patch

from pilot.commands.admin.tune_database import TuneDatabaseCommand
from pilot.config import MariaDBConfig
from pilot.config.common import CommonConfig
from pilot.core.mariadb_memory import calculate_mariadb_memory

MODULE = "pilot.commands.admin.tune_database"


def test_tunes_the_host_mariadb_from_common_config(capsys) -> None:
    config = CommonConfig(mariadb=MariaDBConfig(port=3311))
    with (
        patch(f"{MODULE}.CommonConfig.read", return_value=config),
        patch(f"{MODULE}.MariaDBManager") as manager_class,
    ):
        manager = manager_class.return_value
        manager.tune_to_host.return_value = calculate_mariadb_memory(1024)
        manager.is_running.return_value = False
        TuneDatabaseCommand().run()

    manager_class.assert_called_once_with(config.mariadb)
    manager.tune_to_host.assert_called_once()
    assert "Sized MariaDB for 1024 MiB" in capsys.readouterr().out


def test_asks_for_restart_when_mariadb_is_running(capsys) -> None:
    with (
        patch(f"{MODULE}.CommonConfig.read", return_value=CommonConfig()),
        patch(f"{MODULE}.MariaDBManager") as manager_class,
    ):
        manager = manager_class.return_value
        manager.tune_to_host.return_value = calculate_mariadb_memory(4096)
        manager.is_running.return_value = True
        TuneDatabaseCommand().run()

    assert "Restart it to apply" in capsys.readouterr().out
