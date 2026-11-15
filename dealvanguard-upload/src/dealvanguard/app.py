import os
import sys
import uuid
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Lets `streamlit run src/dealvanguard/app.py` work without `pip install -e .`.
src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
load_dotenv(src_dir.parent / ".env")  # optional local .env with ANTHROPIC_API_KEY

from dealvanguard import charts
from dealvanguard.ai_extractor import DEFAULT_MODEL, SUPPORTED_MODELS, DealExtractor
from dealvanguard.analytics import (
    MIN_GROSS_MARGIN_PCT,
    MIN_LTV_CAC,
    MIN_NRR_PCT,
    DealAnalyticsEngine,
)
from dealvanguard.database import DatabaseManager, record_to_extraction
from dealvanguard.formatting import (
    fmt_months,
    fmt_pct,
    fmt_ratio,
    fmt_usd,
    fmt_usd_compact,
    parse_base_date,
    quarter_labels,
)
from dealvanguard.samples import load_sample_deal, load_sample_memo
from dealvanguard.schemas import ExtractionResult
from dealvanguard.stress_engine import DealStressEngine
from dealvanguard.theme import (
    CSS,
    badge,
    risk_color,
    risk_level,
    section_header,
)

st.set_page_config(
    page_title="DealVanguard AI | Deal Diligence Platform",
    page_icon="📈",
    layout="wide",
)
st.markdown(CSS, unsafe_allow_html=True)

PLACEHOLDER = "-- Select a Saved Deal --"
RUNWAY_TARGET_MONTHS = 12.0
CONFIDENCE_TARGET = 0.90


@st.cache_resource
def get_database() -> DatabaseManager:
    return DatabaseManager()


db = get_database()


# ---------------------------------------------------------------------------
# Session-state callbacks (run before the script reruns, so they always win)
# ---------------------------------------------------------------------------
def set_active_result(result: ExtractionResult, source: str, label: Optional[str] = None) -> None:
    st.session_state["extraction_result"] = result
    st.session_state["result_source"] = source
    st.session_state["result_label"] = label or result.metadata.company_name


def on_load_sample() -> None:
    set_active_result(load_sample_deal(), "sample")
    st.session_state["saved_deal_select"] = PLACEHOLDER


def on_load_saved() -> None:
    label = st.session_state.get("saved_deal_select", PLACEHOLDER)
    if label == PLACEHOLDER:
        return
    record = st.session_state.get("_deal_map", {}).get(label)
    try:
        set_active_result(record_to_extraction(record), "saved", label)
    except Exception as exc:  # shown in the UI on the next run
        st.session_state["load_error"] = f"Failed to load saved deal: {exc}"


def on_clear() -> None:
    for key in ("extraction_result", "result_source", "result_label"):
        st.session_state.pop(key, None)
    st.session_state["saved_deal_select"] = PLACEHOLDER


def on_use_sample_memo() -> None:
    st.session_state["source_option"] = "Text Area"
    st.session_state["document_text"] = load_sample_memo()


# ---------------------------------------------------------------------------
# Small rendering helpers
# ---------------------------------------------------------------------------
def chart_title(title: str, note: Optional[str] = None) -> None:
    st.markdown(f'<div class="dv-chart-title">{title}</div>', unsafe_allow_html=True)
    if note:
        st.markdown(f'<div class="dv-note">{note}</div>', unsafe_allow_html=True)


def gradient_cell(value: Any, bad: float, good: float) -> str:
    """CSS for a table cell whose background follows the value (red to amber to green)."""
    if value is None or pd.isna(value):
        return ""
    return f"background-color: {risk_color(float(value), bad, good)}33; color: {risk_color(float(value), bad, good)}; font-weight: 600"


def style_portfolio(df: pd.DataFrame):
    ranges = {
        "net_revenue_retention": (85.0, 115.0),
        "gross_margin": (50.0, 80.0),
        "ltv_cac_ratio": (1.0, 3.0),
        "runway_months": (3.0, 12.0),
        "confidence_score": (0.6, 0.95),
        "ebitda": (-1_000_000.0, 1_000_000.0),
    }
    styler = df.style
    for col, (bad, good) in ranges.items():
        if col in df.columns:
            styler = styler.map(lambda v, b=bad, g=good: gradient_cell(v, b, g), subset=[col])
    usd = fmt_usd
    formats = {
        "arr": usd, "mrr": usd, "cac": usd, "ltv": usd,
        "monthly_burn_rate": usd, "total_debt": usd, "ebitda": usd,
        "net_revenue_retention": "{:.1f}%", "gross_margin": "{:.1f}%",
        "ltv_cac_ratio": "{:.2f}x", "runway_months": "{:.1f}", "confidence_score": "{:.0%}",
    }
    return styler.format({k: v for k, v in formats.items() if k in df.columns}, na_rep="N/A")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("⚙️ Configuration")
env_api_key = os.getenv("ANTHROPIC_API_KEY", "")
user_api_key = st.sidebar.text_input(
    "Anthropic API Key",
    value=env_api_key,
    type="password",
    help="Needed only for 'Run AI Extraction'. It is held only for this session and is "
    "never saved by the app. The sample deal works without one.",
)
api_key = user_api_key.strip() or env_api_key

st.sidebar.divider()
st.sidebar.subheader("🤖 AI Settings")
model_choice = st.sidebar.selectbox(
    "Claude Model",
    SUPPORTED_MODELS,
    index=SUPPORTED_MODELS.index(DEFAULT_MODEL),
    help="These models support the forced tool call the extractor uses.",
)
enforce_thresholds = st.sidebar.toggle(
    "Highlight Outlier Metrics",
    value=True,
    help="Shows automated underwriting flags (margin, LTV/CAC, NRR, runway, Rule of 40, DSCR).",
)
st.sidebar.divider()
st.sidebar.caption(
    "No API key? Use **Load sample deal** on the first tab to see the full dashboard "
    "with fictional data."
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="dv-hero">
      <h1>DealVanguard AI: Enterprise Deal Diligence</h1>
      <p>AI-powered financial extraction and risk analysis for deal execution</p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_extract, tab_deals = st.tabs(["⚡ AI Deal Ingestion", "📊 Portfolio Deals"])
existing_deals = db.fetch_all_deals()

# ---------------------------------------------------------------------------
# Tab 1: ingestion
# ---------------------------------------------------------------------------
with tab_extract:
    st.markdown(
        section_header(
            "Deal Data Ingestion & Analytics",
            "Start with the sample deal, reopen a saved deal, or extract a new one from a document.",
        ),
        unsafe_allow_html=True,
    )

    if "load_error" in st.session_state:
        st.error(st.session_state.pop("load_error"))

    c_mode1, c_mode2 = st.columns(2)

    with c_mode1:
        st.subheader("1. Open a Deal")
        st.button(
            "▶ Load sample deal (no API key needed)",
            type="primary",
            on_click=on_load_sample,
            help="Loads a fictional example company so you can explore the whole dashboard.",
        )
        st.caption("Fictional example data. Nothing is saved to the database.")

        if existing_deals:
            deal_map = {f"{d.get('company_name', 'Unknown')} ({d.get('deal_id', 'N/A')})": d for d in existing_deals}
            st.session_state["_deal_map"] = deal_map
            st.selectbox(
                "Or open a previously saved deal:",
                options=[PLACEHOLDER] + list(deal_map.keys()),
                key="saved_deal_select",
                on_change=on_load_saved,
            )
        else:
            st.info(
                "No saved deals yet. Deals you extract with your own API key are saved here "
                "(on Streamlit Community Cloud this storage resets when the app restarts)."
            )

    with c_mode2:
        st.subheader("2. Extract a New Deal from a Document")
        source_option = st.radio(
            "Input Source", ["Text Area", "File Upload"], horizontal=True, key="source_option"
        )
        document_text = ""

        if source_option == "Text Area":
            document_text = st.text_area(
                "Paste CIM / Pitch Deck Content",
                height=170,
                key="document_text",
                placeholder="Paste a deal memorandum, CIM or pitch deck text here...",
            )
        else:
            uploaded_file = st.file_uploader("Upload Document (.txt, .md)", type=["txt", "md"])
            if uploaded_file is not None:
                document_text = uploaded_file.read().decode("utf-8", errors="replace")

        b1, b2 = st.columns([1, 1])
        run_btn = b1.button(
            "Run AI Extraction",
            type="primary",
            disabled=not bool(document_text.strip()),
            help="Sends the text to Claude with your API key and saves the validated result.",
        )
        b2.button(
            "Use sample memo text",
            on_click=on_use_sample_memo,
            help="Fills the text box with a fictional memo. Extraction still needs your API key.",
        )

        if run_btn:
            if not api_key:
                st.error(
                    "Add your Anthropic API key in the sidebar to run extraction. "
                    "To explore without a key, click 'Load sample deal'."
                )
            else:
                extracted: Optional[ExtractionResult] = None
                with st.spinner("Analyzing deal document with Claude..."):
                    try:
                        extractor = DealExtractor(api_key=api_key, model=model_choice)
                        extracted = extractor.extract_from_text(document_text)
                        deal_id = f"DEAL-{uuid.uuid4().hex[:8].upper()}"
                        db.save_deal(deal_id=deal_id, extraction=extracted)
                        set_active_result(
                            extracted, "extracted", f"{extracted.metadata.company_name} ({deal_id})"
                        )
                    except Exception as exc:
                        extracted = None
                        st.error(f"Extraction failed: {exc}")
                if extracted is not None:
                    st.rerun()

    st.divider()

    result: Optional[ExtractionResult] = st.session_state.get("extraction_result")

    if result is None:
        st.info(
            "**No deal is open yet.** Click **Load sample deal** to see the full dashboard "
            "right away, or paste a document and run extraction with your own Anthropic API key."
        )
    else:
        source = st.session_state.get("result_source", "saved")
        head_l, head_r = st.columns([5, 1])
        if source == "sample":
            head_l.markdown(
                '<div class="dv-sample"><b>SAMPLE DATA.</b> The company, numbers and risks below are '
                "fictional and exist only to demonstrate the dashboard.</div>",
                unsafe_allow_html=True,
            )
        else:
            head_l.success(f"Active dashboard: {st.session_state.get('result_label', result.metadata.company_name)}")
        head_r.button("Clear dashboard", on_click=on_clear)

        m = result.metrics
        meta = result.metadata
        base_date = parse_base_date(meta.as_of_date)
        trailing_quarters, forward_quarters = quarter_labels(base_date)
        monthly_labels = [d.strftime("%b '%y") for d in pd.date_range(start=base_date, periods=6, freq="MS")]
        arr_m = m.arr / 1e6
        ebitda_margin = (m.ebitda / m.arr * 100.0) if m.arr else 0.0
        analytics = DealAnalyticsEngine.analyze_deal(m)
        stress = DealStressEngine(m)
        scenarios = stress.run_revenue_haircut_scenario()
        dscr = stress.calculate_debt_service_coverage()

        # ---- KPI cards -----------------------------------------------------
        st.markdown(
            section_header(
                f"Deal Snapshot: {meta.company_name}",
                f"{meta.industry_sector}  |  {meta.capital_structure.value}"
                + (f"  |  as of {meta.as_of_date}" if meta.as_of_date else ""),
            ),
            unsafe_allow_html=True,
        )
        row1 = st.columns(4)
        row2 = st.columns(4)
        row1[0].metric("ARR", fmt_usd_compact(m.arr), help=fmt_usd(m.arr, 2))
        row1[1].metric("MRR", fmt_usd_compact(m.mrr), help=fmt_usd(m.mrr, 2))
        row1[2].metric(
            "Gross Margin",
            fmt_pct(m.gross_margin),
            f"{m.gross_margin - MIN_GROSS_MARGIN_PCT:+.1f} pts vs {MIN_GROSS_MARGIN_PCT:.0f}% target",
        )
        row1[3].metric(
            "LTV / CAC",
            fmt_ratio(m.ltv_cac_ratio),
            f"{m.ltv_cac_ratio - MIN_LTV_CAC:+.2f}x vs {MIN_LTV_CAC:.1f}x target",
        )
        row2[0].metric(
            "NRR",
            fmt_pct(m.net_revenue_retention),
            f"{m.net_revenue_retention - MIN_NRR_PCT:+.1f} pts vs {MIN_NRR_PCT:.0f}%",
        )
        row2[1].metric("EBITDA", fmt_usd_compact(m.ebitda), f"{ebitda_margin:+.0f}% margin", help=fmt_usd(m.ebitda, 2))
        if m.runway_months is not None:
            row2[2].metric(
                "Runway",
                fmt_months(m.runway_months),
                f"{m.runway_months - RUNWAY_TARGET_MONTHS:+.1f} mo vs {RUNWAY_TARGET_MONTHS:.0f} mo",
            )
        else:
            row2[2].metric("Runway", "N/A")
        row2[3].metric(
            "Confidence",
            f"{result.confidence_score * 100:.0f}%",
            f"{(result.confidence_score - CONFIDENCE_TARGET) * 100:+.0f} pts vs {CONFIDENCE_TARGET:.0%}",
        )

        with st.expander("Detailed Metric Breakdown", expanded=True):
            d1, d2, d3 = st.columns(3)
            gm_level = risk_level(m.gross_margin, 50.0, 80.0)
            lc_level = risk_level(m.ltv_cac_ratio, 1.0, 3.0)
            nrr_level = risk_level(m.net_revenue_retention, 85.0, 115.0)
            d1.markdown(f"**MRR:** {fmt_usd(m.mrr, 2)}")
            d1.markdown(f"**Gross Margin:** {badge(fmt_pct(m.gross_margin), gm_level)}", unsafe_allow_html=True)
            d1.markdown(f"**Total Debt:** {fmt_usd(m.total_debt, 2)}")
            d2.markdown(f"**CAC:** {fmt_usd(m.cac, 2)}")
            d2.markdown(f"**LTV:** {fmt_usd(m.ltv, 2)}")
            d2.markdown(f"**LTV:CAC Ratio:** {badge(fmt_ratio(m.ltv_cac_ratio), lc_level)}", unsafe_allow_html=True)
            d3.markdown(f"**Monthly Burn:** {fmt_usd(m.monthly_burn_rate, 2)}")
            if m.runway_months is not None:
                rw_level = risk_level(m.runway_months, 3.0, 12.0)
                d3.markdown(f"**Runway:** {badge(fmt_months(m.runway_months), rw_level)}", unsafe_allow_html=True)
            else:
                d3.markdown("**Runway:** N/A")
            d3.markdown(f"**NRR:** {badge(fmt_pct(m.net_revenue_retention), nrr_level)}", unsafe_allow_html=True)
            d3.markdown(f"**Capital Structure:** {meta.capital_structure.value}")

        # ---- Analytics charts ------------------------------------------------
        st.markdown(
            section_header(
                "📈 Deal Intelligence & Cohort Analytics",
                "Charts tagged ILLUSTRATIVE use fixed assumptions because the extraction schema "
                "does not capture quarterly history, cohorts or customer lists.",
            ),
            unsafe_allow_html=True,
        )

        ch1, ch2 = st.columns(2)
        with ch1:
            chart_title("1. ARR Bridge (Waterfall)", "ILLUSTRATIVE: split is assumed (80% beginning, +25% new, +5% expansion, -10% churn).")
            st.plotly_chart(charts.arr_bridge(arr_m), key="chart_bridge")
        with ch2:
            chart_title(
                "2. Customer Economics (LTV vs. CAC)",
                "Target deal is extracted data. Shaded zones are the 1x and 3x LTV:CAC lines. "
                "Peer and top-decile points are ILLUSTRATIVE.",
            )
            st.plotly_chart(charts.unit_economics(m.cac, m.ltv), key="chart_unit")

        ch3, ch4 = st.columns(2)
        with ch3:
            chart_title("3. Net Retention Heatmap (%)", "ILLUSTRATIVE: fixed decay curve, not real cohort data.")
            st.plotly_chart(
                charts.retention_heatmap(m.net_revenue_retention, trailing_quarters), key="chart_heat"
            )
        with ch4:
            chart_title("4. Revenue Concentration Pareto", "ILLUSTRATIVE: assumed top-5 customer shares (25%, 18%, 12%, 8%, 5% of ARR).")
            st.plotly_chart(charts.concentration_pareto(m.arr), key="chart_pareto")

        chart_title("Quarterly ARR Growth Trend", "ILLUSTRATIVE: back-cast from current ARR with fixed factors. Bar color follows QoQ growth.")
        st.plotly_chart(charts.arr_growth(trailing_quarters, arr_m), key="chart_growth")

        sc1, sc2 = st.columns(2)
        with sc1:
            chart_title("Scenario Trajectory ($M)", "ILLUSTRATIVE: fixed growth multipliers for each case.")
            st.plotly_chart(charts.scenario_trajectory(forward_quarters, arr_m), key="chart_scen")
        with sc2:
            chart_title("Cash Runway Drawdown ($M)", "Derived: implied cash = monthly burn x runway. Bars shift from green to red as cash nears zero.")
            fig_cash = charts.cash_drawdown(m.monthly_burn_rate, m.runway_months or 0.0, monthly_labels)
            if fig_cash is None:
                st.info("Needs a monthly burn rate and runway above zero to estimate cash. None reported for this deal.")
            else:
                st.plotly_chart(fig_cash, key="chart_cash")

        # ---- Stress tests ----------------------------------------------------
        st.markdown(
            section_header(
                "🧪 Downside Stress Tests",
                "Calculated from the extracted metrics by DealStressEngine.",
            ),
            unsafe_allow_html=True,
        )
        s1, s2 = st.columns([3, 2])
        with s1:
            chart_title("Runway After Revenue Haircuts", "Revenue loss is added to monthly burn; cash is implied from burn x runway.")
            fig_stress = charts.stress_runway(m.runway_months, scenarios)
            if fig_stress is None:
                st.info("Runway stress needs a non-zero burn rate and a reported runway.")
            else:
                st.plotly_chart(fig_stress, key="chart_stress")
        with s2:
            fig_dscr = charts.dscr_gauge(dscr["dscr"])
            if fig_dscr is None:
                st.markdown('<div class="dv-chart-title">Debt Service Coverage</div>', unsafe_allow_html=True)
                st.info(f"DSCR: {dscr['status']}.")
            else:
                st.plotly_chart(fig_dscr, key="chart_dscr")
                st.markdown(
                    f"{badge(dscr['status'], 'good' if dscr['status'] == 'Healthy' else 'bad')} "
                    f"Annual interest at 8%: {fmt_usd(dscr['annual_interest'])}",
                    unsafe_allow_html=True,
                )
        scen_df = pd.DataFrame(
            [
                {
                    "Revenue haircut": f"-{s['haircut_pct']:.0f}%",
                    "Stressed ARR": s["stressed_arr"],
                    "Monthly burn": s["monthly_burn"],
                    "Runway (months)": s["projected_runway_months"],
                }
                for s in scenarios
            ]
        )
        st.dataframe(
            scen_df.style.map(lambda v: gradient_cell(v, 0.0, 12.0), subset=["Runway (months)"]).format(
                {"Stressed ARR": fmt_usd, "Monthly burn": fmt_usd, "Runway (months)": "{:.1f}"},
                na_rep="N/A",
            ),
            hide_index=True,
        )

        # ---- Diligence findings -----------------------------------------------
        if enforce_thresholds:
            st.markdown(
                section_header("🚦 Persistent Diligence Findings", "Automated underwriting checks from DealAnalyticsEngine."),
                unsafe_allow_html=True,
            )
            a1, a2, a3 = st.columns(3)
            a1.metric("Rule of 40 (NRR proxy)", f"{analytics.rule_of_40:.1f}", f"{analytics.rule_of_40 - 40:+.1f} vs 40")
            a2.metric("Annual burn / ARR", f"{analytics.annual_burn_to_arr:.2f}x")
            a3.metric(
                "Runway after 20% revenue haircut",
                fmt_months(analytics.runway_stress_tested),
                None if analytics.runway_stress_tested is None else f"{analytics.runway_stress_tested - 6:+.1f} mo vs 6 mo",
            )
            for flag in analytics.red_flags:
                st.markdown(f'<div class="dv-flag">🔴 {flag}</div>', unsafe_allow_html=True)
            if not analytics.red_flags:
                st.markdown('<div class="dv-ok">🟢 No underwriting red flags triggered.</div>', unsafe_allow_html=True)
            if m.gross_margin >= MIN_GROSS_MARGIN_PCT:
                st.markdown('<div class="dv-ok">🟢 <b>Healthy gross margin:</b> unit economics meet standard software benchmarks.</div>', unsafe_allow_html=True)
            if m.net_revenue_retention >= 105.0:
                st.markdown(
                    f'<div class="dv-ok">🟢 <b>Strong expansion:</b> NRR of {m.net_revenue_retention:.1f}% indicates positive net account growth.</div>',
                    unsafe_allow_html=True,
                )

        # ---- Sanity checks table -----------------------------------------------
        st.markdown(
            section_header(
                "🔎 AI Extraction Confidence & Sanity Checks",
                "Claude returns one confidence score for the whole extraction (there is no per-field "
                "scoring). Status is a rule-based cross-check done in this app.",
            ),
            unsafe_allow_html=True,
        )
        arr_gap = abs(m.mrr * 12 - m.arr) / m.arr * 100 if m.arr else 0.0
        implied_ratio = m.ltv / m.cac if m.cac else 0.0
        ratio_gap = abs(implied_ratio - m.ltv_cac_ratio) / m.ltv_cac_ratio * 100 if m.ltv_cac_ratio else 0.0
        debt_to_arr = m.total_debt / m.arr if m.arr else 0.0
        checks = [
            ("ARR", fmt_usd(m.arr, 2), "OK" if arr_gap <= 2.0 else "Review",
             "Matches MRR x 12" if arr_gap <= 2.0 else f"Differs from MRR x 12 by {arr_gap:.1f}%"),
            ("NRR", fmt_pct(m.net_revenue_retention), "OK" if 50.0 <= m.net_revenue_retention <= 150.0 else "Review",
             "Within a typical 50-150% range" if 50.0 <= m.net_revenue_retention <= 150.0 else "Unusual value, verify in source"),
            ("LTV:CAC", fmt_ratio(m.ltv_cac_ratio), "OK" if ratio_gap <= 5.0 else "Review",
             "Matches LTV / CAC" if ratio_gap <= 5.0 else f"LTV / CAC is {implied_ratio:.2f}x"),
            ("EBITDA", fmt_usd(m.ebitda, 2), "OK" if m.ebitda >= 0 else "Review",
             "Positive EBITDA" if m.ebitda >= 0 else f"Negative EBITDA ({ebitda_margin:.0f}% margin)"),
            ("Total Debt", fmt_usd(m.total_debt, 2), "OK" if debt_to_arr <= 1.0 else "Review",
             "No debt reported" if m.total_debt == 0 else f"Debt is {debt_to_arr:.2f}x ARR"),
        ]
        audit_df = pd.DataFrame(
            [
                {"Metric": n, "Extracted Value": v, "Overall Confidence": result.confidence_score, "Status": s, "Check": c}
                for n, v, s, c in checks
            ]
        )
        st.dataframe(
            audit_df.style.map(lambda v: gradient_cell(v, 0.6, 0.95), subset=["Overall Confidence"])
            .map(
                lambda v: "background-color: #22C55E33; color: #86EFAC; font-weight: 600"
                if v == "OK"
                else "background-color: #F59E0B33; color: #FCD34D; font-weight: 600",
                subset=["Status"],
            )
            .format({"Overall Confidence": "{:.0%}"}),
            hide_index=True,
        )

        if result.key_risks_identified:
            st.markdown(section_header("⚠️ Identified Deal Risks"), unsafe_allow_html=True)
            for risk in result.key_risks_identified:
                st.markdown(f'<div class="dv-risk">⚠️ {risk}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tab 2: portfolio
# ---------------------------------------------------------------------------
with tab_deals:
    st.markdown(
        section_header("Portfolio Deals Database", "Every deal you extract is stored in an embedded DuckDB file."),
        unsafe_allow_html=True,
    )
    if existing_deals:
        deals_df = pd.DataFrame(existing_deals)
        lead = [
            "company_name", "industry_sector", "capital_structure", "arr", "net_revenue_retention",
            "gross_margin", "ltv_cac_ratio", "runway_months", "ebitda", "confidence_score",
        ]
        order = lead + [c for c in deals_df.columns if c not in lead]
        labels = {
            "company_name": "Company", "industry_sector": "Sector", "capital_structure": "Capital structure",
            "arr": "ARR", "net_revenue_retention": "NRR", "gross_margin": "Gross margin",
            "ltv_cac_ratio": "LTV:CAC", "runway_months": "Runway (mo)", "ebitda": "EBITDA",
            "confidence_score": "Confidence",
        }
        st.dataframe(
            style_portfolio(deals_df),
            hide_index=True,
            column_order=order,
            column_config={k: st.column_config.Column(v) for k, v in labels.items()},
        )
        st.caption("Cell colors follow the value: red is weak, amber is borderline, green is strong.")
    else:
        st.info(
            "No saved deals yet. Run an extraction with your own API key and it will appear here. "
            "The sample deal is not written to the database."
        )
