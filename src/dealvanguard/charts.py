"""Plotly figure builders. Each returns a go.Figure; nothing here imports Streamlit.

Charts marked ILLUSTRATIVE use fixed assumptions (named constants below) because the
extraction schema does not capture quarterly history, cohorts or customer lists.
"""
from typing import Any, Dict, List, Optional

import plotly.graph_objects as go

from dealvanguard.theme import (
    AMBER, BLUE, GREEN, RED, RISK_SCALE, SLATE, TEXT,
    risk_color, rgba, style_fig,
)

# ILLUSTRATIVE assumptions (not extracted from the document).
BRIDGE_SPLIT = {"beginning": 0.80, "new_business": 0.25, "expansion": 0.05, "churn": -0.10}
PEER_LTV_CAC = 2.8
TOP_DECILE_LTV_CAC = 4.5
PEER_CAC_FACTOR = 0.85
TOP_DECILE_CAC_FACTOR = 0.70
RETENTION_DECAY = [1.0, 0.96, 0.93, 0.90, 0.88, 0.86]
CONCENTRATION_SHARES = [0.25, 0.18, 0.12, 0.08, 0.05]
TRAILING_ARR_FACTORS = [0.75, 0.82, 0.89, 0.94, 1.0]
SCENARIO_FACTORS = {
    "Downside": [1.0, 0.98, 0.95, 0.92, 0.90],
    "Base": [1.0, 1.05, 1.10, 1.16, 1.22],
    "Upside": [1.0, 1.10, 1.21, 1.33, 1.45],
}


def arr_bridge(arr_m: float) -> go.Figure:
    s = BRIDGE_SPLIT
    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "relative", "relative", "total"],
            x=["Beginning ARR", "New Business", "Expansion", "Churn", "Ending ARR"],
            y=[arr_m * s["beginning"], arr_m * s["new_business"], arr_m * s["expansion"],
               arr_m * s["churn"], arr_m],
            text=[f"${v:.2f}M" for v in (arr_m * s["beginning"], arr_m * s["new_business"],
                                           arr_m * s["expansion"], arr_m * s["churn"], arr_m)],
            textposition="outside",
            connector=dict(line=dict(color=SLATE, width=1, dash="dot")),
            decreasing=dict(marker=dict(color=RED)),
            increasing=dict(marker=dict(color=GREEN)),
            totals=dict(marker=dict(color=BLUE)),
            hovertemplate="%{x}: %{y:.2f} $M<extra></extra>",
        )
    )
    fig.update_yaxes(title="$M", range=[0, arr_m * 1.35 if arr_m else 1])
    return style_fig(fig, 330, legend_below=False)


def unit_economics(cac: float, ltv: float) -> go.Figure:
    """LTV vs CAC with shaded LTV:CAC zones (<1x red, 1x-3x amber, >=3x green)."""
    xmax = max(cac * 1.6, 1.0)
    ymax = max(ltv * 1.35, cac * TOP_DECILE_LTV_CAC * 1.1, 1.0)
    xs = [xmax * i / 40 for i in range(41)]
    zone = lambda k: [min(k * x, ymax) for x in xs]  # noqa: E731

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=[0] * len(xs), mode="lines", line=dict(width=0),
                             hoverinfo="skip", showlegend=False))
    for k, color, name in [(1.0, RED, "Below 1x"), (3.0, AMBER, "1x to 3x"), (None, GREEN, "3x and above")]:
        y = zone(k) if k else [ymax] * len(xs)
        fig.add_trace(go.Scatter(x=xs, y=y, mode="lines", line=dict(width=0),
                                 fill="tonexty", fillcolor=rgba(color, 0.14),
                                 name=name, hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=xs, y=zone(3.0), mode="lines", name="3.0x target line",
                             line=dict(dash="dash", color=TEXT, width=1.5), hoverinfo="skip"))

    ratio = ltv / cac if cac else 0.0
    fig.add_trace(go.Scatter(
        x=[cac * PEER_CAC_FACTOR, cac * TOP_DECILE_CAC_FACTOR],
        y=[cac * PEER_CAC_FACTOR * PEER_LTV_CAC, cac * TOP_DECILE_CAC_FACTOR * TOP_DECILE_LTV_CAC],
        mode="markers+text", text=["Peer (illustrative)", "Top decile (illustrative)"],
        textposition="top center", name="Illustrative benchmarks",
        marker=dict(size=12, color="rgba(0,0,0,0)", line=dict(color=SLATE, width=2)),
        hovertemplate="CAC $%{x:,.0f}<br>LTV $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[cac], y=[ltv], mode="markers+text", text=[f"Target deal {ratio:.2f}x"],
        textposition="bottom center", name="Target deal",
        marker=dict(size=24, color=risk_color(ratio, 1.0, 3.0),
                    line=dict(color="white", width=2)),
        hovertemplate="CAC $%{x:,.0f}<br>LTV $%{y:,.0f}<extra></extra>",
    ))
    fig.add_annotation(x=xmax * 0.03, y=ymax * 0.97, text="Green zone: 3x and above", showarrow=False,
                       xanchor="left", yanchor="top", font=dict(color=GREEN, size=11))
    fig.add_annotation(x=xmax * 0.97, y=xmax * 0.97 * 0.5, text="Red zone: below 1x", showarrow=False,
                       xanchor="right", font=dict(color=RED, size=11))
    fig.update_xaxes(title="CAC ($)", range=[0, xmax])
    fig.update_yaxes(title="LTV ($)", range=[0, ymax])
    return style_fig(fig, 340)


def retention_heatmap(nrr: float, quarters: List[str]) -> go.Figure:
    matrix = [[round(100.0 * d * (1.0 + i * 0.01), 1) for d in RETENTION_DECAY] for i in range(5)]
    fig = go.Figure(
        go.Heatmap(
            z=matrix, x=[f"M{i}" for i in range(6)], y=quarters,
            colorscale=RISK_SCALE, zmin=60, zmax=max(110.0, nrr),
            text=matrix, texttemplate="%{text}%", xgap=3, ygap=3,
            colorbar=dict(title="Retained %", thickness=12),
            hovertemplate="Cohort %{y}, %{x}: %{z}%<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed")
    return style_fig(fig, 330, legend_below=False)


def concentration_pareto(arr: float) -> go.Figure:
    revs = [arr * p for p in CONCENTRATION_SHARES]
    total = arr or (sum(revs) or 1.0)
    cum, running = [], 0.0
    for r in revs:
        running += r
        cum.append(round(running / total * 100, 1))
    ranks = [f"Cust {i}" for i in range(1, len(revs) + 1)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=ranks, y=revs, name="ARR contribution ($)",
        marker=dict(color=[p * 100 for p in CONCENTRATION_SHARES], colorscale="Tealgrn",
                    line=dict(color="rgba(255,255,255,0.25)", width=1)),
        hovertemplate="%{x}: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=ranks, y=cum, name="Cumulative % of ARR", yaxis="y2", mode="lines+markers+text",
        text=[f"{c:.0f}%" for c in cum], textposition="top center",
        line=dict(color=AMBER, width=3), marker=dict(size=9, color=AMBER),
    ))
    fig.update_layout(
        yaxis=dict(title="ARR ($)"),
        yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 105],
                    tickvals=[0, 25, 50, 75, 100], showgrid=False),
    )
    return style_fig(fig, 330)


def arr_growth(quarters: List[str], arr_m: float) -> go.Figure:
    vals = [arr_m * f for f in TRAILING_ARR_FACTORS]
    qoq = [None] + [(b / a - 1) * 100 if a else 0.0 for a, b in zip(vals, vals[1:])]
    colors = [SLATE] + [risk_color(g, 0.0, 8.0) for g in qoq[1:]]
    text = [f"${v:.2f}M" + ("" if g is None else f"<br>{g:+.1f}% QoQ") for v, g in zip(vals, qoq)]
    fig = go.Figure(go.Bar(
        x=quarters, y=vals, text=text, textposition="outside",
        marker=dict(color=colors, line=dict(color="rgba(255,255,255,0.25)", width=1)),
        hovertemplate="%{x}: $%{y:.2f}M<extra></extra>",
    ))
    fig.update_xaxes(type="category")
    fig.update_yaxes(title="ARR ($M)", range=[0, max(vals) * 1.3 if vals else 1])
    return style_fig(fig, 320, legend_below=False)


def scenario_trajectory(quarters: List[str], arr_m: float) -> go.Figure:
    s = {k: [arr_m * f for f in v] for k, v in SCENARIO_FACTORS.items()}
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=quarters, y=s["Upside"], mode="lines", line=dict(width=0),
                             hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=quarters, y=s["Downside"], mode="lines", line=dict(width=0),
                             fill="tonexty", fillcolor="rgba(148,163,184,0.15)",
                             name="Scenario range", hoverinfo="skip"))
    for name, color in [("Downside", RED), ("Base", BLUE), ("Upside", GREEN)]:
        fig.add_trace(go.Scatter(
            x=quarters, y=s[name], mode="lines+markers", name=f"{name} case",
            line=dict(color=color, width=3), marker=dict(size=8),
            hovertemplate="%{x}: $%{y:.2f}M<extra></extra>",
        ))
        fig.add_annotation(x=quarters[-1], y=s[name][-1], text=f"${s[name][-1]:.2f}M",
                           showarrow=False, xanchor="left", xshift=8, font=dict(color=color))
    fig.update_xaxes(type="category")
    fig.update_yaxes(title="ARR ($M)")
    fig.update_layout(margin=dict(r=60))
    return style_fig(fig, 320)


def cash_drawdown(monthly_burn: float, runway_months: float, labels: List[str]) -> Optional[go.Figure]:
    """Implied cash balance (burn x runway) month by month. None when burn is zero."""
    if monthly_burn <= 0 or runway_months <= 0:
        return None
    start = monthly_burn * runway_months / 1e6
    burn_m = monthly_burn / 1e6
    cash = [max(0.0, start - burn_m * i) for i in range(len(labels))]
    left = [c / burn_m for c in cash]
    fig = go.Figure(go.Bar(
        x=labels, y=cash, customdata=left,
        marker=dict(color=[risk_color(m, 0.0, 12.0) for m in left],
                    line=dict(color="rgba(255,255,255,0.25)", width=1)),
        text=[f"${c:.2f}M" for c in cash], textposition="outside",
        hovertemplate="%{x}: $%{y:.2f}M (%{customdata:.1f} months of cash left)<extra></extra>",
    ))
    fig.add_hline(y=burn_m * 6, line_dash="dot", line_color=AMBER,
                  annotation_text="6 months of burn", annotation_font_color=AMBER)
    fig.update_xaxes(type="category")
    fig.update_yaxes(title="Cash ($M)", range=[0, start * 1.25])
    return style_fig(fig, 320, legend_below=False)


def stress_runway(base_runway: Optional[float], scenarios: List[Dict[str, Any]]) -> Optional[go.Figure]:
    """Runway after revenue haircuts. Bars shift from green to red as runway shrinks."""
    rows = [("Base case", base_runway)] + [
        (f"-{s['haircut_pct']:.0f}% revenue", s["projected_runway_months"]) for s in scenarios
    ]
    rows = [(n, v) for n, v in rows if v is not None]
    if not rows:
        return None
    names, vals = zip(*rows)
    fig = go.Figure(go.Bar(
        x=list(names), y=list(vals),
        marker=dict(color=[risk_color(v, 0.0, 12.0) for v in vals],
                    line=dict(color="rgba(255,255,255,0.25)", width=1)),
        text=[f"{v:.1f} mo" for v in vals], textposition="outside",
        hovertemplate="%{x}: %{y:.1f} months<extra></extra>",
    ))
    fig.add_hline(y=6, line_dash="dot", line_color=AMBER,
                  annotation_text="6-month minimum", annotation_position="top right",
                  annotation_font_color=AMBER)
    fig.update_yaxes(title="Runway (months)", range=[0, max(max(vals), 6) * 1.3])
    return style_fig(fig, 300, legend_below=False)


def dscr_gauge(dscr: Optional[float]) -> Optional[go.Figure]:
    if dscr is None:
        return None
    lo, hi = -2.0, 3.0
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=dscr, number=dict(suffix="x", font=dict(color=TEXT)),
        title=dict(text="Debt Service Coverage (assumes 8% interest)", font=dict(size=14)),
        gauge=dict(
            axis=dict(range=[lo, hi], tickcolor=SLATE),
            bar=dict(color="white", thickness=0.25),
            steps=[dict(range=[lo, 0], color=rgba(RED, 0.75)),
                   dict(range=[0, 1.25], color=rgba(AMBER, 0.75)),
                   dict(range=[1.25, hi], color=rgba(GREEN, 0.75))],
            threshold=dict(line=dict(color="white", width=3), thickness=0.8, value=1.25),
        ),
    ))
    return style_fig(fig, 260, legend_below=False)
