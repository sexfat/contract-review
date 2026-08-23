from __future__ import annotations

import logging
from typing import NoReturn

import httpx
from langchain_core.exceptions import OutputParserException
from pydantic import ValidationError

from app.domain.errors import LLMOutputInvalidError, LLMProviderUnavailableError

# Connectivity/auth failures fail the whole document (spec.md 情境「LLM
# provider 整體無法連線」); output-shape failures are retried per item.
# Anything neither pattern recognizes is treated as the former — failing
# loud beats silently downgrading an unknown error into fabricated data.
_CONNECTIVITY_EXCEPTIONS = (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError, TimeoutError)
_OUTPUT_EXCEPTIONS = (ValidationError, OutputParserException, ValueError)


def raise_mapped_llm_exception(exc: Exception, *, logger: logging.Logger, log_extra: dict) -> NoReturn:
    """Classifies a raw LLM-call exception and raises the corresponding
    domain error. Always raised with `from None`: the original exception
    (e.g. a pydantic ValidationError embedding the LLM's raw output, which
    may echo contract text from the prompt) must never reach a traceback
    that the global handler's exc_info logging could later print — see
    specs/002-llm-clause-classification/spec.md 驗收紀錄."""
    if isinstance(exc, _CONNECTIVITY_EXCEPTIONS):
        logger.warning("llm_provider_unavailable", extra=log_extra)
        raise LLMProviderUnavailableError() from None
    if isinstance(exc, _OUTPUT_EXCEPTIONS):
        logger.info("llm_output_invalid", extra=log_extra)
        raise LLMOutputInvalidError() from None
    logger.error("llm_provider_unrecognized_error", extra=log_extra)  # noqa: LOG015
    raise LLMProviderUnavailableError() from None
