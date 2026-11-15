from typing import Any, Dict, List, Optional, Sequence

from dealvanguard.schemas import FinancialMetrics

DEFAULT_HAIRCUTS: Sequence[float] = (0.10, 0.20, 0.30)
DSCR_HEALTHY_THRESHOLD = 1.25


class DealStressEngine:
    """Calculates financial downside scenarios and debt-service coverage."""

    def __init__(self, metrics: FinancialMetrics):
        self.metrics = metrics

    def implied_cash(self) -> Optional[float]:
        """Cash balance implied by burn x runway, or None when it cannot be inferred.

        The schema has no cash-balance field, so cash is backed out of the
        extracted burn rate and runway. With zero burn (or no runway) it is unknown.
        """
        if self.metrics.runway_months is None or self.metrics.monthly_burn_rate <= 0:
            return None
        return self.metrics.monthly_burn_rate * self.metrics.runway_months

    def run_revenue_haircut_scenario(
        self, haircut_percentages: Optional[Sequence[float]] = None
    ) -> List[Dict[str, Any]]:
        """Simulates revenue declines and the recalculated burn / runway impact."""
        haircuts = DEFAULT_HAIRCUTS if haircut_percentages is None else haircut_percentages
        base_arr = self.metrics.arr
        base_burn = self.metrics.monthly_burn_rate
        cash = self.implied_cash()

        scenarios = []
        for haircut in haircuts:
            stressed_arr = base_arr * (1.0 - haircut)
            mrr_loss = (base_arr - stressed_arr) / 12.0
            stressed_burn = base_burn + mrr_loss

            projected_runway = None
            if cash is not None and stressed_burn > 0:
                projected_runway = round(cash / stressed_burn, 1)

            scenarios.append(
                {
                    "haircut_pct": round(haircut * 100, 1),
                    "stressed_arr": round(stressed_arr, 2),
                    "monthly_burn": round(stressed_burn, 2),
                    "projected_runway_months": projected_runway,
                }
            )
        return scenarios

    def calculate_debt_service_coverage(self, interest_rate: float = 0.08) -> Dict[str, Any]:
        """Calculates Debt Service Coverage Ratio (EBITDA / annual interest).

        Interest is an assumption (default 8% of total debt); it is not extracted.
        """
        if self.metrics.total_debt == 0.0:
            return {"dscr": None, "annual_interest": 0.0, "status": "No Debt"}

        annual_interest = self.metrics.total_debt * interest_rate
        if annual_interest == 0.0:
            return {"dscr": None, "annual_interest": 0.0, "status": "Zero Interest"}

        dscr = round(self.metrics.ebitda / annual_interest, 2)
        status = "Healthy" if dscr >= DSCR_HEALTHY_THRESHOLD else "Distressed"

        return {
            "dscr": dscr,
            "annual_interest": round(annual_interest, 2),
            "status": status,
        }
