from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from pilot.commands import Arg, Command


@dataclass(kw_only=True)
class SetupTelemetryCommand(Command):
    """Write this bench's Datum credential and install the log shipper."""

    name: ClassVar[str] = "telemetry"
    help: ClassVar[str] = "Write the metrics credential to common_config.toml and install Fluent Bit."
    group: ClassVar[str] = "setup"

    endpoint: Annotated[
        str | None,
        Arg(
            help="Telemetry base URL (e.g. https://datum.internal), written to common_config.toml. "
            "Fetched from Central when omitted"
        ),
    ] = None
    token: Annotated[
        str | None,
        Arg(
            help="Bearer JWT for this region's Datum, written to common_config.toml. Fetched from Central when omitted"
        ),
    ] = None

    def run(self) -> None:
        """Metrics and logs share one credential, so both are configured here.

        Only logs need installing: the monitor builds its shipper from this same config on
        every tick, so writing it is all metrics take."""
        from pilot.managers.fluentbit import LogsConfigurator

        self._apply_credential()
        telemetry = self.bench.config.telemetry

        if not (telemetry.endpoint and telemetry.token):
            self.report(
                "Telemetry is not configured. Set [telemetry] endpoint in common_config.toml,\n"
                "or pass --endpoint. Both are fetched from Central when it knows this region's Datum."
            )
            return

        self.report(
            f"Metrics {'will ship to ' + telemetry.endpoint if telemetry.is_shipping_metrics else 'are off'}."
        )
        if not telemetry.is_shipping_logs:
            self.report("Logs are off. Set [telemetry] logs_enabled to ship them.")
            return

        configurator = LogsConfigurator(self.bench)
        configurator.setup()
        configurator.install(telemetry)
        self.report("Fluent Bit installed. Logs will ship to " + telemetry.endpoint)

    def _apply_credential(self) -> None:
        """What was passed, or what Central hands out, written to the bench and the file."""
        endpoint, token = self.endpoint, self.token
        if not (endpoint and token):
            fetched_endpoint, fetched_token = self._fetch_credential()
            endpoint = endpoint or fetched_endpoint
            token = token or fetched_token

        if not (endpoint or token):
            return

        from pilot.config import BenchConfig

        with BenchConfig.open(self.bench.path) as config:
            if endpoint:
                config.telemetry.endpoint = endpoint
            if token:
                config.telemetry.token = token

        if endpoint:
            self.bench.config.telemetry.endpoint = endpoint
        if token:
            self.bench.config.telemetry.token = token

    def _fetch_credential(self) -> tuple[str | None, str | None]:
        """Central mints the JWT and names the region's Datum to present it to."""
        from pilot.integrations.central import CentralClient

        if not self.bench.config.central.enabled:
            return None, None
        credentials = CentralClient().datum_token()

        return credentials.get("endpoint") or None, credentials.get("token") or None
