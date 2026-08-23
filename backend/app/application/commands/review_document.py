from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.application.ports.clause_classification_repository import ClauseClassificationRepository
from app.application.ports.document_repository import DocumentRepository
from app.application.ports.risk_assessment_provider import RiskAssessmentProvider
from app.application.ports.risk_assessment_repository import RiskAssessmentRepository
from app.application.ports.risk_rule_repository import RiskRuleRepository
from app.domain.entities.document import Document, DocumentStatus
from app.domain.errors import (
    DocumentNotFoundError,
    DocumentNotReadyError,
    LLMOutputInvalidError,
    LLMProviderUnavailableError,
)
from app.domain.schemas.extracted_clause import ExtractedClause
from app.domain.schemas.llm_risk_assessment import RiskAssessmentRequest, RiskAssessmentResult
from app.domain.schemas.risk_assessment import EvidenceRef, RiskAssessment
from app.domain.schemas.risk_rule import RiskRule
from app.domain.services.conservative_language_guard import find_banned_phrase
from app.domain.services.risk_rule_matcher import match_rules

_READY_STATUSES = (DocumentStatus.CLASSIFIED, DocumentStatus.COMPLETED)


@dataclass
class ReviewDocumentCommand:
    document_repository: DocumentRepository
    classification_repository: ClauseClassificationRepository
    risk_rule_repository: RiskRuleRepository
    risk_assessment_repository: RiskAssessmentRepository
    risk_provider: RiskAssessmentProvider
    max_retries: int = 1

    def __post_init__(self) -> None:
        if not 0 <= self.max_retries <= 1:
            raise ValueError("max_retries must be 0 or 1 (spec.md FR8: 最多重試一次)")

    def execute(self, document_id: str) -> Document:
        document = self.document_repository.get(document_id)
        if document is None:
            raise DocumentNotFoundError()
        if document.status not in _READY_STATUSES:
            raise DocumentNotReadyError()

        self.document_repository.set_status(document_id, DocumentStatus.REVIEWING)

        clauses = self.classification_repository.list_for_document(document_id)
        rules = self.risk_rule_repository.list_reviewed()

        risks: list[RiskAssessment] = []
        try:
            for clause in clauses:
                for rule in match_rules(clause, rules):
                    risk = self._assess_one(clause, rule, document.checksum)
                    if risk is not None:
                        risks.append(risk)
        except LLMProviderUnavailableError as exc:
            self.document_repository.set_status(document_id, DocumentStatus.FAILED, exc.error_code)
            raise

        self.risk_assessment_repository.replace_for_document(document_id, risks)
        self.document_repository.set_status(document_id, DocumentStatus.COMPLETED)

        reviewed_document = self.document_repository.get(document_id)
        assert reviewed_document is not None
        return reviewed_document

    def _assess_one(self, clause: ExtractedClause, rule: RiskRule, checksum: str) -> RiskAssessment | None:
        request = RiskAssessmentRequest(
            clause_id=clause.clause_id,
            clause_type=clause.clause_type,
            original_text=clause.original_text,
            rule_id=rule.id,
            rule_topic=rule.topic,
            rule_risk_explanation=rule.risk_explanation,
            rule_review_questions=rule.review_questions,
            rule_suggestion_template=rule.suggestion_template,
        )

        for _ in range(self.max_retries + 1):
            try:
                result = self.risk_provider.assess_risk(request)
            except LLMOutputInvalidError:
                continue

            if not result.applicable:
                return None  # LLM 判斷此規則其實不適用；非驗證失敗

            if not result.evidence or not all(e.quote in clause.original_text for e in result.evidence):
                continue  # RiskAssessment.evidence requires >=1 item (DEVELOPMENT_SPEC.md §7)
            if find_banned_phrase(result.concern) or find_banned_phrase(result.suggestion):
                continue

            return self._to_risk_assessment(clause, rule, result, checksum)

        return None  # 重試後仍未通過驗證：捨棄，不產生佔位風險

    def _to_risk_assessment(
        self, clause: ExtractedClause, rule: RiskRule, result: RiskAssessmentResult, checksum: str
    ) -> RiskAssessment:
        risk_id = hashlib.sha256(f"{checksum}{clause.clause_id}{rule.id}".encode()).hexdigest()[:20]
        return RiskAssessment(
            risk_id=risk_id,
            clause_id=clause.clause_id,
            clause_type=clause.clause_type,
            risk_for_client=result.risk_for_client,
            risk_for_vendor=result.risk_for_vendor,
            concern=result.concern,
            suggestion=result.suggestion,
            evidence=[
                EvidenceRef(clause_id=clause.clause_id, quote=e.quote, rationale=e.rationale)
                for e in result.evidence
            ],
            source_refs=[rule.id],
            confidence=result.confidence,
            requires_human_review=False,
        )
