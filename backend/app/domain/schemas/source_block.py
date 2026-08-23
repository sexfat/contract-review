from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SourceBlock(BaseModel):
    """A single ordered unit of text read from the DOCX body.

    `block_id` uses `p-0001` for paragraphs and `t-0003-r02-c01` for table
    cells (table index, row index, column index), matching design.md.
    """

    block_id: str = Field(min_length=1)
    order: int = Field(ge=0)
    kind: Literal["paragraph", "table_cell"]
    text: str
    style_name: str | None = None
    table_ref: str | None = None
