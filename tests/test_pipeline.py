import sys
from pathlib import Path

src_path = str(Path(__file__).resolve().parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import logging
from datetime import datetime

from dealvanguard.schemas import (
    CapitalStructureType,
    DealMetadata,
    ExtractionResult,
    FinancialMetrics,
)
from dealvanguard.analytics import DealAnalyticsEngine
from dealvanguard.database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_pipeline_test():
    logger.info("Starting DealVanguard AI Pipeline Integration Test...")

    metadata = DealMetadata(
        company_name="ApexCloud Analytics",
        industry_sector="Enterprise B2B SaaS",
        founding_year=2021,
        capital_structure=CapitalStructureType.EQUITY,
        extraction_timestamp=datetime.now().isoformat(),
    )

    metrics = FinancialMetrics(
        arr=2_400_000.0,
        mrr=200_000.0,
        net_revenue_retention=0.92,  
        gross_margin=0.68,  
        cac=15_000.0,
        ltv=40_000.0,
        ltv_cac_ratio=2.67,  
        monthly_burn_rate=80_000.0,
        runway_months=8.0,
        total_debt=150_000.0,
        ebitda=-600_000.0,
    )

    extraction = ExtractionResult(
        metadata=metadata,
        metrics=metrics,
        confidence_score=0.91,
        key_risks_identified=[
            "High customer churn in SMB tier.",
            "Gross margin compressed by hosting infrastructure costs.",
        ],
    )

    logger.info("Executing DealAnalyticsEngine...")
    analytics_summary = DealAnalyticsEngine.analyze_deal(metrics)

    print("\n" + "=" * 50)
    print("      ANALYTICS & UNDERWRITING SUMMARY      ")
    print("=" * 50)
    print(f"Rule of 40 Score        : {analytics_summary.rule_of_40}%")
    print(f"CAC Payback Period      : {analytics_summary.cac_payback_months} months")
    print(f"Burn Multiple           : {analytics_summary.burn_multiple}x")
    print(f"Stress-Tested Runway    : {analytics_summary.runway_stress_tested} months")
    print(f"\nTriggered Red Flags ({len(analytics_summary.red_flags)}):")
    for flag in analytics_summary.red_flags:
        print(f"  [!] {flag}")
    print("=" * 50 + "\n")

    logger.info("Persisting deal payload to DuckDB...")
    db = DatabaseManager()
    deal_id = "DEAL-TEST-001"
    db.save_deal(deal_id, extraction)

    records = db.fetch_all_deals()
    logger.info("Successfully retrieved %d deal(s) from database.", len(records))

    print("Pipeline Integration Test Passed Successfully!\n")


if __name__ == "__main__":
    run_pipeline_test()