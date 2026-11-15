import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import duckdb

from dealvanguard.schemas import ExtractionResult

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages the embedded DuckDB file: schema setup and deal persistence."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        else:
            root_dir = Path(__file__).resolve().parent.parent.parent
            self.db_path = str(root_dir / "data" / "dealvanguard.db")

        # An in-memory DuckDB database disappears with its connection, so keep one open.
        self._memory_conn: Optional[duckdb.DuckDBPyConnection] = None
        if self.db_path == ":memory:":
            self._memory_conn = duckdb.connect(":memory:")
        else:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Returns a connection to the DuckDB file (a cursor on the shared one for :memory:)."""
        if self._memory_conn is not None:
            return self._memory_conn.cursor()
        return duckdb.connect(self.db_path)

    def _init_db(self) -> None:
        """Creates target SQL relational table if not exists."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS extracted_deals (
            deal_id VARCHAR PRIMARY KEY,
            company_name VARCHAR NOT NULL,
            industry_sector VARCHAR,
            founding_year INTEGER,
            capital_structure VARCHAR,
            extraction_timestamp TIMESTAMP,
            arr DOUBLE,
            mrr DOUBLE,
            net_revenue_retention DOUBLE,
            gross_margin DOUBLE,
            cac DOUBLE,
            ltv DOUBLE,
            ltv_cac_ratio DOUBLE,
            monthly_burn_rate DOUBLE,
            runway_months DOUBLE,
            total_debt DOUBLE,
            ebitda DOUBLE,
            confidence_score DOUBLE,
            key_risks_json VARCHAR
        );
        """
        with self.get_connection() as conn:
            conn.execute(schema_sql)
            logger.info("DuckDB schema initialized successfully.")

    def save_deal(self, deal_id: str, extraction: ExtractionResult) -> None:
        """Persists a validated ExtractionResult into the extracted_deals table."""
        meta = extraction.metadata
        metrics = extraction.metrics

        cap_struct = getattr(
            meta.capital_structure, "value", meta.capital_structure
        )

        insert_sql = """
        INSERT OR REPLACE INTO extracted_deals VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        );
        """

        parameters = [
            deal_id,
            meta.company_name,
            meta.industry_sector,
            meta.founding_year,
            cap_struct,
            meta.extraction_timestamp,
            metrics.arr,
            metrics.mrr,
            metrics.net_revenue_retention,
            metrics.gross_margin,
            metrics.cac,
            metrics.ltv,
            metrics.ltv_cac_ratio,
            metrics.monthly_burn_rate,
            metrics.runway_months,
            metrics.total_debt,
            metrics.ebitda,
            extraction.confidence_score,
            json.dumps(extraction.key_risks_identified or []),
        ]

        with self.get_connection() as conn:
            conn.execute(insert_sql, parameters)
            logger.info("Deal %s saved to DuckDB.", deal_id)

    def fetch_all_deals(self) -> List[Dict[str, Any]]:
        """Queries stored deals as list of dictionaries."""
        with self.get_connection() as conn:
            rel = conn.sql(
                "SELECT * FROM extracted_deals ORDER BY extraction_timestamp DESC"
            )
            if rel is None:
                return []
            df = rel.df()
            records = df.to_dict(orient="records")
            return cast(List[Dict[str, Any]], records)


def _clean(value: Any) -> Any:
    """Turns pandas/NumPy NaN and NaT into None so Pydantic can validate the value."""
    if value is None:
        return None
    try:
        if isinstance(value, float) and math.isnan(value):
            return None
        if hasattr(value, "item"):
            value = value.item()
        if isinstance(value, float) and math.isnan(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def record_to_extraction(record: Dict[str, Any]) -> ExtractionResult:
    """Rebuilds a nested ExtractionResult from one flat extracted_deals row."""
    risks_raw = record.get("key_risks_json") or "[]"
    try:
        risks = json.loads(risks_raw) if isinstance(risks_raw, str) else list(risks_raw)
    except json.JSONDecodeError:
        risks = [str(risks_raw)]

    timestamp = _clean(record.get("extraction_timestamp"))
    if timestamp is not None and hasattr(timestamp, "isoformat"):
        timestamp = timestamp.isoformat()

    founding_year = _clean(record.get("founding_year"))
    metadata: Dict[str, Any] = {
        "company_name": record.get("company_name") or "Unknown",
        "industry_sector": record.get("industry_sector") or "Not specified",
        "founding_year": int(founding_year) if founding_year is not None else None,
        "capital_structure": record.get("capital_structure") or "Equity",
    }
    if timestamp is not None:
        metadata["extraction_timestamp"] = str(timestamp)

    metric_fields = [
        "arr", "mrr", "net_revenue_retention", "gross_margin", "cac", "ltv",
        "ltv_cac_ratio", "monthly_burn_rate", "runway_months", "total_debt", "ebitda",
    ]
    metrics = {name: _clean(record.get(name)) for name in metric_fields}
    if metrics["total_debt"] is None:
        metrics["total_debt"] = 0.0

    confidence = _clean(record.get("confidence_score"))
    return ExtractionResult.model_validate(
        {
            "metadata": metadata,
            "metrics": metrics,
            "confidence_score": float(confidence) if confidence is not None else 0.0,
            "key_risks_identified": risks,
        }
    )
