from app.domain.schemas.source_block import SourceBlock
from app.domain.services.clause_splitter import split_into_clauses

CHECKSUM = "deadbeef"


def block(order: int, text: str, kind: str = "paragraph", table_ref: str | None = None) -> SourceBlock:
    block_id = table_ref if table_ref else f"p-{order:04d}"
    return SourceBlock(block_id=block_id, order=order, kind=kind, text=text, table_ref=table_ref)


def test_preamble_without_article_becomes_unstructured():
    blocks = [
        block(0, "前言：本合約規範雙方權利義務。"),
        block(1, "第一條　工作範圍"),
        block(2, "乙方應完成系統開發。"),
    ]
    clauses = split_into_clauses(blocks, CHECKSUM)

    assert len(clauses) == 2
    assert clauses[0].clause_id.startswith("unstructured-")
    assert "前言" in clauses[0].original_text
    assert clauses[1].location.article_no == "第一條"
    assert "乙方應完成系統開發" in clauses[1].original_text


def test_sub_items_absorbed_into_current_main_clause():
    blocks = [
        block(0, "第一條　工作範圍"),
        block(1, "一、系統應包含訂單管理功能。"),
        block(2, "（一）逾期未回覆者，視為驗收合格。"),
        block(3, "第二條　驗收"),
        block(4, "甲方應於十日內完成驗收。"),
    ]
    clauses = split_into_clauses(blocks, CHECKSUM)

    assert len(clauses) == 2
    assert "一、系統應包含訂單管理功能" in clauses[0].original_text
    assert "（一）逾期未回覆者" in clauses[0].original_text
    assert clauses[1].location.article_no == "第二條"


def test_recognizes_arabic_and_spaced_article_numbers():
    blocks = [
        block(0, "第 1 條　定義"),
        block(1, "本合約用語定義如下。"),
        block(2, "第2條　工作範圍"),
        block(3, "乙方應完成開發工作。"),
    ]
    clauses = split_into_clauses(blocks, CHECKSUM)

    assert [c.location.article_no for c in clauses] == ["第 1 條", "第2條"]


def test_clause_id_is_deterministic_across_runs():
    blocks = [
        block(0, "第一條　工作範圍"),
        block(1, "乙方應完成系統開發。"),
    ]
    first = split_into_clauses(blocks, CHECKSUM)
    second = split_into_clauses(blocks, CHECKSUM)

    assert [c.clause_id for c in first] == [c.clause_id for c in second]


def test_table_cell_populates_table_refs_and_not_paragraph_ids():
    blocks = [
        block(0, "第二條　付款里程碑"),
        block(1, "百分之三十", kind="table_cell", table_ref="t-0001-r02-c03"),
    ]
    clauses = split_into_clauses(blocks, CHECKSUM)

    assert clauses[0].location.table_refs == ["t-0001-r02-c03"]
    assert "t-0001-r02-c03" not in clauses[0].location.paragraph_ids


def test_document_ending_mid_clause_is_flushed():
    blocks = [
        block(0, "第一條　工作範圍"),
        block(1, "乙方應完成系統開發。"),
    ]
    clauses = split_into_clauses(blocks, CHECKSUM)
    assert len(clauses) == 1
    assert clauses[0].location.source_end_index == 1
