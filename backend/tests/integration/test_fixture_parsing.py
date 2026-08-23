from pathlib import Path

from app.domain.services.clause_splitter import split_into_clauses
from app.infrastructure.docx.block_reader import compute_checksum, open_docx, read_source_blocks

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "specs" / "001-docx-clause-extraction" / "fixtures"


def _parse(filename: str):
    content = (FIXTURES_DIR / filename).read_bytes()
    checksum = compute_checksum(content)
    docx = open_docx(content)
    blocks = read_source_blocks(docx)
    return split_into_clauses(blocks, checksum), content


def test_normal_numbering_has_at_least_three_main_clauses():
    clauses, _ = _parse("normal-numbering.docx")
    main_clauses = [c for c in clauses if c.location.article_no]
    assert len(main_clauses) >= 3
    assert {c.location.article_no for c in main_clauses} >= {"第一條", "第二條", "第三條"}


def test_mixed_numbering_preserves_preamble_as_unstructured():
    clauses, _ = _parse("mixed-numbering.docx")
    unstructured = [c for c in clauses if c.clause_id.startswith("unstructured-")]
    assert len(unstructured) == 1
    assert "前言" in unstructured[0].original_text
    assert "名詞定義" in unstructured[0].original_text

    main_clauses = [c for c in clauses if c.location.article_no]
    assert len(main_clauses) == 3


def test_payment_table_cells_are_present_in_output_text():
    clauses, _ = _parse("payment-table.docx")
    joined_text = "\n".join(c.original_text for c in clauses)
    for expected_cell in ["第一期", "簽約日", "百分之三十", "第二期", "系統驗收合格日", "百分之四十"]:
        assert expected_cell in joined_text

    table_clauses = [c for c in clauses if c.location.table_refs]
    assert table_clauses
    for clause in table_clauses:
        assert clause.location.article_no is not None


def test_reparsing_same_fixture_yields_stable_ids_and_order():
    first, content = _parse("normal-numbering.docx")
    checksum = compute_checksum(content)
    docx = open_docx(content)
    blocks = read_source_blocks(docx)
    second = split_into_clauses(blocks, checksum)

    assert [c.clause_id for c in first] == [c.clause_id for c in second]
    assert [c.location.source_start_index for c in first] == [
        c.location.source_start_index for c in second
    ]
