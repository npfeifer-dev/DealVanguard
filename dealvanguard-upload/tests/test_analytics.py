import pytest

from dealvanguard.analytics import DealAnalyticsEngine
from dealvanguard.schemas import FinancialMetrics


def make_metrics(**overrides):
    base = dict(
        arr=2_400_000.0, mrr=200_000.0, net_revenue_retention=92.0, gross_margin=68.0,
        cac=15_000.0, ltv=40_000.0, ltv_cac_ratio=2.67, monthly_burn_rate=80_000.0,
        runway_months=8.0, total_debt=150_000.0, ebitda=-600_000.0,
    )
    base.update(overrides)
    return FinancialMetrics(**base)


def test_percent_scale_inputs_produce_sensible_rule_of_40():
    summary = DealAnalyticsEngine.analyze_deal(make_metrics())
    # (92 - 100) + (-600k / 2.4M = -25%) = -33
    assert summary.rule_of_40 == pytest.approx(-33.0)


def test_weak_deal_triggers_expected_flags():
    flags = " ".join(DealAnalyticsEngine.analyze_deal(make_metrics()).red_flags)
    assert "Low gross margin" in flags
    assert "LTV/CAC" in flags
    assert "Net revenue contraction" in flags
    assert "Rule of 40" in flags


def test_healthy_deal_has_no_flags():
    metrics = make_metrics(
        net_revenue_retention=118.0, gross_margin=82.0, ltv=60_000.0, ltv_cac_ratio=4.0,
        ebitda=900_000.0, total_debt=0.0, runway_months=30.0, monthly_burn_rate=20_000.0,
    )
    summary = DealAnalyticsEngine.analyze_deal(metrics)
    assert summary.red_flags == []
    assert summary.rule_of_40 > 40


def test_runway_stress_is_none_without_burn():
    summary = DealAnalyticsEngine.analyze_deal(make_metrics(monthly_burn_rate=0.0, runway_months=99.0))
    assert summary.runway_stress_tested is None
