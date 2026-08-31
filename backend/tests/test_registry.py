from app.platform.registry import DatasetRegistry, capabilities


def test_registry_lists_three_structurally_different_datasets():
    rows=DatasetRegistry().list()
    assert {r["id"] for r in rows}=={"demo_ecommerce","ga4_ecommerce","hmda_2025_de"}
    assert all(r["available"] for r in rows)


def test_ga4_capabilities_are_dynamic():
    caps=capabilities(DatasetRegistry().load("ga4_ecommerce"))
    assert caps["funnel"]["enabled"]
    assert caps["retention"]["enabled"]
    assert caps["institution"]["enabled"] is False


def test_hmda_disables_event_only_analyses():
    caps=capabilities(DatasetRegistry().load("hmda_2025_de"))
    assert not caps["funnel"]["enabled"]
    assert not caps["retention"]["enabled"]
    assert caps["institution"]["enabled"]
    assert caps["gmv"]["enabled"]

