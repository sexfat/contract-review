from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from app.application.commands.classify_clauses import ClassifyClausesCommand
from app.application.commands.parse_document import ParseDocumentCommand
from app.application.commands.review_document import ReviewDocumentCommand
from app.application.commands.upload_document import UploadDocumentCommand
from app.application.ports.embedding_provider import EmbeddingProvider
from app.application.ports.knowledge_repository import KnowledgeRepository
from app.application.ports.llm_provider import LLMProvider
from app.application.ports.risk_assessment_provider import RiskAssessmentProvider
from app.application.ports.risk_judge_provider import RiskJudgeProvider
from app.application.queries.get_clauses import GetClausesQuery
from app.application.queries.get_review_report import GetReviewReportQuery
from app.infrastructure.llm.config import load_llm_settings
from app.infrastructure.llm.ollama_embedding_provider import OllamaEmbeddingProvider
from app.infrastructure.llm.ollama_provider import OllamaClassificationProvider
from app.infrastructure.llm.ollama_risk_judge_provider import OllamaRiskJudgeProvider
from app.infrastructure.llm.ollama_risk_provider import OllamaRiskAssessmentProvider
from app.infrastructure.repositories.json_risk_rule_repository import JsonRiskRuleRepository
from app.infrastructure.repositories.local_vector_knowledge_repository import (
    LocalVectorKnowledgeRepository,
    NullKnowledgeRepository,
)
from app.infrastructure.repositories.memory_repository import (
    InMemoryClauseClassificationRepository,
    InMemoryClauseRepository,
    InMemoryDocumentRepository,
    InMemoryRiskAssessmentRepository,
)
from app.infrastructure.storage.local_file_storage import LocalFileStorage

logger = logging.getLogger("contract_review.dependencies")

_REPO_ROOT = Path(__file__).resolve().parents[3]
_STORAGE_DIR = _REPO_ROOT / "backend" / "var" / "documents"
_RISK_RULES_PATH = _REPO_ROOT / "data" / "risk_rules.seed.json"
_LEGAL_SOURCES_PATH = _REPO_ROOT / "data" / "legal_sources.seed.json"
_LEGAL_SOURCES_EMBEDDINGS_PATH = _REPO_ROOT / "data" / "legal_sources.embeddings.npz"


@lru_cache
def get_document_repository() -> InMemoryDocumentRepository:
    return InMemoryDocumentRepository()


@lru_cache
def get_clause_repository() -> InMemoryClauseRepository:
    return InMemoryClauseRepository()


@lru_cache
def get_classification_repository() -> InMemoryClauseClassificationRepository:
    return InMemoryClauseClassificationRepository()


@lru_cache
def get_risk_assessment_repository() -> InMemoryRiskAssessmentRepository:
    return InMemoryRiskAssessmentRepository()


@lru_cache
def get_risk_rule_repository() -> JsonRiskRuleRepository:
    return JsonRiskRuleRepository(_RISK_RULES_PATH)


@lru_cache
def get_file_storage() -> LocalFileStorage:
    return LocalFileStorage(_STORAGE_DIR)


@lru_cache
def get_llm_provider() -> LLMProvider:
    # Raises pydantic's ValidationError if OLLAMA_API_KEY is unset — fail
    # fast on first /classify call rather than silently misbehaving later.
    settings = load_llm_settings()
    return OllamaClassificationProvider(settings)


@lru_cache
def get_risk_assessment_provider() -> RiskAssessmentProvider:
    settings = load_llm_settings()
    return OllamaRiskAssessmentProvider(settings)


@lru_cache
def get_risk_judge_provider() -> RiskJudgeProvider:
    settings = load_llm_settings()
    return OllamaRiskJudgeProvider(settings)


@lru_cache
def get_embedding_provider() -> EmbeddingProvider | None:
    """None (not an exception) when no embedding model is configured yet —
    mirrors 002's "lazily resolved, fail soft at the edge" stance for
    optional capabilities. get_knowledge_repository() falls back to
    NullKnowledgeRepository when this is None (specs/005-rag-and-judge-gate/
    spec.md Failure handling)."""
    try:
        settings = load_llm_settings()
    except Exception:  # noqa: BLE001 — e.g. OLLAMA_API_KEY unset
        return None
    if settings.ollama_embedding_model is None:
        return None
    return OllamaEmbeddingProvider(settings)


@lru_cache
def get_knowledge_repository() -> KnowledgeRepository:
    embedding_provider = get_embedding_provider()
    if embedding_provider is None or not _LEGAL_SOURCES_EMBEDDINGS_PATH.exists():
        logger.info("knowledge_repository_fallback_null")
        return NullKnowledgeRepository()
    return LocalVectorKnowledgeRepository(_LEGAL_SOURCES_PATH, _LEGAL_SOURCES_EMBEDDINGS_PATH, embedding_provider)


def get_upload_document_command() -> UploadDocumentCommand:
    return UploadDocumentCommand(
        document_repository=get_document_repository(),
        file_storage=get_file_storage(),
    )


def get_parse_document_command() -> ParseDocumentCommand:
    return ParseDocumentCommand(
        document_repository=get_document_repository(),
        clause_repository=get_clause_repository(),
        file_storage=get_file_storage(),
    )


def get_classify_clauses_command() -> ClassifyClausesCommand:
    return ClassifyClausesCommand(
        document_repository=get_document_repository(),
        clause_repository=get_clause_repository(),
        classification_repository=get_classification_repository(),
        llm_provider=get_llm_provider(),
    )


def get_review_document_command() -> ReviewDocumentCommand:
    return ReviewDocumentCommand(
        document_repository=get_document_repository(),
        classification_repository=get_classification_repository(),
        risk_rule_repository=get_risk_rule_repository(),
        risk_assessment_repository=get_risk_assessment_repository(),
        risk_provider=get_risk_assessment_provider(),
        knowledge_repository=get_knowledge_repository(),
        judge_provider=get_risk_judge_provider(),
    )


def get_clauses_query() -> GetClausesQuery:
    return GetClausesQuery(
        document_repository=get_document_repository(),
        clause_repository=get_clause_repository(),
        classification_repository=get_classification_repository(),
    )


def get_review_report_query() -> GetReviewReportQuery:
    return GetReviewReportQuery(
        document_repository=get_document_repository(),
        classification_repository=get_classification_repository(),
        risk_assessment_repository=get_risk_assessment_repository(),
    )
