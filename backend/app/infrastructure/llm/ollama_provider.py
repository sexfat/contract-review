from __future__ import annotations

import logging

import httpx
from langchain_core.exceptions import OutputParserException
from langchain_ollama import ChatOllama
from pydantic import ValidationError

from app.domain.errors import LLMOutputInvalidError, LLMProviderUnavailableError
from app.domain.schemas.clause_type import ClauseType
from app.domain.schemas.llm_classification import LLMClassificationRequest, LLMClassificationResult
from app.infrastructure.llm.config import LLMSettings

logger = logging.getLogger("contract_review.llm")

_SYSTEM_PROMPT = (
    "你是合約條款分類助手。僅根據使用者提供的單一條款原文作答，"
    "不得引用原文以外的任何資訊，不得臆造金額、日期、法條或義務。"
    f"clause_type 必須是下列其中之一：{', '.join(t.value for t in ClauseType)}。"
    "plain_summary 須為白話中文摘要，且不得出現原文未提及的金額或日期。"
    "confidence 為 0 到 1 之間的浮點數，反映你對本次分類與摘要的信心程度。"
)

# Connectivity/auth failures should fail the whole document (spec.md 情境
# 「LLM provider 整體無法連線」); output-shape failures are retried per
# clause. Anything neither pattern recognizes is treated as the former —
# failing loud beats silently downgrading an unknown error into fabricated
# "low confidence" data.
_CONNECTIVITY_EXCEPTIONS = (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError, TimeoutError)
_OUTPUT_EXCEPTIONS = (ValidationError, OutputParserException, ValueError)


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
        except _CONNECTIVITY_EXCEPTIONS:
            logger.warning("llm_provider_unavailable", extra={"clause_id": request.clause_id})
            # `from None` suppresses exception chaining: the original error
            # (e.g. a pydantic ValidationError embedding the LLM's raw output,
            # which may echo contract text from the prompt) must never reach
            # a traceback that main.py's exc_info logging could later print.
            raise LLMProviderUnavailableError() from None
        except _OUTPUT_EXCEPTIONS:
            logger.info("llm_output_invalid", extra={"clause_id": request.clause_id})
            raise LLMOutputInvalidError() from None
        except Exception:  # noqa: BLE001 — unrecognized failure, fail loud not silent
            logger.error("llm_provider_unrecognized_error", extra={"clause_id": request.clause_id})
            raise LLMProviderUnavailableError() from None

        if not isinstance(result, LLMClassificationResult):
            raise LLMOutputInvalidError()

        if result.clause_id != request.clause_id:
            result = result.model_copy(update={"clause_id": request.clause_id})
        return result
