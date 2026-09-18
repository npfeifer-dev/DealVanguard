import pytest
from dealvanguard.database import DatabaseManager
from dealvanguard.schemas import (
    ExtractionResult,
    DealMetadata,
    FinancialMetrics,
    CapitalStructure,
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
        capital_structure=CapitalStructure.BOOTSTRAPPED,
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