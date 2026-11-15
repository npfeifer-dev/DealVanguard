from dealvanguard.samples import load_sample_deal, load_sample_memo
from dealvanguard.schemas import ExtractionResult


def test_sample_deal_matches_schema_and_is_labeled():
    deal = load_sample_deal()
    assert isinstance(deal, ExtractionResult)
    assert "Sample" in deal.metadata.company_name
    assert deal.key_risks_identified


def test_sample_memo_is_labeled_fictional():
    assert "FICTIONAL" in load_sample_memo()


def test_no_em_dashes_in_sample_data():
    assert "\u2014" not in load_sample_memo()
    assert "\u2014" not in load_sample_deal().model_dump_json()
