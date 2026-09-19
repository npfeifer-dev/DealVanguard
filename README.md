[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://DealVanguard.streamlit.app)
# DealVanguard AI

**DealVanguard AI** is an enterprise deal diligence platform built for automated financial extraction, risk modeling, and interactive deal analytics. Powered by Claude, DuckDB, and Streamlit, it enables seamless deal ingestion, automated schema parsing, and interactive stress testing.

---

## Project Architecture

```text
dealvanguard/
├── .github/workflows/ci.yml
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── setup.py
├── docs/
│   └── Schedule_Gantt_CPM_Analysis.md
├── src/
│   └── dealvanguard/
│       ├── __init__.py
│       ├── config.py
│       ├── schemas.py
│       ├── ai_extractor.py
│       ├── database.py
│       ├── stress_engine.py
│       └── app.py
└── tests/
    ├── test_schemas.py
    ├── test_ai_extractor.py
    ├── test_database.py
    └── test_stress_engine.py
