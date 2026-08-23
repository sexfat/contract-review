from __future__ import annotations

import logging

from langchain_ollama import ChatOllama

from app.domain.errors import LLMOutputInvalidError
from app.domain.schemas.clause_type import ClauseType
from app.domain.schemas.llm_classification import LLMClassificationRequest, LLMClassificationResult
from app.infrastructure.llm.config import LLMSettings
from app.infrastructure.llm.exception_mapping import raise_mapped_llm_exception

logger = logging.getLogger("contract_review.llm")

_SYSTEM_PROMPT = (
    "你是合約條款分類助手。僅根據使用者提供的單一條款原文作答，"
    "不得引用原文以外的任何資訊，不得臆造金額、日期、法條或義務。"
    f"clause_type 必須是下列其中之一：{', '.join(t.value for t in ClauseType)}。"
    "plain_summary 須為白話中文摘要，且不得出現原文未提及的金額或日期。"
    "confidence 為 0 到 1 之間的浮點數，反映你對本次分類與摘要的信心程度。\n\n"
    # `with_structured_output` alone was found (003 live testing) to not
    # reliably constrain gemma4:31b-cloud's output via Ollama Cloud for a
    # more complex risk-assessment schema — the model invented its own JSON
    # shape instead of following the Pydantic schema. This task's simpler
    # schema happened to work without this, but spelling the exact expected
    # JSON out explicitly removes the reliance on that being a coincidence.
    "請只輸出一個 JSON 物件，格式完全比照以下範例，欄位名稱與型別必須一致："
    '{"clause_id": "與輸入相同的 clause_id", "clause_type": "scope", '
    '"plain_summary": "白話摘要", "confidence": 0.8}\n'
    "不要輸出其他任何文字、標題或說明。"
)


class OllamaClassificationProvider:
    """Infrastructure adapter: the only place langchain_ollama / model choice
    appears (SDD_ARCHITECTURE.md §4 dependency rule)."""

    def __init__(self, settings: LLMSettings) -> None:
        self.model_id = settings.ollama_model
        chat = ChatOllama(
            model=settings.ollama_model,
            base_url=str(settings.ollama_base_url),
            timeout=settings.request_timeout_seconds,
        )
        self._structured_chat = chat.with_structured_output(LLMClassificationResult)

    def classify_clause(self, request: LLMClassificationRequest) -> LLMClassificationResult:
        human_prompt = f"clause_id: {request.clause_id}\n條款原文：\n{request.original_text}"
        try:
            result = self._structured_chat.invoke(
                [("system", _SYSTEM_PROMPT), ("human", human_prompt)]
            )
        except Exception as exc:  # noqa: BLE001 — classified by raise_mapped_llm_exception
            raise_mapped_llm_exception(exc, logger=logger, log_extra={"clause_id": request.clause_id})

        if not isinstance(result, LLMClassificationResult):
            raise LLMOutputInvalidError()

        if result.clause_id != request.clause_id:
            result = result.model_copy(update={"clause_id": request.clause_id})
        return result
