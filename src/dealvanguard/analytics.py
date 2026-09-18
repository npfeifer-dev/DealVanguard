import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from dealvanguard.schemas import FinancialMetrics

logger = logging.getLogger(__name__)

class AnalyticsSummary(BaseModel):
    """Derived SaaS KPIs and calculated risk indicators."""
    rule_of_40: float = Field(
        ...,
        description="Growth Rate (or NRR proxy) + EBITDA Margin %."
    )
    cac_payback_months: float = Field(
        ...,
        description="Months required to recover CAC based on MRR and Gross Margin."
    )
    arr_per_employee_estimate: float = Field(
        default=0.0,
        description="Estimated ARR per employee based on head count provided."
    )
    burn_multiple: float = Field(
        ...,
        description="Net Burn / Net New ARR. (efficiency ratio)."
    )
    runway_stress_tested: float = Field(
            ...,
            description="Estimated runway (months) under a 20% revenue contraction scenario."
        )
    red_flags: List[str] = Field(
            default_factory=list,
            description="Automated risk triggers based on PE underwriting thresholds."
        )

class DealAnalyticsEngine:
    """Computes advanced financial KPIs, stress test models, and automated PE underwriting flags from raw deal metrics.
    """

    @staticmethod
    def analyze_deal(metrics: FinancialMetrics) -> AnalyticsSummary:
        """Compute derived metrics and evaluated deal risk profile."""
        red_flags: List[str] = []

        gross_margin_pct = metrics.gross_margin
        if gross_margin_pct < 0.70:
            red_flags.append(
                f"Low Gross Margin ({gross_margin_pct * 100:.1f}%). SaaS target is >= 75%."
            )

        ltv_cac = metrics.ltv_cac_ratio
        if ltv_cac < 3.0:
            red_flags.append(
                f"Suboptimal LTV/CAC ratio ({ltv_cac:.2f}x). Standard target is >= 3.0x."
            )

        monthly_gross_profit = (metrics.mrr) * gross_margin_pct
        if monthly_gross_profit > 0:
            cac_payback_months = round(metrics.cac / monthly_gross_profit, 1)
        else:
            cac_payback_months = 999.0

        if cac_payback_months > 18.0:
            red_flags.append(
                f"Extended CAC Payback Period ({cac_payback_months} months). Target is <= 12 months."
            )

        nrr_pct = metrics.net_revenue_retention
        if nrr_pct < 1.0:
            red_flags.append(
                f"Net Revenue Contraction (NRR {nrr_pct * 100:.1f}%). Indicates net churn."
            )

        stressed_mrr = metrics.mrr * 0.80
        revenue_loss = metrics.mrr - stressed_mrr
        stressed_burn = metrics.monthly_burn_rate + revenue_loss

        estimated_cash_reserve = (
            (metrics.runway_months or 12.0) * metrics.monthly_burn_rate
        )

        if stressed_burn > 0:
            runway_stress_tested = round(estimated_cash_reserve / stressed_burn, 1)
        else:
            runway_stress_tested = 99.0

        if runway_stress_tested < 6.0:
            red_flags.append(
                f"Critical Runway Risk (Stress-Tested Runway {runway_stress_tested} months)."
            )

        ebitda_margin = (
            (metrics.ebitda / metrics.arr) if metrics.arr > 0 else -1.0
            )
        rule_of_40 = round(((nrr_pct - 1.0) + ebitda_margin) * 100, 1)

        if rule_of_40 < 40.0:
            red_flags.append(
                 f"Fails Rule of 40 threshold ({rule_of_40}%)."
                )

        burn_multiple = (
            round(metrics.monthly_burn_rate * 12 / metrics.arr, 2)
            if metrics.arr > 0
            else 0.0
        )

        return AnalyticsSummary(
            rule_of_40=rule_of_40,
            cac_payback_months=cac_payback_months,
            arr_per_employee_estimate=0.0,
            burn_multiple=burn_multiple,
            runway_stress_tested=runway_stress_tested,
            red_flags=red_flags
        )