from typing import List, Optional

from pydantic import BaseModel, Field

from dealvanguard.schemas import FinancialMetrics
from dealvanguard.stress_engine import DSCR_HEALTHY_THRESHOLD, DealStressEngine

# Underwriting thresholds. All percentages are on the same 0-100 scale as the schema.
MIN_GROSS_MARGIN_PCT = 70.0
MIN_LTV_CAC = 3.0
MIN_NRR_PCT = 100.0
MIN_STRESSED_RUNWAY_MONTHS = 6.0
MIN_RULE_OF_40 = 40.0
STRESS_HAIRCUT = 0.20


class AnalyticsSummary(BaseModel):
    """Derived KPIs and automated underwriting flags."""

    rule_of_40: float = Field(
        ...,
        description="(NRR - 100) as a growth proxy plus EBITDA margin, in percentage points.",
    )
    annual_burn_to_arr: float = Field(
        ...,
        description="Annualized burn divided by ARR (a simple burn-efficiency ratio).",
    )
    runway_stress_tested: Optional[float] = Field(
        default=None,
        description="Runway in months after a 20% revenue haircut, or None if cash cannot be inferred.",
    )
    red_flags: List[str] = Field(
        default_factory=list,
        description="Automated risk triggers based on PE underwriting thresholds.",
    )


class DealAnalyticsEngine:
    """Computes derived KPIs and automated underwriting flags from extracted metrics."""

    @staticmethod
    def analyze_deal(metrics: FinancialMetrics) -> AnalyticsSummary:
        red_flags: List[str] = []

        if metrics.gross_margin < MIN_GROSS_MARGIN_PCT:
            red_flags.append(
                f"Low gross margin ({metrics.gross_margin:.1f}%). Target is at least {MIN_GROSS_MARGIN_PCT:.0f}%."
            )

        if metrics.ltv_cac_ratio < MIN_LTV_CAC:
            red_flags.append(
                f"Suboptimal LTV/CAC ratio ({metrics.ltv_cac_ratio:.2f}x). Target is at least {MIN_LTV_CAC:.1f}x."
            )

        if metrics.net_revenue_retention < MIN_NRR_PCT:
            red_flags.append(
                f"Net revenue contraction (NRR {metrics.net_revenue_retention:.1f}%). Indicates net churn."
            )

        engine = DealStressEngine(metrics)
        stressed = engine.run_revenue_haircut_scenario([STRESS_HAIRCUT])[0]
        runway_stress_tested = stressed["projected_runway_months"]
        if runway_stress_tested is not None and runway_stress_tested < MIN_STRESSED_RUNWAY_MONTHS:
            red_flags.append(
                f"Critical runway risk: {runway_stress_tested} months after a {STRESS_HAIRCUT:.0%} revenue haircut."
            )

        ebitda_margin_pct = (metrics.ebitda / metrics.arr * 100.0) if metrics.arr > 0 else -100.0
        rule_of_40 = round((metrics.net_revenue_retention - 100.0) + ebitda_margin_pct, 1)
        if rule_of_40 < MIN_RULE_OF_40:
            red_flags.append(
                f"Fails Rule of 40 ({rule_of_40}). Uses NRR minus 100 as a growth proxy."
            )

        dscr = engine.calculate_debt_service_coverage()
        if dscr["dscr"] is not None and dscr["dscr"] < DSCR_HEALTHY_THRESHOLD:
            red_flags.append(
                f"Weak debt service coverage (DSCR {dscr['dscr']:.2f}x at an assumed 8% interest rate)."
            )

        annual_burn_to_arr = (
            round(metrics.monthly_burn_rate * 12 / metrics.arr, 2) if metrics.arr > 0 else 0.0
        )

        return AnalyticsSummary(
            rule_of_40=rule_of_40,
            annual_burn_to_arr=annual_burn_to_arr,
            runway_stress_tested=runway_stress_tested,
            red_flags=red_flags,
        )
