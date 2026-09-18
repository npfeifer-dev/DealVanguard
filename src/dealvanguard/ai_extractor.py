import logging
from typing import Any, Dict, List, Optional, cast
import anthropic
from anthropic.types import MessageParam, ToolChoiceToolParam, ToolParam
from pydantic import ValidationError

from dealvanguard.schemas import ExtractionResult

logger = logging.getLogger(__name__)


class DealExtractor:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-7-sonnet-20250219",
    ):
        self.client = (
            anthropic.Anthropic(api_key=api_key)
            if api_key
            else anthropic.Anthropic()
        )
        self.model = model

    def _build_tool_definition(self) -> ToolParam:
        schema = ExtractionResult.model_json_schema()
        tool: ToolParam = {
            "name": "extract_deal_metrics",
            "description": (
                "Extracts structured financial metrics, SaaS KPIs, metadata, and risk disclosures from deal room documents."
            ),
            "input_schema": cast(Dict[str, Any], schema),
        }
        return tool

    def extract_from_text(self, document_text: str) -> ExtractionResult:
        tool_definition = self._build_tool_definition()

        tool_choice: ToolChoiceToolParam = {
            "type": "tool",
            "name": "extract_deal_metrics",
        }

        messages: List[MessageParam] = [
            {
                "role": "user",
                "content": f"Extract financial metrics from the following text:\n\n{document_text}",
            }
        ]

        system_prompt = (
            "You are a Principal Investment Analyst at a Private Equity firm. Your task is to "
            "read raw deal room text, Confidential Information Memorandums (CIMs), or pitch documents "
            "and rigorously extract financial metrics, SaaS parameters, and potential risks. "
            "Normalize all numbers into exact floating point numbers (e.g. $12.5M ARR = 12500000.0). "
            "You must invoke the `extract_deal_metrics` tool with the extracted structured data."
        )

        try:
            response = self.client.messages.create(
                max_tokens=2048,
                messages=messages,
                model=self.model,
                system=system_prompt,
                tools=[tool_definition],
                tool_choice=tool_choice,
            )

            tool_use_block = next(
                (
                    block
                    for block in response.content
                    if block.type == "tool_use"
                ),
                None,
            )
            if not tool_use_block:
                raise ValueError("Claude response missing tool_use block.")

            raw_input = tool_use_block.input

            result = ExtractionResult.model_validate(raw_input)
            return result

        except ValidationError as ve:
            logger.error("Validation error on Claude payload: %s", ve)
            raise RuntimeError(f"Data Contract Violation: {ve}") from ve
        except anthropic.APIError as ae:
            logger.error("Anthropic API error: %s", ae)
            raise RuntimeError(
                f"Anthropic API Execution failed: {ae}"
            ) from ae