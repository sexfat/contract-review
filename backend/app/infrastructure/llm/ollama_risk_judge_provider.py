from __future__ import annotations

import logging

from langchain_ollama import ChatOllama

from app.domain.errors import LLMOutputInvalidError
from app.domain.schemas.judge import JudgeRequest, JudgeResult
from app.infrastructure.llm.config import LLMSettings
from app.infrastructure.llm.exception_mapping import raise_mapped_llm_exception

logger = logging.getLogger("contract_review.llm")

_SYSTEM_PROMPT = (
    "你是軟體開發合約風險審閱結果的複核員（judge）。你會收到：條款原文、一筆已產生的雙視角風險評估"
    "（風險等級、疑慮說明、建議、引用的原文片段），以及（可能有）檢索到的法規依據。"
    "請依下列四項逐一檢查，任一項不通過就整體判定不通過：\n"
    "1. evidence 的每一則引用是否確實存在於條款原文，且沒有斷章取義、扭曲原意。\n"
    "2. concern／suggestion 的風險描述是否超出條款原文與檢索到的法規依據所能支持的範圍（不得臆測原文未提及"
    "的事實）。\n"
    "3. risk_for_client 與 risk_for_vendor 的判斷是否互相矛盾（例如理由邏輯上不可能同時成立）。\n"
    "4. concern／suggestion 的措辭是否構成不當法律結論（斷言式語氣，例如暗示「一定違法」「必然無效」等，即"
    "使沒有使用黑名單字面詞也算）。\n"
    "只根據提供的內容判斷，不得引入外部知識或臆造原文未提及的事實。\n"
    "請只輸出一個 JSON 物件，格式完全比照以下範例，欄位名稱與型別必須一致：\n"
    '{"passed": true, "reason": "四項檢查皆通過"}\n'
    "或\n"
    '{"passed": false, "reason": "具體指出哪一項不通過及原因"}\n'
    "不要輸出其他任何文字、標題或說明。"
)


class OllamaRiskJudgeProvider:
    """Infrastructure adapter for judge gate (任務 C). Structurally parallel
    to OllamaRiskAssessmentProvider — see
    specs/005-rag-and-judge-gate/design.md."""

    def __init__(self, settings: LLMSettings) -> None:
        self.model_id = settings.ollama_model
        chat = ChatOllama(
            model=settings.ollama_model,
            base_url=str(settings.ollama_base_url),
            timeout=settings.request_timeout_seconds,
        )
        self._structured_chat = chat.with_structured_output(JudgeResult)

    def judge(self, request: JudgeRequest) -> JudgeResult:
        sources_text = "\n".join(
            f"- {s.title}：{s.content}" for s in request.retrieved_sources
        ) or "（無檢索到的法規依據）"
        evidence_text = "\n".join(f"- {e.quote}（{e.rationale}）" for e in request.evidence)
        human_prompt = (
            f"條款原文：\n{request.clause_original_text}\n\n"
            f"風險評估結果：\n"
            f"甲方風險：{request.risk_for_client.value}\n"
            f"乙方風險：{request.risk_for_vendor.value}\n"
            f"疑慮：{request.concern}\n"
            f"建議：{request.suggestion}\n"
            f"引用原文：\n{evidence_text}\n\n"
            f"檢索到的法規依據：\n{sources_text}"
        )
        try:
            result = self._structured_chat.invoke(
                [("system", _SYSTEM_PROMPT), ("human", human_prompt)]
            )
        except Exception as exc:  # noqa: BLE001 — classified by raise_mapped_llm_exception
            raise_mapped_llm_exception(exc, logger=logger, log_extra={})

        if not isinstance(result, JudgeResult):
            raise LLMOutputInvalidError()

        return result
