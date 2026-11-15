import pytest
from dealvanguard.database import DatabaseManager, record_to_extraction
from dealvanguard.schemas import (
    ExtractionResult,
    DealMetadata,
    FinancialMetrics,
    CapitalStructureType,
)


@pytest.fixture
def db():
    manager = DatabaseManager(db_path=":memory:")
    return manager


@pytest.fixture
def sample_extraction():
    meta = DealMetadata(
        company_name="Acme SaaS",
        industry_sector="B2B Software",
        capital_structure=CapitalStructureType.EQUITY,
    )
    metrics = FinancialMetrics(
        arr=1200000.0,
        mrr=100000.0,
        net_revenue_retention=110.0,
        gross_margin=80.0,
        cac=4000.0,
        ltv=20000.0,
        ltv_cac_ratio=5.0,
        monthly_burn_rate=20000.0,
        runway_months=18.0,
        total_debt=0.0,
        ebitda=300000.0,
    )
    return ExtractionResult(
        metadata=meta,
        metrics=metrics,
        key_risks_identified=["Customer concentration"],
        confidence_score=0.95,
    )


def test_database_initialization(db):
    deals = db.fetch_all_deals()
    assert deals == []


def test_save_and_fetch_deal(db, sample_extraction):
    deal_id = "DEAL-TEST-001"
    db.save_deal(deal_id, sample_extraction)

    deals = db.fetch_all_deals()
    assert len(deals) == 1
    
    row = deals[0]
    assert row["deal_id"] == deal_id
    assert row["company_name"] == "Acme SaaS"
    assert row["arr"] == 1200000.0
    assert row["confidence_score"] == 0.95

def test_saved_deal_round_trips_to_extraction(db, sample_extraction):
    db.save_deal("DEAL-RT-001", sample_extraction)
    rebuilt = record_to_extraction(db.fetch_all_deals()[0])

    assert rebuilt.metadata.company_name == "Acme SaaS"
    assert rebuilt.metrics.arr == 1200000.0
    assert rebuilt.key_risks_identified == ["Customer concentration"]
    assert rebuilt.confidence_score == 0.95


def test_round_trip_handles_missing_optional_values(db):
    """Runway and founding year are optional; NULLs come back as NaN from pandas."""
    extraction = ExtractionResult(
        metadata=DealMetadata(company_name="NoRunway Inc", industry_sector="SaaS"),
        metrics=FinancialMetrics(
            arr=1_000_000.0, mrr=83_333.0, net_revenue_retention=100.0, gross_margin=70.0,
            cac=3000.0, ltv=15000.0, ltv_cac_ratio=5.0, monthly_burn_rate=0.0,
            runway_months=None, ebitda=100000.0,
        ),
        confidence_score=0.8,
    )
    db.save_deal("DEAL-RT-002", extraction)
    rebuilt = record_to_extraction(db.fetch_all_deals()[0])

    assert rebuilt.metrics.runway_months is None
    assert rebuilt.metadata.founding_year is None
