import pytest
from unittest.mock import MagicMock, patch
import anthropic
from dealvanguard.ai_extractor import DealExtractor
from dealvanguard.schemas import ExtractionResult, CapitalStructure


@pytest.fixture
def sample_payload():
    return {
        "metadata": {
            "company_name": "Acme SaaS",
            "industry_sector": "B2B Software",
            "capital_structure": "Bootstrapped",
        },
        "metrics": {
            "arr": 1200000.0,
            "mrr": 100000.0,
            "net_revenue_retention": 110.0,
            "gross_margin": 80.0,
            "cac": 4000.0,
            "ltv": 20000.0,
            "ltv_cac_ratio": 5.0,
            "monthly_burn_rate": 20000.0,
            "runway_months": 18.0,
            "total_debt": 0.0,
            "ebitda": 300000.0,
        },
        "key_risks_identified": ["Customer concentration", "High churn rate"],
        "confidence_score": 0.95,
    }


@patch("anthropic.Anthropic")
def test_extractor_initialization(mock_anthropic):
    extractor = DealExtractor(api_key="fake-api-key", model="claude-3-5-sonnet-20241022")
    assert extractor.model == "claude-3-5-sonnet-20241022"
    mock_anthropic.assert_called_once_with(api_key="fake-api-key")


def test_build_tool_definition():
    extractor = DealExtractor(api_key="fake-api-key")
    tool_def = extractor._build_tool_definition()

    assert tool_def["name"] == "extract_deal_metrics"
    assert "input_schema" in tool_def
    assert "properties" in tool_def["input_schema"]


@patch("anthropic.Anthropic")
def test_extract_from_text_success(mock_anthropic, sample_payload):
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client

    mock_tool_block = MagicMock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.input = sample_payload

    mock_response = MagicMock()
    mock_response.content = [mock_tool_block]
    mock_client.messages.create.return_value = mock_response

    extractor = DealExtractor(api_key="fake-api-key")
    result = extractor.extract_from_text("Acme SaaS makes $1.2M ARR...")

    assert isinstance(result, ExtractionResult)
    assert result.metadata.company_name == "Acme SaaS"
    assert result.metadata.capital_structure == CapitalStructure.BOOTSTRAPPED
    assert result.metrics.arr == 1200000.0
    assert result.confidence_score == 0.95


@patch("anthropic.Anthropic")
def test_extract_from_text_missing_tool_use(mock_anthropic):
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client

    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = "I couldn't extract any data."

    mock_response = MagicMock()
    mock_response.content = [mock_text_block]
    mock_client.messages.create.return_value = mock_response

    extractor = DealExtractor(api_key="fake-api-key")

    with pytest.raises(ValueError, match="Claude response missing tool_use block."):
        extractor.extract_from_text("Unusable text document...")


@patch("anthropic.Anthropic")
def test_extract_from_text_validation_error(mock_anthropic, sample_payload):
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client

    invalid_payload = sample_payload.copy()
    invalid_payload["metrics"]["arr"] = -500.0

    mock_tool_block = MagicMock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.input = invalid_payload

    mock_response = MagicMock()
    mock_response.content = [mock_tool_block]
    mock_client.messages.create.return_value = mock_response

    extractor = DealExtractor(api_key="fake-api-key")

    with pytest.raises(RuntimeError, match="Data Contract Violation"):
        extractor.extract_from_text("Invalid metrics document...")


@patch("anthropic.Anthropic")
def test_extract_from_text_api_error(mock_anthropic):
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client

    mock_client.messages.create.side_effect = anthropic.APIError(
        message="Rate limit reached", request=MagicMock(), body=None
    )

    extractor = DealExtractor(api_key="fake-api-key")

    with pytest.raises(RuntimeError, match="Anthropic API Execution failed"):
        extractor.extract_from_text("Sample pitch deck text...")