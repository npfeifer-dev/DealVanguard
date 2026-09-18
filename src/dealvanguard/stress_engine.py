from typing import Dict, List, Any
from dealvanguard.schemas import FinancialMetrics

class DealStressEngine:
    """Calculates financial downside scenarios and LBO sensitivity metrics."""

    def __init__(self, metrics: FinancialMetrics):
        self.metrics = metrics

    def run_revenue_haircut_scenario(self, haircut_percentages: List[float] = [0.10, 0.20, 0.30]) -> List[Dict[str, Any]]:
        """Simulates revenue declines and recalculated runway / burn impact."""
        scenarios = []
        base_arr = self.metrics.arr
        base_burn = self.metrics.monthly_burn_rate

        for haircut in haircut_percentages:
            stressed_arr = base_arr * (1.0 - haircut)
            mrr_loss = (base_arr - stressed_arr) / 12.0
            stressed_burn = base_burn + mrr_loss
            
            projected_runway = None
            if stressed_burn > 0 and self.metrics.runway_months is not None:
                implied_cash = base_burn * self.metrics.runway_months
                projected_runway = round(implied_cash / stressed_burn, 1)

            scenarios.append({
                "haircut_pct": round(haircut * 100, 1),
                "stressed_arr": round(stressed_arr, 2),
                "monthly_burn": round(stressed_burn, 2),
                "projected_runway_months": projected_runway,
            })
        return scenarios

    def calculate_debt_service_coverage(self, interest_rate: float = 0.08) -> Dict[str, Any]:
        """Calculates Debt Service Coverage Ratio (DSCR) under current EBITDA."""
        if self.metrics.total_debt == 0.0:
            return {"dscr": None, "annual_interest": 0.0, "status": "No Debt"}

        annual_interest = self.metrics.total_debt * interest_rate
        if annual_interest == 0.0:
            return {"dscr": None, "annual_interest": 0.0, "status": "Zero Interest"}

        dscr = round(self.metrics.ebitda / annual_interest, 2)
        status = "Healthy" if dscr >= 1.25 else "Distressed"

        return {
            "dscr": dscr,
            "annual_interest": round(annual_interest, 2),
            "status": status,
        }