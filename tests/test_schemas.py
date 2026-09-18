import pytest
from pydantic import ValidationError
from dealvanguard.schemas import (
    CapitalStructureType,
    FinancialMetrics,
    DealMetadata,
    ExtractionResult,
)


def test_financial_metrics_valid():
    metrics = FinancialMetrics(
        arr=1000000.0,
        mrr=83333.33,
        net_revenue_retention=115.0,
        gross_margin=75.0,
        cac=5000.0,
        ltv=25000.0,
        ltv_cac_ratio=5.0,
        monthly_burn_rate=20000.0,
        runway_months=18.0,
        total_debt=500000.0,
        ebitda=150000.0,
    )
    assert metrics.arr == 1000000.0
    assert metrics.ltv_cac_ratio == 5.0
    assert metrics.total_debt == 500000.0


def test_financial_metrics_invalid_negative_arr():
    with pytest.raises(ValidationError):
        FinancialMetrics(
            arr=-1000.0,
            mrr=0.0,
            net_revenue_retention=100.0,
            gross_margin=50.0,
            cac=100.0,
            ltv=500.0,
            ltv_cac_ratio=5.0,
            monthly_burn_rate=0.0,
            ebitda=0.0,
        )


def test_financial_metrics_nrr_out_of_bounds():
    with pytest.raises(ValidationError):
        FinancialMetrics(
            arr=100000.0,
            mrr=8333.0,
            net_revenue_retention=350.0,
            gross_margin=50.0,
            cac=100.0,
            ltv=500.0,
            ltv_cac_ratio=5.0,
            monthly_burn_rate=0.0,
            ebitda=0.0,
        )


def test_financial_metrics_immutability():
    metrics = FinancialMetrics(
        arr=1000000.0,
        mrr=83333.33,
        net_revenue_retention=115.0,
        gross_margin=75.0,
        cac=5000.0,
        ltv=25000.0,
        ltv_cac_ratio=5.0,
        monthly_burn_rate=20000.0,
        ebitda=150000.0,
    )
    with pytest.raises(ValidationError):
        metrics.arr = 2000000.0


def test_financial_metrics_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        FinancialMetrics(
            arr=1000000.0,
            mrr=83333.33,
            net_revenue_retention=115.0,
            gross_margin=75.0,
            cac=5000.0,
            ltv=25000.0,
            ltv_cac_ratio=5.0,
            monthly_burn_rate=20000.0,
            ebitda=150000.0,
            unrecognized_field="unexpected_data",
        )


def test_deal_metadata_defaults():
    meta = DealMetadata(
        company_name="Acme Corp",
        industry_sector="Enterprise SaaS",
    )
    assert meta.capital_structure == CapitalStructureType.EQUITY
    assert meta.founding_year is None
    assert meta.extraction_timestamp is not None


def test_extraction_result_valid():
    meta = DealMetadata(
        company_name="Acme Corp",
        industry_sector="Enterprise SaaS",
        capital_structure=CapitalStructureType.SENIOR_DEBT,
    )
    metrics = FinancialMetrics(
        arr=1000000.0,
        mrr=83333.33,
        net_revenue_retention=115.0,
        gross_margin=75.0,
        cac=5000.0,
        ltv=25000.0,
        ltv_cac_ratio=5.0,
        monthly_burn_rate=20000.0,
        ebitda=150000.0,
    )
    result = ExtractionResult(
        metadata=meta,
        metrics=metrics,
        confidence_score=0.92,
        key_risks_identified=["High churn rate"],
    )
    assert result.confidence_score == 0.92
    assert len(result.key_risks_identified) == 1


def test_extraction_result_invalid_confidence_score():
    meta = DealMetadata(
        company_name="Acme Corp",
        industry_sector="Enterprise SaaS",
    )
    metrics = FinancialMetrics(
        arr=1000000.0,
        mrr=83333.33,
        net_revenue_retention=115.0,
        gross_margin=75.0,
        cac=5000.0,
        ltv=25000.0,
        ltv_cac_ratio=5.0,
        monthly_burn_rate=20000.0,
        ebitda=150000.0,
    )
    with pytest.raises(ValidationError):
        ExtractionResult(
            metadata=meta,
            metrics=metrics,
            confidence_score=1.5,
        )