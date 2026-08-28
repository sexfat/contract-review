from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.domain.schemas.clause_type import ClauseType


class RetrievalQuery(BaseModel):
    """SDD_ARCHITECTURE.md §7 RAG 契約，欄位不可自行增減。"""

    clause_type: ClauseType
    query_text: str = Field(min_length=1)
    jurisdiction: str = "TW"
    top_k: int = Field(default=5, ge=1)


class RetrievedKnowledge(BaseModel):
    """SDD_ARCHITECTURE.md §7 RAG 契約。`knowledge_id` 是實際命中的條目（可能是 child），
    但 `content` 等展示欄位可能已依 chunking 政策展開為 parent 完整原文——
    見 app/domain/services/knowledge_ranking.py 的 resolve_retrieved_knowledge。"""

    knowledge_id: str = Field(min_length=1)
    parent_id: str | None
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source_url: str | None
    effective_date: date | None
    version: int
