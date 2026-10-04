from types import SimpleNamespace

from pilot.tasks.clear_cache import ClearCacheTask


def _bench(calls: list[str]) -> SimpleNamespace:
    site = SimpleNamespace(clear_cache=lambda: calls.append("site"))
    return SimpleNamespace(site=lambda name: site, clear_cache=lambda: calls.append("bench"))


def test_clear_cache_for_one_site(tmp_path):
    calls: list[str] = []
    ClearCacheTask(bench=_bench(calls), bench_root=tmp_path, site="a.localhost").clear_cache()
    assert calls == ["site"]


def test_clear_cache_without_a_site_clears_every_site(tmp_path):
    calls: list[str] = []
    ClearCacheTask(bench=_bench(calls), bench_root=tmp_path).clear_cache()
    assert calls == ["bench"]
