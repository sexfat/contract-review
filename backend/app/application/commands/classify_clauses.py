from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.clause_classification_repository import ClauseClassificationRepository
from app.application.ports.clause_repository import ClauseRepository
from app.application.ports.document_repository import DocumentRepository
from app.application.ports.llm_provider import LLMProvider
from app.domain.entities.document import Document, DocumentStatus
from app.domain.errors import (
    DocumentNotFoundError,
    DocumentNotReadyError,
    LLMOutputInvalidError,
    LLMProviderUnavailableError,
)
from app.domain.schemas.clause import ParsedClause
from app.domain.schemas.clause_type import ClauseType
from app.domain.schemas.extracted_clause import ExtractedClause
from app.domain.schemas.llm_classification import LLMClassificationRequest, LLMClassificationResult
from app.domain.services.summary_guard import find_ungrounded_amounts_and_dates

_READY_STATUSES = (DocumentStatus.PARSED, DocumentStatus.CLASSIFIED)

_FALLBACK_SUMMARY = "此條款目前無法可靠分析，建議人工確認。"


@dataclass
class ClassifyClausesCommand:
    document_repository: DocumentRepository
    clause_repository: ClauseRepository
    classification_repository: ClauseClassificationRepository
    llm_provider: LLMProvider
    max_retries: int = 1

    def execute(self, document_id: str) -> Document:
        document = self.document_repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError()
        if document.status not in _READY_STATUSES:
            raise DocumentNotReadyError()

        self.document_repository.set_status(document_id, DocumentStatus.CLASSIFYING)

        parsed_clauses = self.clause_repository.list_for_document(document_id)
        try:
            extracted = [self._classify_one(clause) for clause in parsed_clauses]
        except LLMProviderUnavailableError as exc:
            self.document_repository.set_status(document_id, DocumentStatus.FAILED, exc.error_code)
            raise

        self.classification_repository.replace_for_document(document_id, extracted)
        self.document_repository.set_status(document_id, DocumentStatus.CLASSIFIED)

        classified_document = self.document_repository.get(document_id)
        assert classified_document is not None
        return classified_document

    def _classify_one(self, clause: ParsedClause) -> ExtractedClause:
        request = LLMClassificationRequest(clause_id=clause.clause_id, original_text=clause.original_text)

        for _ in range(self.max_retries + 1):
            try:
                result = self.llm_provider.classify_clause(request)
            except LLMOutputInvalidError:
                continue

            ungrounded = find_ungrounded_amounts_and_dates(clause.original_text, result.plain_summary)
            if not ungrounded:
                return self._to_extracted_clause(clause, result, requires_human_review=False)

        return self._fallback_clause(clause)

    def _to_extracted_clause(
        self, clause: ParsedClause, result: LLMClassificationResult, *, requires_human_review: bool
    ) -> ExtractedClause:
        return ExtractedClause(
            clause_id=clause.clause_id,
            clause_type=result.clause_type,
            original_text=clause.original_text,
            location=clause.location,
            plain_summary=result.plain_summary,
            confidence=result.confidence,
            requires_human_review=requires_human_review,
            model_id=self.llm_provider.model_id,
        )

    def _fallback_clause(self, clause: ParsedClause) -> ExtractedClause:
        return ExtractedClause(
            clause_id=clause.clause_id,
            clause_type=ClauseType.OTHER,
            original_text=clause.original_text,
            location=clause.location,
            plain_summary=_FALLBACK_SUMMARY,
            confidence=0.0,
            requires_human_review=True,
            model_id=self.llm_provider.model_id,
        )
