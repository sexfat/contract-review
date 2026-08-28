from datetime import date

from app.domain.schemas.clause_type import ClauseType
from app.domain.schemas.legal_source import LegalSource
from app.domain.schemas.retrieval import RetrievalQuery
from app.domain.services.knowledge_ranking import rank_by_similarity, resolve_retrieved_knowledge


def _source(
    knowledge_id: str,
    *,
    parent_id: str | None = None,
    clause_type: ClauseType | None = ClauseType.WARRANTY,
    jurisdiction: str = "TW",
    status: str = "reviewed",
    title: str | None = None,
    content: str | None = None,
) -> LegalSource:
    return LegalSource(
        knowledge_id=knowledge_id,
        corpus="legal_sources",
        parent_id=parent_id,
        title=title or f"{knowledge_id} 標題",
        source_title="測試法規",
        content=content or f"{knowledge_id} 原文",
        clause_type=clause_type,
        jurisdiction=jurisdiction,
        source_url=None,
        effective_date=None,
        version=1,
        status=status,
        reviewed_by="tester" if status == "reviewed" else None,
        updated_at=date(2026, 8, 28),
    )


def _query(**overrides) -> RetrievalQuery:
    defaults = dict(clause_type=ClauseType.WARRANTY, query_text="條款原文", jurisdiction="TW", top_k=5)
    defaults.update(overrides)
    return RetrievalQuery(**defaults)


def test_filters_out_draft_status():
    reviewed = _source("kid-reviewed", status="reviewed")
    draft = _source("kid-draft", status="draft")
    result = rank_by_similarity([1.0, 0.0], [(reviewed, [1.0, 0.0]), (draft, [1.0, 0.0])], _query())
    assert [s.knowledge_id for s in result] == ["kid-reviewed"]


def test_filters_out_mismatched_jurisdiction():
    tw = _source("kid-tw", jurisdiction="TW")
    us = _source("kid-us", jurisdiction="US")
    result = rank_by_similarity([1.0, 0.0], [(tw, [1.0, 0.0]), (us, [1.0, 0.0])], _query(jurisdiction="TW"))
    assert [s.knowledge_id for s in result] == ["kid-tw"]


def test_null_clause_type_matches_any_query_clause_type():
    broad = _source("kid-broad", clause_type=None)
    result = rank_by_similarity([1.0, 0.0], [(broad, [1.0, 0.0])], _query(clause_type=ClauseType.PAYMENT))
    assert [s.knowledge_id for s in result] == ["kid-broad"]


def test_mismatched_clause_type_excluded():
    warranty = _source("kid-warranty", clause_type=ClauseType.WARRANTY)
    result = rank_by_similarity([1.0, 0.0], [(warranty, [1.0, 0.0])], _query(clause_type=ClauseType.PAYMENT))
    assert result == []


def test_ranks_by_cosine_similarity_descending():
    close = _source("kid-close")
    far = _source("kid-far")
    # query_vector = [1, 0]; close is parallel (sim=1), far is orthogonal (sim=0)
    result = rank_by_similarity([1.0, 0.0], [(far, [0.0, 1.0]), (close, [1.0, 0.0])], _query())
    assert [s.knowledge_id for s in result] == ["kid-close", "kid-far"]


def test_top_k_truncates():
    sources = [(_source(f"kid-{i}"), [1.0, 0.0]) for i in range(10)]
    result = rank_by_similarity([1.0, 0.0], sources, _query(top_k=3))
    assert len(result) == 3


def test_resolve_retrieved_knowledge_without_parent_returns_self():
    source = _source("kid-standalone", parent_id=None)
    resolved = resolve_retrieved_knowledge(source, {"kid-standalone": source})
    assert resolved.knowledge_id == "kid-standalone"
    assert resolved.parent_id is None
    assert resolved.content == source.content


def test_resolve_retrieved_knowledge_with_parent_expands_to_parent_content():
    parent = _source("civil-227", parent_id=None, title="民法第227條", content="完整條文")
    child = _source("civil-227-2", parent_id="civil-227", title="民法第227條第2項", content="子片段")
    resolved = resolve_retrieved_knowledge(child, {"civil-227": parent, "civil-227-2": child})
    assert resolved.knowledge_id == "civil-227-2"  # 仍記錄實際命中的 child ID
    assert resolved.parent_id == "civil-227"
    assert resolved.content == "完整條文"  # 但內容展開為 parent
    assert resolved.title == "民法第227條"
