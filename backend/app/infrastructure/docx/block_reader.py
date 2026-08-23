from __future__ import annotations

import hashlib
import zipfile
from io import BytesIO

from docx import Document as OpenDocx
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.domain.errors import InvalidDocxError, TrackedChangesNotSupportedError
from app.domain.schemas.source_block import SourceBlock

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024

_TRACK_CHANGE_TAGS = {
    qn(tag)
    for tag in (
        "w:ins",
        "w:del",
        "w:moveFrom",
        "w:moveTo",
        "w:pPrChange",
        "w:rPrChange",
        "w:tblPrChange",
        "w:trPrChange",
        "w:tcPrChange",
        "w:sectPrChange",
        "w:numberingChange",
    )
}


def compute_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def open_docx(content: bytes) -> OpenDocx:
    try:
        return OpenDocx(BytesIO(content))
    except (zipfile.BadZipFile, KeyError, ValueError, OSError) as exc:
        raise InvalidDocxError() from exc


def assert_no_tracked_changes(document: OpenDocx) -> None:
    body = document.element.body
    for element in body.iter():
        if element.tag in _TRACK_CHANGE_TAGS:
            raise TrackedChangesNotSupportedError()


def read_source_blocks(document: OpenDocx) -> list[SourceBlock]:
    """Read paragraph and table-cell text in original OOXML body order.

    Empty (whitespace-only) blocks are dropped; `order` is assigned only to
    blocks that are kept, matching how ClauseLocation indices are used.
    """
    blocks: list[SourceBlock] = []
    body = document.element.body
    paragraph_counter = 0
    table_counter = 0

    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            paragraph_counter += 1
            paragraph = Paragraph(child, document)
            text = paragraph.text.strip()
            if not text:
                continue
            block_id = f"p-{paragraph_counter:04d}"
            style_name = paragraph.style.name if paragraph.style is not None else None
            blocks.append(
                SourceBlock(
                    block_id=block_id,
                    order=len(blocks),
                    kind="paragraph",
                    text=text,
                    style_name=style_name,
                )
            )
        elif child.tag == qn("w:tbl"):
            table_counter += 1
            table = Table(child, document)
            for row_idx, row in enumerate(table.rows, start=1):
                for col_idx, cell in enumerate(row.cells, start=1):
                    text = cell.text.strip()
                    if not text:
                        continue
                    table_ref = f"t-{table_counter:04d}-r{row_idx:02d}-c{col_idx:02d}"
                    blocks.append(
                        SourceBlock(
                            block_id=table_ref,
                            order=len(blocks),
                            kind="table_cell",
                            text=text,
                            style_name=None,
                            table_ref=table_ref,
                        )
                    )

    return blocks
