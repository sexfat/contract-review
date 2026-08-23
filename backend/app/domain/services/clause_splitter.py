from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from app.domain.schemas.clause import ClauseLocation, ParsedClause
from app.domain.schemas.source_block import SourceBlock

# Main-article markers only: 第壹條 / 第一條 / 第 1 條 / 第1條.
# Sub-item markers (壹、一、1. 1、 （一）(一)（1）(1)) are intentionally NOT
# used to start new clauses in M1 — design.md: sub-items stay attached to the
# current main clause; they may become RAG child chunks in a later feature.
_ARTICLE_NUMERAL = r"[壹貳參肆伍陸柒捌玖拾佰仟百千萬〇零一二三四五六七八九十0-9]+"
ARTICLE_RE = re.compile(rf"^第\s*({_ARTICLE_NUMERAL})\s*條")

UNSTRUCTURED_ID_PREFIX = "unstructured"


@dataclass
class _ClauseAccumulator:
    is_unstructured: bool
    start_block_id: str
    start_index: int
    article_no: str | None = None
    heading: str | None = None
    texts: list[str] = field(default_factory=list)
    paragraph_ids: list[str] = field(default_factory=list)
    table_refs: list[str] = field(default_factory=list)
    end_index: int = 0


def _clause_id(document_checksum: str, start_block_id: str, *, unstructured: bool) -> str:
    # design.md 切分演算法 step 7: clause_id = sha256(document_checksum + start_block_id)[:20]
    digest = hashlib.sha256((document_checksum + start_block_id).encode()).hexdigest()
    if unstructured:
        return f"{UNSTRUCTURED_ID_PREFIX}-{digest[:16]}"
    return digest[:20]


def _finalize(acc: _ClauseAccumulator, document_checksum: str) -> ParsedClause:
    original_text = "\n".join(acc.texts)
    location = ClauseLocation(
        article_no=acc.article_no,
        heading=acc.heading,
        source_start_index=acc.start_index,
        source_end_index=acc.end_index,
        paragraph_ids=acc.paragraph_ids,
        table_refs=acc.table_refs,
    )
    clause_id = _clause_id(document_checksum, acc.start_block_id, unstructured=acc.is_unstructured)
    return ParsedClause(
        clause_id=clause_id,
        clause_type="other",
        original_text=original_text,
        location=location,
    )


def _append_block(acc: _ClauseAccumulator, block: SourceBlock) -> None:
    acc.texts.append(block.text)
    acc.end_index = block.order
    if block.kind == "table_cell" and block.table_ref is not None:
        acc.table_refs.append(block.table_ref)
    else:
        acc.paragraph_ids.append(block.block_id)


def split_into_clauses(blocks: list[SourceBlock], document_checksum: str) -> list[ParsedClause]:
    """Split ordered source blocks into clauses per design.md's algorithm.

    A main-article marker starts a new parent clause. Everything else
    (including sub-item markers) is appended to whichever clause is
    currently open. Text before the first main-article marker is collected
    into a single `unstructured-*` clause so nothing is lost.
    """
    clauses: list[ParsedClause] = []
    current: _ClauseAccumulator | None = None

    for block in blocks:
        match = ARTICLE_RE.match(block.text)
        if match:
            if current is not None:
                clauses.append(_finalize(current, document_checksum))
            current = _ClauseAccumulator(
                is_unstructured=False,
                start_block_id=block.block_id,
                start_index=block.order,
                article_no=match.group(0).strip(),
                heading=block.text,
            )
            _append_block(current, block)
        else:
            if current is None:
                current = _ClauseAccumulator(
                    is_unstructured=True,
                    start_block_id=block.block_id,
                    start_index=block.order,
                )
            _append_block(current, block)

    if current is not None:
        clauses.append(_finalize(current, document_checksum))

    return clauses
