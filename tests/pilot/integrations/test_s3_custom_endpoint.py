from unittest.mock import Mock

from flask import Flask

from admin.backend.api.v1.settings import ConfigPatcher, s3_provider_options
from pilot.config import S3Config
from pilot.config.bench import BenchConfig
from pilot.core.bench.settings import s3_payload
from pilot.integrations.central import CentralClient, CentralClientError
from pilot.integrations.s3 import base


def bench_config() -> BenchConfig:
    return BenchConfig._from_dict(
        {
            "bench": {"name": "test-bench", "python": "3.14"},
            "apps": [
                {
                    "name": "frappe",
                    "repo": "https://github.com/frappe/frappe",
                    "branch": "develop",
                }
            ],
            "mariadb": {"root_password": "root"},
            "admin": {"domain": "admin.example.com"},
        }
    )


def test_custom_endpoint_overrides_provider_endpoint(monkeypatch) -> None:
    boto3 = Mock()
    monkeypatch.setattr(base, "load_boto3", lambda: None)
    monkeypatch.setattr(base, "boto3", boto3)
    monkeypatch.setattr(base, "Config", Mock(return_value="client-config"))

    storage = base.S3(
        access_key="access",
        secret_key="secret",
        region_name="in-mumbai",
        provider="garage",
        bucket_name="team-42-in-mumbai-backups",
        endpoint_url="https://s3.in-mumbai.example.test",
    )

    assert storage.endpoint_url == "https://s3.in-mumbai.example.test"
    boto3.client.assert_called_once_with(
        "s3",
        aws_access_key_id="access",
        aws_secret_access_key="secret",
        endpoint_url="https://s3.in-mumbai.example.test",
        region_name="in-mumbai",
        config="client-config",
    )


def test_custom_endpoint_is_a_complete_s3_configuration() -> None:
    config = S3Config(
        access_key="access",
        secret_key="secret",
        bucket="backups",
        provider="garage",
        region="in-mumbai",
        endpoint_url="https://s3.in-mumbai.example.test",
    )

    assert config.is_configured is True


def test_a_provider_update_can_explicitly_clear_the_managed_endpoint() -> None:
    config = bench_config()
    config.s3 = S3Config(
        access_key="garage-access",
        secret_key="garage-secret",
        bucket="managed-backups",
        provider="garage",
        region="in-mumbai",
        endpoint_url="https://s3.in-mumbai.example.test",
    )

    error = ConfigPatcher(
        config,
        {
            "s3": {
                "access_key": "aws-access",
                "secret_key": "aws-secret",
                "bucket": "customer-backups",
                "provider": "aws",
                "region": "us-east-1",
                "endpoint_url": "",
            }
        },
    ).apply()

    assert error is None
    assert config.s3.endpoint_url == ""


def test_s3_payload_tracks_the_custom_endpoint() -> None:
    config = bench_config()
    config.s3.endpoint_url = "https://s3.in-mumbai.example.test"

    assert s3_payload(config)["endpoint_url"] == "https://s3.in-mumbai.example.test"


FRAPPE_REGIONS = {"Aradhya-Local": "https://s3.aradhya-local.example.test"}


def frappe_s3_update(region: str) -> dict:
    return {
        "s3": {
            "access_key": "garage-access",
            "secret_key": "garage-secret",
            "bucket": "3836-aradhya-local-media",
            "provider": "frappe",
            "region": region,
            "endpoint_url": "https://elsewhere.example.test",
        }
    }


def test_frappe_storage_takes_its_endpoint_from_central(monkeypatch) -> None:
    monkeypatch.setattr(CentralClient, "storage_regions", lambda self: FRAPPE_REGIONS)
    config = bench_config()

    error = ConfigPatcher(config, frappe_s3_update("Aradhya-Local")).apply()

    assert error is None
    assert config.s3.endpoint_url == "https://s3.aradhya-local.example.test"


def test_frappe_storage_refuses_a_region_central_does_not_serve(monkeypatch) -> None:
    monkeypatch.setattr(CentralClient, "storage_regions", lambda self: FRAPPE_REGIONS)

    error = ConfigPatcher(bench_config(), frappe_s3_update("elsewhere")).apply()

    assert error == "s3.region 'elsewhere' does not serve Frappe object storage."


def test_frappe_storage_reports_an_unreachable_central(monkeypatch) -> None:
    def unreachable(self):
        raise CentralClientError("Cannot reach Central")

    monkeypatch.setattr(CentralClient, "storage_regions", unreachable)

    error = ConfigPatcher(bench_config(), frappe_s3_update("Aradhya-Local")).apply()

    assert error == "Could not read Frappe storage regions from Central: Cannot reach Central"


def test_frappe_is_offered_only_on_a_central_bench(monkeypatch) -> None:
    monkeypatch.setattr(CentralClient, "storage_regions", lambda self: FRAPPE_REGIONS)
    config = bench_config()

    with Flask(__name__).app_context():
        assert "frappe" not in [option["value"] for option in s3_provider_options(config)]

        config.central.enabled = True
        options = s3_provider_options(config)

    assert options[0] == {"value": "frappe", "label": "Frappe Cloud", "regions": ["Aradhya-Local"]}


def test_an_unreachable_central_leaves_the_other_providers(monkeypatch) -> None:
    def unreachable(self):
        raise CentralClientError("Cannot reach Central")

    monkeypatch.setattr(CentralClient, "storage_regions", unreachable)
    config = bench_config()
    config.central.enabled = True

    with Flask(__name__).app_context():
        options = s3_provider_options(config)

    assert [option["value"] for option in options] == list(base.SUPPORTED_REGIONS)
