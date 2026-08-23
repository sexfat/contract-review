from io import BytesIO

import pytest
from docx import Document
from docx.oxml.ns import qn

from app.domain.errors import InvalidDocxError, TrackedChangesNotSupportedError
from app.infrastructure.docx.block_reader import (
    assert_no_tracked_changes,
    open_docx,
    read_source_blocks,
)

FIXTURES_DIR = (
    __import__("pathlib").Path(__file__).resolve().parents[3]
    / "specs"
    / "001-docx-clause-extraction"
    / "fixtures"
)


def _docx_bytes(document: Document) -> bytes:
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_open_docx_rejects_garbage_bytes():
    with pytest.raises(InvalidDocxError):
        open_docx(b"not a docx file at all")


def test_reads_paragraphs_and_table_cells_in_document_order():
    content = (FIXTURES_DIR / "payment-table.docx").read_bytes()
    docx = open_docx(content)
    blocks = read_source_blocks(docx)

    kinds = [b.kind for b in blocks]
    assert "paragraph" in kinds
    assert "table_cell" in kinds

    table_block_indices = [i for i, b in enumerate(blocks) if b.kind == "table_cell"]
    heading_index = next(i for i, b in enumerate(blocks) if "付款里程碑" in b.text)
    assert heading_index < table_block_indices[0]

    first_row_cells = [b.text for b in blocks if b.table_ref and b.table_ref.startswith("t-0001-r02-")]
    assert first_row_cells == ["第一期", "簽約日", "百分之三十"]


def test_order_is_sequential_starting_at_zero():
    content = (FIXTURES_DIR / "normal-numbering.docx").read_bytes()
    docx = open_docx(content)
    blocks = read_source_blocks(docx)
    assert [b.order for b in blocks] == list(range(len(blocks)))


def test_detects_tracked_changes():
    document = Document()
    paragraph = document.add_paragraph("第一條　工作範圍")

    ins = paragraph._p.makeelement(qn("w:ins"), {})
    paragraph._p.append(ins)

    docx = open_docx(_docx_bytes(document))
    with pytest.raises(TrackedChangesNotSupportedError):
        assert_no_tracked_changes(docx)


def test_clean_document_passes_tracked_changes_check():
    content = (FIXTURES_DIR / "normal-numbering.docx").read_bytes()
    docx = open_docx(content)
    assert_no_tracked_changes(docx)
