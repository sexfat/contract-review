# 001：DOCX 條款抽取技術設計

## 模組

```text
API route
  → UploadDocument command
  → FileStorage port
  → ParseDocument command
  → DocxBlockReader
  → ClauseSplitter
  → ClauseRepository port
  → ClauseListResponse
```

## 資料結構

```python
class SourceBlock(BaseModel):
    block_id: str                 # p-0001 / t-0003-r02-c01
    order: int
    kind: Literal["paragraph", "table_cell"]
    text: str
    style_name: str | None
    table_ref: str | None = None


class ParsedClause(BaseModel):
    clause_id: str
    clause_type: Literal["other"] = "other"
    original_text: str
    location: ClauseLocation
```

`DocxBlockReader` 以 `document.element.body.iterchildren()` 讀取 OOXML body，保持 paragraph 與 table 在原文件中的交錯順序。表格依 row / column 順序輸出非空 `table_cell` block。

## 切分演算法

1. 依序走訪 `SourceBlock`。
2. 使用 regex 偵測開頭條號及其 level。
3. 遇到主條時封存目前 clause，建立新的 parent clause。
4. 遇到子項時仍保留在當前主條 `original_text`；位置增加該 block。
5. 尚未遇到主條的文字，建立或附加至 `unstructured-001`。
6. 文件結尾封存最後一條。
7. `clause_id = sha256(document_checksum + start_block_id)[:20]`。

MVP 的 clause 不拆成 child chunks；後續 RAG feature 再以主條建立 parent-document / child-chunk 結構。

## 儲存介面

```python
class DocumentRepository(Protocol):
    def create(self, document: Document) -> Document: ...
    def get(self, document_id: str) -> Document | None: ...
    def set_status(self, document_id: str, status: DocumentStatus) -> None: ...


class ClauseRepository(Protocol):
    def replace_for_document(self, document_id: str, clauses: list[ParsedClause]) -> None: ...
    def list_for_document(self, document_id: str) -> list[ParsedClause]: ...
```

初期使用 filesystem + in-memory 實作；等 feature 006 再替換成 PostgreSQL adapter，不得更動 application command 的呼叫方式。

## 測試策略

- Unit：條號偵測、文檔順序、未結尾 clause、ID 穩定性。
- Integration：fixture `.docx` 解析後符合 JSON Schema。
- API contract：上傳、解析、查詢、錯誤 code。
- Regression：每個修復條號或表格 bug 時，都新增最小 fixture。

## 不確定事項與決策

- Word 樣式不能視為可靠語意；樣式僅用於輔助條號判斷。
- 表格的儲存格位置可精確追蹤，但在 MVP 前端只需呈現為條款文字，不處理單一 cell 高亮。
- DOCX comments 與 Track Changes 不納入；一旦偵測修訂，拒絕而非猜測採用版本。
