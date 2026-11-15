"""Loaders for the fictional sample deal that ships with the repo."""
import json
from pathlib import Path

from dealvanguard.schemas import ExtractionResult

SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "sample_data"
SAMPLE_DEAL_PATH = SAMPLE_DIR / "sample_deal.json"
SAMPLE_MEMO_PATH = SAMPLE_DIR / "sample_deal_memo.txt"


def load_sample_deal(path: Path = SAMPLE_DEAL_PATH) -> ExtractionResult:
    """Loads the fictional example deal, validated by the same schema as real extractions."""
    with open(path, encoding="utf-8") as fh:
        return ExtractionResult.model_validate(json.load(fh))


def load_sample_memo(path: Path = SAMPLE_MEMO_PATH) -> str:
    """Returns the fictional example memo that can be pasted into the extraction box."""
    return Path(path).read_text(encoding="utf-8")
