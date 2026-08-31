import pytest

from app.platform.metrics import MetricEngine


engine=MetricEngine()


def scalar(result): return result["rows"][0]["value"]


def test_same_metric_api_queries_demo_and_ga4():
    assert scalar(engine.query("demo_ecommerce","users"))==5
    assert scalar(engine.query("ga4_ecommerce","users"))==5


def test_real_hmda_metrics_match_source_project():
    applications=scalar(engine.query("hmda_2025_de","applications"))
    denial_rate=round(scalar(engine.query("hmda_2025_de","denial_rate"))*100,2)
    if applications==55183:
        assert denial_rate==22.73
    else:
        assert applications==4 and denial_rate==33.33


def test_filtered_sum_and_distinct_count():
    assert scalar(engine.query("demo_ecommerce","orders"))==3
    assert scalar(engine.query("demo_ecommerce","gmv"))==727
    assert round(scalar(engine.query("demo_ecommerce","avg_order_amount")),2)==242.33
    assert round(scalar(engine.query("demo_ecommerce","aov_derived")),2)==242.33


def test_cumulative_and_period_change():
    cumulative=engine.query("demo_ecommerce","gmv",time_grain="day",calculation="cumulative")
    assert cumulative["rows"][-1]["value"]==727
    change=engine.query("demo_ecommerce","events",time_grain="day",calculation="period_change")
    assert change["rows"][0]["value"] is None


def test_dimension_and_time_grain_are_generated_safely():
    result=engine.query("demo_ecommerce","gmv",dimension="channel",time_grain="day")
    assert len(result["rows"])==6
    assert sum((row["value"] or 0) for row in result["rows"])==727
    assert "GROUP BY" in result["generated_sql"]


def test_unapproved_dimension_is_rejected():
    with pytest.raises(ValueError): engine.query("demo_ecommerce","users",dimension="user_id;drop")
