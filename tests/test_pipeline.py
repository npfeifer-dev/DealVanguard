"""End-to-end check without an API key: sample deal -> database -> analytics -> stress tests."""
from dealvanguard.analytics import DealAnalyticsEngine
from dealvanguard.database import DatabaseManager, record_to_extraction
from dealvanguard.samples import load_sample_deal
from dealvanguard.stress_engine import DealStressEngine


def test_sample_deal_flows_through_the_pipeline():
    deal = load_sample_deal()
    db = DatabaseManager(db_path=":memory:")
    db.save_deal("DEAL-PIPE-001", deal)

    rebuilt = record_to_extraction(db.fetch_all_deals()[0])
    assert rebuilt.metrics == deal.metrics

    summary = DealAnalyticsEngine.analyze_deal(rebuilt.metrics)
    assert summary.red_flags  # the sample deal is intentionally a weak deal

    scenarios = DealStressEngine(rebuilt.metrics).run_revenue_haircut_scenario()
    runways = [s["projected_runway_months"] for s in scenarios]
    assert runways == sorted(runways, reverse=True)  # bigger haircut, shorter runway
