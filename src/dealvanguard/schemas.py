from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class CapitalStructureType(str, Enum):
    SENIOR_DEBT = "Senior Debt"
    MEZZANINE = "Mezzanine"
    CONVERTIBLE_NOTE = "Convertible Note"
    EQUITY = "Equity"

class FinancialMetrics(BaseModel):
    """Core financial metrics extracted from pitch decks, CIMs, or VDR documents."""    
    model_config = ConfigDict(extra="forbid", frozen=True)

    arr: float = Field(
        description="Annual Recurring Revenue (ARR) in USD",
        ge=0.0
    )
    mrr: float = Field(
        description="Monthly Recurring Revenue (MRR) in USD",
        ge=0.0
    )
    net_revenue_retention: float = Field(
        description="Net Revenue Retention (NRR) expressed as a percentage",
        ge=0.0,
        le=300.0
    )
    gross_margin: float = Field(
        description="Gross Profit Margin expressed as a percentage",
        ge=-100.0,
        le=100.0
    )
    cac: float = Field(
        description="Customer Acquisition Cost (CAC) in USD",
        ge=0.0
    )
    ltv: float = Field(
        description="Customer Lifetime Value (LTV) in USD",
        ge=0.0
    )
    ltv_cac_ratio: float = Field(
        description="LTV:CAC Ratio",
        ge=0.0
    )
    monthly_burn_rate: float = Field(
        description="Monthly Burn Rate in USD",
        ge=0.0
    )
    runway_months: Optional[float] = Field(
        default=None,
        description="Runway in months, calculated as Cash Balance divided by Monthly Burn Rate",
        ge=0.0
    )
    total_debt: float = Field(
        default=0.0,
        description="Total debt principal in USD",
        ge=0.0
    )
    ebitda: float = Field(
        description="Earnings Before Interest, Taxes, Depreciation, and Amortization (EBITDA) in USD",
    )

class DealMetadata(BaseModel):
    """Metadata regarding the deal target and document extraction process."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    company_name: str = Field(description="Legal or commercial name of the target entity.")
    industry_sector: str = Field(description="Primary industry or SaaS vertical.")
    founding_year: Optional[int] = Field(default=None, description="Year the company was founded.")
    as_of_date: Optional[str] = Field(
        default=None, 
        description="Effective reporting date or memorandum date of the financial metrics (e.g. '2023-12-31' or 'Q3 2022')."
    )
    capital_structure: CapitalStructureType = Field(
        default=CapitalStructureType.EQUITY,
        description="Primary debt/equity instrument of interest."
    )
    extraction_timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp of extraction execution."
    )

class ExtractionResult(BaseModel):
    """Container schema returned by Claude tool calling orchestration."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    metadata: DealMetadata
    metrics: FinancialMetrics
    confidence_score: float = Field(
        description="Model confidence score between 0.0 and 1.0 regarding metric completeness and accuracy.",
        ge=0.0,
        le=1.0
    )
    key_risks_identified: List[str] = Field(
        default_factory=list,
        description="List of top operations or financial risk disclosures extracted from text."
    )