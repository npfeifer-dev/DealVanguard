import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import duckdb

from dealvanguard.schemas import ExtractionResult

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages DuckDB embedded database connections,

    schema initialization, and deal persistence.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = db_path
        else:
            root_dir = Path(__file__).resolve().parent.parent.parent
            self.db_path = str(root_dir / "data" / "dealvanguard.db")

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Returns connection instance to DuckDB file."""
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
        """Persists validated ExtractionResult Pydantic payload

        directly into relational DuckDB database table.
        """
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
            json.dumps(
                extraction.key_risks_identified
                if extraction.key_risks_identified
                else []
            ),
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