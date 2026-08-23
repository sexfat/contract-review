from __future__ import annotations

import logging

from langchain_ollama import ChatOllama

from app.domain.errors import LLMOutputInvalidError
from app.domain.schemas.llm_risk_assessment import RiskAssessmentRequest, RiskAssessmentResult
from app.infrastructure.llm.config import LLMSettings
from app.infrastructure.llm.exception_mapping import raise_mapped_llm_exception

logger = logging.getLogger("contract_review.llm")

_SYSTEM_PROMPT = (
    "你是軟體開發合約的雙視角風險審閱助手。僅能根據使用者提供的單一條款原文，"
    "以及這一條風險規則的主題、風險說明、審閱問題與建議範本作答；"
    "不得引用其他規則或條款，不得臆造原文未提及的事實、金額、日期或法條。"
    "先判斷這條規則是否真的適用於此條款：若原文只是字面剛好命中觸發詞、但實質內容不構成該規則描述的風險，"
    "請將 applicable 設為 false；此時 risk_for_client 與 risk_for_vendor 請填 \"none\"，"
    "concern 與 suggestion 請填 \"不適用\"，evidence 請填空陣列 []——絕對不要留空字串。"
    "若適用，請同時給出甲方（業主）與乙方（開發商）視角的風險等級（high/medium/low/none）、"
    "以保守措辭（可能有疑慮、建議確認、可考慮協商）描述疑慮與建議，"
    "禁止使用「本條無效」「一定會賠償」「保證勝訴」等斷言用語。"
    "evidence 的每一則 quote 必須逐字出現在條款原文中。"
    "confidence 為 0 到 1 之間的浮點數。\n\n"
    # `with_structured_output` alone was found (live testing, 003 驗收) to not
    # reliably constrain gemma4:31b-cloud's output via Ollama Cloud — the
    # model would invent its own JSON shape and ignore the Pydantic schema.
    # Spelling the exact expected JSON out in the prompt itself fixed it.
    # It also emitted empty strings ("") for risk_for_client/concern/etc when
    # applicable=false, which fails RiskLevel enum / min_length=1 validation
    # — the two example lines below (applicable / not-applicable) fixed that.
    "請只輸出一個 JSON 物件，格式完全比照以下其中一個範例，欄位名稱與型別必須一致：\n"
    "適用時："
    '{"applicable": true, "risk_for_client": "low", "risk_for_vendor": "high", '
    '"concern": "可能有疑慮的描述", "suggestion": "建議的描述", '
    '"evidence": [{"quote": "逐字出現在原文中的引用", "rationale": "為何這段話支持此風險判斷"}], '
    '"confidence": 0.8}\n'
    "不適用時："
    '{"applicable": false, "risk_for_client": "none", "risk_for_vendor": "none", '
    '"concern": "不適用", "suggestion": "不適用", "evidence": [], "confidence": 0.9}\n'
    "不要輸出其他任何文字、標題或說明。"
)


class OllamaRiskAssessmentProvider:
    """Infrastructure adapter for LLM Task B (雙視角風險評估). Structurally
    parallel to OllamaClassificationProvider (002) — see design.md."""

    def __init__(self, settings: LLMSettings) -> None:
        self.model_id = settings.ollama_model
        chat = ChatOllama(
            model=settings.ollama_model,
            base_url=str(settings.ollama_base_url),
            timeout=settings.request_timeout_seconds,
        )
        self._structured_chat = chat.with_structured_output(RiskAssessmentResult)

    def assess_risk(self, request: RiskAssessmentRequest) -> RiskAssessmentResult:
        human_prompt = (
            f"clause_id: {request.clause_id}\n"
            f"clause_type: {request.clause_type.value}\n"
            f"條款原文：\n{request.original_text}\n\n"
            f"風險規則主題：{request.rule_topic}\n"
            f"風險說明：{request.rule_risk_explanation}\n"
            f"審閱問題：{'; '.join(request.rule_review_questions)}\n"
            f"建議範本：{request.rule_suggestion_template}"
        )
        try:
            result = self._structured_chat.invoke(
                [("system", _SYSTEM_PROMPT), ("human", human_prompt)]
            )
        except Exception as exc:  # noqa: BLE001 — classified by raise_mapped_llm_exception
            raise_mapped_llm_exception(
                exc, logger=logger, log_extra={"clause_id": request.clause_id, "rule_id": request.rule_id}
            )

        if not isinstance(result, RiskAssessmentResult):
            raise LLMOutputInvalidError()

        return result
