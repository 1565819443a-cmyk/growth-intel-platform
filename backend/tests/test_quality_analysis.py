import pytest

from app.platform.analysis import funnel
from app.platform.quality import run_quality
from app.platform.registry import DatasetRegistry


def test_dataset_specific_quality_rules_pass():
    for dataset in ["demo_ecommerce","ga4_ecommerce","hmda_2025_de"]:
        report=run_quality(dataset)
        assert report["failed"]==0
        assert report["rules"]==3


def test_warning_severity_is_not_counted_as_failure(tmp_path):
    config_dir = tmp_path / "configs/datasets"
    config_dir.mkdir(parents=True)
    (tmp_path / "events.csv").write_text(
        "event_name,transaction_id\npurchase,\n", encoding="utf-8"
    )
    (config_dir / "warning_case.yaml").write_text(
        """id: warning_case
name: Warning case
source: {type: csv, path: events.csv}
mappings: {event_type: event_name, order_id: transaction_id}
metrics: {events: {name: Events, aggregation: count, owner: test, version: 1.0.0}}
quality_rules:
  - {id: order_not_null, type: conditional_non_null, field: transaction_id, when: "event_name='purchase'", severity: warning}
""",
        encoding="utf-8",
    )
    report = run_quality("warning_case", DatasetRegistry(tmp_path))
    assert report["warnings"] == 1
    assert report["failed"] == 0


def test_funnel_is_order_aware():
    result=funnel("demo_ecommerce")
    assert [x["users"] for x in result["steps"]]==[5,4,4,3,2]


def test_hmda_funnel_returns_explanation():
    with pytest.raises(ValueError,match="需要用户"): funnel("hmda_2025_de")

