"""Shared visual language: value-driven red/amber/green colors, CSS, and Plotly styling."""
from typing import Optional, Tuple

import plotly.graph_objects as go

# Palette tuned for a dark background.
RED = "#EF4444"
AMBER = "#F59E0B"
GREEN = "#22C55E"
TEAL = "#2DD4BF"
BLUE = "#3B82F6"
SLATE = "#94A3B8"
TEXT = "#E6EDF7"
GRID = "rgba(148, 163, 184, 0.15)"

# Red -> amber -> green, used for every value-driven color in the app.
RISK_SCALE = [[0.0, RED], [0.5, AMBER], [1.0, GREEN]]
_STOPS = [(0.0, (239, 68, 68)), (0.5, (245, 158, 11)), (1.0, (34, 197, 94))]


def _hex(rgb: Tuple[float, float, float]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*[int(round(c)) for c in rgb])


def risk_color(value: float, bad: float, good: float) -> str:
    """Maps a value onto red (at `bad`) through amber to green (at `good`).

    Works in either direction: pass bad > good when lower values are better.
    """
    if good == bad:
        return GREEN
    t = (value - bad) / (good - bad)
    t = max(0.0, min(1.0, t))
    for (t0, c0), (t1, c1) in zip(_STOPS, _STOPS[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            return _hex(tuple(a + (b - a) * f for a, b in zip(c0, c1)))
    return GREEN


def risk_level(value: float, bad: float, good: float) -> str:
    """Returns 'good', 'warn' or 'bad' for a value given its red and green anchors."""
    t = (value - bad) / (good - bad) if good != bad else 1.0
    if t >= 0.75:
        return "good"
    if t >= 0.4:
        return "warn"
    return "bad"


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def badge(text: str, level: str) -> str:
    """HTML pill: level is 'good', 'warn', 'bad' or 'info'."""
    return f'<span class="dv-badge dv-{level}">{text}</span>'


def section_header(title: str, subtitle: Optional[str] = None) -> str:
    sub = f'<div class="dv-sub">{subtitle}</div>' if subtitle else ""
    return f'<div class="dv-section"><div class="dv-section-title">{title}</div>{sub}</div>'


def style_fig(fig: go.Figure, height: int = 320, legend_below: bool = True) -> go.Figure:
    """Applies the shared chart look: transparent dark canvas, soft grid, tidy legend."""
    fig.update_layout(
        template="plotly_dark",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Source Sans Pro, sans-serif", color=TEXT, size=12),
        margin=dict(l=10, r=10, t=30, b=70 if legend_below else 10),
        hoverlabel=dict(bgcolor="#0F172A", font_size=12),
    )
    if legend_below:
        fig.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=-0.30, xanchor="center", x=0.5)
        )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID)
    return fig


CSS = f"""
<style>
.dv-hero {{
    background: linear-gradient(120deg, rgba(45,212,191,0.22) 0%, rgba(59,130,246,0.20) 55%, rgba(15,23,42,0) 100%);
    border: 1px solid rgba(45,212,191,0.25);
    border-radius: 14px; padding: 18px 24px; margin-bottom: 12px;
}}
.dv-hero h1 {{ margin: 0; font-size: 2rem; font-weight: 750; color: {TEXT}; padding: 0; }}
.dv-hero p {{ margin: 4px 0 0 0; color: {SLATE}; font-size: 0.98rem; }}
.dv-section {{ margin: 22px 0 8px 0; padding-bottom: 6px;
    border-bottom: 2px solid; border-image: linear-gradient(90deg, {TEAL}, {BLUE}, rgba(0,0,0,0)) 1; }}
.dv-section-title {{ font-size: 1.35rem; font-weight: 700; color: {TEXT}; }}
.dv-sub {{ color: {SLATE}; font-size: 0.88rem; margin-top: 2px; }}
.dv-chart-title {{ font-weight: 650; font-size: 1.02rem; margin: 6px 0 0 0; color: {TEXT}; }}
.dv-note {{ color: {SLATE}; font-size: 0.8rem; font-style: italic; margin: -4px 0 6px 0; }}
div[data-testid="stMetric"] {{
    background: linear-gradient(160deg, rgba(30,41,59,0.85), rgba(15,23,42,0.85));
    border: 1px solid rgba(148,163,184,0.18); border-left: 4px solid {TEAL};
    border-radius: 10px; padding: 10px 14px;
}}
.dv-badge {{ padding: 4px 10px; border-radius: 999px; font-weight: 650; font-size: 0.82rem;
    display: inline-block; white-space: nowrap; }}
.dv-good {{ background: rgba(34,197,94,0.18); color: #86EFAC; border: 1px solid rgba(34,197,94,0.5); }}
.dv-warn {{ background: rgba(245,158,11,0.18); color: #FCD34D; border: 1px solid rgba(245,158,11,0.5); }}
.dv-bad  {{ background: rgba(239,68,68,0.18); color: #FCA5A5; border: 1px solid rgba(239,68,68,0.5); }}
.dv-info {{ background: rgba(59,130,246,0.18); color: #93C5FD; border: 1px solid rgba(59,130,246,0.5); }}
.dv-risk {{ background: rgba(245,158,11,0.10); border-left: 4px solid {AMBER};
    border-radius: 6px; padding: 10px 14px; margin: 6px 0; }}
.dv-flag {{ background: rgba(239,68,68,0.10); border-left: 4px solid {RED};
    border-radius: 6px; padding: 10px 14px; margin: 6px 0; }}
.dv-ok {{ background: rgba(34,197,94,0.10); border-left: 4px solid {GREEN};
    border-radius: 6px; padding: 10px 14px; margin: 6px 0; }}
.dv-sample {{ background: rgba(59,130,246,0.12); border: 1px dashed rgba(59,130,246,0.7);
    border-radius: 10px; padding: 10px 16px; margin-bottom: 8px; }}
</style>
"""
