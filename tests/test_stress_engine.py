import pytest
from dealvanguard.schemas import FinancialMetrics
from dealvanguard.stress_engine import DealStressEngine


@pytest.fixture
def sample_metrics():
    return FinancialMetrics(
        arr=1200000.0,
        mrr=100000.0,
        net_revenue_retention=110.0,
        gross_margin=80.0,
        cac=4000.0,
        ltv=20000.0,
        ltv_cac_ratio=5.0,
        monthly_burn_rate=20000.0,
        runway_months=12.0,
        total_debt=500000.0,
        ebitda=200000.0,
    )


def test_revenue_haircut_scenario_default(sample_metrics):
    engine = DealStressEngine(sample_metrics)
    scenarios = engine.run_revenue_haircut_scenario()

    assert len(scenarios) == 3
    assert scenarios[0]["haircut_pct"] == 10.0
    assert scenarios[0]["stressed_arr"] == 1080000.0
    assert scenarios[0]["monthly_burn"] == 30000.0
    assert scenarios[0]["projected_runway_months"] == 8.0

    assert scenarios[2]["haircut_pct"] == 30.0
    assert scenarios[2]["stressed_arr"] == 840000.0
    assert scenarios[2]["monthly_burn"] == 50000.0
    assert scenarios[2]["projected_runway_months"] == 4.8


def test_revenue_haircut_scenario_custom_pct(sample_metrics):
    engine = DealStressEngine(sample_metrics)
    scenarios = engine.run_revenue_haircut_scenario(haircut_percentages=[0.50])

    assert len(scenarios) == 1
    assert scenarios[0]["haircut_pct"] == 50.0
    assert scenarios[0]["stressed_arr"] == 600000.0
    assert scenarios[0]["monthly_burn"] == 70000.0


def test_revenue_haircut_scenario_no_runway():
    metrics = FinancialMetrics(
        arr=1000000.0,
        mrr=83333.33,
        net_revenue_retention=100.0,
        gross_margin=70.0,
        cac=3000.0,
        ltv=15000.0,
        ltv_cac_ratio=5.0,
        monthly_burn_rate=10000.0,
        runway_months=None,
        total_debt=0.0,
        ebitda=100000.0,
    )
    engine = DealStressEngine(metrics)
    scenarios = engine.run_revenue_haircut_scenario()

    assert scenarios[0]["projected_runway_months"] is None


def test_calculate_dscr_healthy(sample_metrics):
    engine = DealStressEngine(sample_metrics)
    result = engine.calculate_debt_service_coverage(interest_rate=0.08)

    assert result["annual_interest"] == 40000.0
    assert result["dscr"] == 5.0
    assert result["status"] == "Healthy"


def test_calculate_dscr_distressed(sample_metrics):
    distressed_metrics = FinancialMetrics(
        arr=1200000.0,
        mrr=100000.0,
        net_revenue_retention=110.0,
        gross_margin=80.0,
        cac=4000.0,
        ltv=20000.0,
        ltv_cac_ratio=5.0,
        monthly_burn_rate=20000.0,
        runway_months=12.0,
        total_debt=1000000.0,
        ebitda=50000.0,
    )
    engine = DealStressEngine(distressed_metrics)
    result = engine.calculate_debt_service_coverage(interest_rate=0.10)

    assert result["annual_interest"] == 100000.0
    assert result["dscr"] == 0.5
    assert result["status"] == "Distressed"


def test_calculate_dscr_no_debt():
    metrics = FinancialMetrics(
        arr=1000000.0,
        mrr=83333.33,
        net_revenue_retention=100.0,
        gross_margin=70.0,
        cac=3000.0,
        ltv=15000.0,
        ltv_cac_ratio=5.0,
        monthly_burn_rate=10000.0,
        total_debt=0.0,
        ebitda=100000.0,
    )
    engine = DealStressEngine(metrics)
    result = engine.calculate_debt_service_coverage()

    assert result["dscr"] is None
    assert result["annual_interest"] == 0.0
    assert result["status"] == "No Debt"


def test_calculate_dscr_zero_interest_rate(sample_metrics):
    engine = DealStressEngine(sample_metrics)
    result = engine.calculate_debt_service_coverage(interest_rate=0.0)

    assert result["dscr"] is None
    assert result["annual_interest"] == 0.0
    assert result["status"] == "Zero Interest"