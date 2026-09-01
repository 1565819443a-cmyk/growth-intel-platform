import pytest

from app.platform.analysis import funnel
from app.platform.quality import run_quality


def test_dataset_specific_quality_rules_pass():
    for dataset in ["demo_ecommerce","ga4_ecommerce","hmda_2025_de"]:
        report=run_quality(dataset)
        assert report["failed"]==0
        if dataset == "ga4_ecommerce":
            assert report["warnings"] == 1
        assert report["rules"]==3


def test_funnel_is_order_aware():
    result=funnel("demo_ecommerce")
    assert [x["users"] for x in result["steps"]]==[5,4,4,3,2]


def test_hmda_funnel_returns_explanation():
    with pytest.raises(ValueError,match="需要用户"): funnel("hmda_2025_de")

