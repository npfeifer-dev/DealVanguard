"""Number and date formatting helpers shared by the dashboard."""
from datetime import datetime
from typing import List, Optional, Tuple

import pandas as pd


def fmt_usd(value: float, decimals: int = 0) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.{decimals}f}"


def fmt_usd_compact(value: float) -> str:
    sign = "-" if value < 0 else ""
    v = abs(value)
    if v >= 1e9:
        return f"{sign}${v / 1e9:.2f}B"
    if v >= 1e6:
        return f"{sign}${v / 1e6:.2f}M"
    if v >= 1e3:
        return f"{sign}${v / 1e3:.0f}K"
    return f"{sign}${v:,.0f}"


def fmt_pct(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}%"


def fmt_ratio(value: float) -> str:
    return f"{value:.2f}x"


def fmt_months(value: Optional[float]) -> str:
    return "N/A" if value is None else f"{value:.1f} mo"


def parse_base_date(as_of_date: Optional[str]) -> datetime:
    """Parses the extracted as-of date, falling back to today if it is missing or unparseable."""
    if as_of_date:
        try:
            parsed = pd.to_datetime(as_of_date)
            if not pd.isna(parsed):
                return parsed.to_pydatetime()
        except (ValueError, TypeError):
            pass
    return datetime.now()


def quarter_labels(base_date: datetime) -> Tuple[List[str], List[str]]:
    """Returns (trailing five quarters ending at base_date, forward five quarters from it)."""
    base_quarter = (base_date.month - 1) // 3 + 1

    def label(offset: int) -> str:
        q_off = base_quarter + offset
        year = base_date.year + (q_off - 1) // 4
        quarter = ((q_off - 1) % 4) + 1
        return f"Q{quarter} '{str(year)[-2:]}"

    trailing = [label(-i) for i in range(4, -1, -1)]
    forward = [label(i) for i in range(5)]
    return trailing, forward
