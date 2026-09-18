```mermaid
%%{
  init: {
    'theme': 'base',
    'themeVariables': {
      'fontFamily': 'sans-serif',
      'fontWeight': 'bold',
    },
    'gantt': {
      'titleTopMargin': 50,
      'barHeight': 32,
      'barGap': 20,
      'topPadding': 90,
      'sidePadding': 650,
      'gridLineStartPadding': 50,
      'fontSize': 18,
      'sectionFontSize': 25,
      'numberSectionStyles': 2,
      'axisFormat': '%m/%d',
      'useWidth': 2600
    }
  }
}%%
gantt
    title DealVanguard MIS 448 Capstone - Baseline Schedule
    dateFormat  YYYY-MM-DD
    axisFormat  %m/%d
    tickInterval 2day
    weekday monday
    todayMarker off

    

    section Phase 1: Core Schemas & Storage
    Phase 1 Core Schemas & Storage                :active, p1_summary, 2026-08-20, 8d
    Project Kickoff (08/20)                       :milestone, ms_start, 2026-08-20, 0d
    Metric Schemas (3d)                           :crit, t1, 2026-08-20, 3d
    Tool Calling Schemas (2d)                     :crit, t2, after t1, 2d
    DuckDB Engine (3d)                            :crit, t3, after t2, 3d
    Deal Persistence API (2d)                     :t4, after t3, 2d
    Data Contract Unit Tests (3d)                :t5, after t3, 3d
    Phase 1 Complete (08/28)                      :milestone, ms_p1, after t3, 0d

    section Phase 2: AI Extractor Engine
    Phase 2 AI Extractor Engine                   :active, p2_summary, after t3, 7d
    Anthropic API Setup (2d)                      :crit, t6, after t3, 2d
    Claude Tool Calling (4d)                      :crit, t7, after t6, 4d
    LLM Parsing & Fallback Logic (3d)             :crit, t8, after t7, 3d
    Extractor Unit Tests (3d)                     :t9, after t8, 3d
    Phase 2 Complete (09/06)                      :milestone, ms_p2, after t8, 0d

    section Phase 3: Stress Engine & Math
    Phase 3 Stress Engine & Math                  :active, p3_summary, after t8, 7d
    Vectorized Haircut Engine (4d)                :crit, t10, after t8, 4d
    DSCR & Coverage Ratio Logic (3d)              :crit, t11, after t10, 3d
    Stress Engine Unit Tests (3d)                 :t12, after t10, 3d
    Phase 3 Complete (09/13)                      :milestone, ms_p3, after t11, 0d

    section Phase 4: Streamlit UI & Release
    Phase 4 Streamlit UI & Release                :active, p4_summary, after t11, 6d
    File Upload & Parsing UI (4d)                 :crit, t13, after t11, 4d
    Stress Scenario Controls (3d)                 :crit, t14, after t13, 3d
    DuckDB Portfolio Data Grid (3d)               :t15, after t13, 3d
    Project Launch Complete (09/19)              :milestone, m1, after t14, 0d