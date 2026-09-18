from flask import Blueprint, current_app

sites_bp = Blueprint("sites", __name__)


@sites_bp.url_value_preprocessor
def resolve_site_name(endpoint, values):
    """Resolve site aliases before authorization and route handling."""
    from pilot.core.bench import Bench

    name = (values or {}).get("name")
    if not name:
        return
    try:
        resolved = Bench(current_app.config["BENCH_ROOT"]).resolve_site_name(name)
    except Exception:
        return
    if resolved:
        values["name"] = resolved


from admin.backend.api.v1.sites import (  # noqa: E402
    apps,
    backups,
    central,
    configuration,
    core,
    domains,
    monitoring,
    storage,
    uptime,
)

__all__ = [
    "apps",
    "backups",
    "central",
    "configuration",
    "core",
    "domains",
    "monitoring",
    "sites_bp",
    "storage",
    "uptime",
]
