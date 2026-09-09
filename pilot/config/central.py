from dataclasses import dataclass


@dataclass
class CentralConfig:
    """Central-managed state. The endpoint and auth token live in metadata, not here."""

    enabled: bool = False
    bootstrapped: bool = False

    @property
    def is_awaiting_bootstrap(self) -> bool:
        """Central-managed, but the credential has not arrived."""
        return self.enabled and not self.bootstrapped

    @classmethod
    def from_dict(cls, data: dict) -> "CentralConfig":
        return cls(
            enabled=bool(data.get("enabled", False)),
            bootstrapped=bool(data.get("bootstrapped", False)),
        )
