# 001：DOCX 條款抽取

## Goal

使用者可上傳一份繁中 `.docx` 軟體開發合約，取得保留原文順序、條號與來源位置的結構化條款清單，作為後續 LLM 分類與風險審閱的唯一輸入。

## In scope

- 驗證 `.docx` 副檔名、OOXML MIME type、檔案大小與可開啟性。
- 讀取文件正文段落、標題、清單與表格中的文字，並依文件實際順序串接。
- 對常見繁中條號進行階層辨識並切出 clause。
- 為每個 clause 提供穩定 `clause_id`、原文、段落／表格位置與預設 `other` 類型。
- 以 REST API 回傳解析狀態與條款 JSON。
- 建立正常條號、混合條號、表格條款三份 fixture 與測試。

## Out of scope

- LLM、摘要、條款分類、風險規則、RAG、judge。
- PDF、OCR、`.doc`、含 Track Changes 的實際內容合併。
- 使用者帳號、多租戶、雲端儲存、資料庫持久化（MVP 可先使用本機檔案與 in-memory repository）。

## User scenarios

### 正常解析

Given 使用者選擇可開啟的 `.docx` 合約  
When 上傳後要求解析  
Then 系統回傳完成狀態與依原始順序排列的 clauses。

### 無法識別的段落

Given 合約中有沒有條號的前言或格式不規則文字  
When 系統解析文件  
Then 文字仍須出現在一個 `unstructured-*` clause，不可遺失。

### 含表格條款

Given 合約包含付款里程碑表格  
When 系統解析文件  
Then 每個非空儲存格的文字必須能由輸出 clauses 找到，且 location 含 table reference。

## Functional requirements

1. 上傳只接受 `.docx`；拒絕 `.doc`、PDF、ZIP 與偽裝副檔名。
2. 文件中的 block element 必須依 OOXML document body 的原始順序讀取，包含 paragraph 與 table。
3. 支援主條模式：`第壹條`、`第一條`、`第 1 條`。
4. 支援子項模式：`壹、`、`一、`、`1.`、`1、`、`（一）`、`(一)`、`（1）`、`(1)`。
5. 主條開始後，後續內容歸屬該主條，直到下一個同階或更高階條號開始。
6. 每個 clause 均使用 `other` 作為此階段預設 `clause_type`。
7. `original_text` 保留原字，不可由 parser 修正錯字、數字、日期或標點；允許去除純格式空白。
8. `clause_id` 由文件 checksum + 起始位置衍生，不可使用隨機 UUID；同檔重跑必須相同。
9. 偵測 Track Changes XML 時回傳 `TRACKED_CHANGES_NOT_SUPPORTED`，不輸出可能混合的文字。

## API contract

### `POST /api/documents`

- Request：`multipart/form-data`，欄位名 `file`。
- Response `201`：`document_id`、`status=uploaded`。
- Response `400`：格式或可讀性問題。

### `POST /api/documents/{document_id}/parse`

- Response `202`：`status=parsing`；本機 MVP 可立即完成，但 response contract 不變。

### `GET /api/documents/{document_id}/clauses`

- `parsed` 時回傳 `200` + `ClauseListResponse`。
- `parsing` 時回傳 `409` + `DOCUMENT_NOT_READY`。
- 不存在時回傳 `404`。

完整 schema 見 [contracts/clause.schema.json](./contracts/clause.schema.json)。

## Failure handling

| Error code | 對使用者訊息 |
|---|---|
| `UNSUPPORTED_FILE_TYPE` | 請上傳 `.docx` 格式的 Word 文件。 |
| `FILE_TOO_LARGE` | 檔案超過系統允許大小。 |
| `INVALID_DOCX` | 文件無法讀取，請確認檔案未毀損。 |
| `TRACKED_CHANGES_NOT_SUPPORTED` | 文件含修訂追蹤，請先接受或拒絕修訂後重新上傳。 |
| `DOCUMENT_NOT_READY` | 文件仍在解析，請稍後再試。 |

錯誤 log 僅記錄 `document_id`、error code 與技術堆疊；不得輸出條款文字或檔案內容。

## Acceptance criteria

1. 三份 fixture 皆能完成解析，且輸出順序一致。
2. 表格 fixture 的每個非空儲存格文字均在至少一個 `original_text` 出現。
3. 正常條號 fixture 至少能辨識三個主條及其 article number。
4. 混合條號 fixture 的無條號前言不遺失。
5. 對同一檔案解析兩次，所有 `clause_id`、順序與 location 相同。
6. Pydantic contract validation、單元測試與整合測試全部通過。

## Non-functional requirements

- 10 MB 以下、100 個 block element 的本機文件應在 5 秒內完成解析（不含上傳網路時間）。
- 解析失敗不應造成 process crash 或建立部分成功的正式結果。
- 所有 API response 以繁中可讀訊息搭配英文 machine error code。

## 驗收紀錄

- 實作位置：`backend/app`（layered per SDD_ARCHITECTURE.md）；測試位置：`backend/tests`。
- `uv run pytest`：27 passed（unit / integration / API contract，含 `clause.schema.json` 驗證）。
- 三份 fixture（`normal-numbering.docx`、`mixed-numbering.docx`、`payment-table.docx`）已產生於
  `specs/001-docx-clause-extraction/fixtures/`，經人工檢視條款切分結果符合預期（見
  `backend/README.md` 的重新產生指令）。
- Acceptance criteria 1–6：以上述測試涵蓋；`clause_id` 穩定性另有 API 層測試（同一 fixture 上傳兩次比對
  `clause_id` 序列）。
- 已請 Codex 對照本 spec / design.md / DEVELOPMENT_SPEC.md 做獨立驗證；發現並修正：
  - `POST /parse` 回應改為固定回傳 `status=parsing`（符合 202 契約字面定義，即使本機 MVP 同步完成）。
  - 上傳流程新增 MIME type 白名單檢查與 `open_docx` 可讀性驗證，不再等到 parse 階段才發現壞檔。
  - Track Changes 偵測擴充涵蓋 `w:moveFrom`/`w:moveTo`/`w:pPrChange` 等修訂標記，不只 `w:ins`/`w:del`。
  - `clause_id` 雜湊輸入改為與 design.md 完全一致的字串串接（原實作多了分隔符號）。
  - 文件解析失敗後查詢 clauses，改回傳該 error_code 對應的正確繁中訊息，而非泛用訊息。
  - 錯誤 log 加入 `exc_info`（技術堆疊），仍不含合約原文。

## 已知限制

- `clause_type` 於此階段固定為 `other`，分類與摘要留待 002-llm-clause-classification。
- Repository／FileStorage 為 in-memory + 本機檔案系統 adapter，尚未接 PostgreSQL（見 design.md 決策）。
- 子項條號僅併入所屬主條原文，不切出獨立 child chunk（RAG feature 再處理）。
- 尚未實作前端左欄顯示；`tasks.md` 未列此項目，留待 004-vue-review-workbench。
- 主條 regex（`第X條`）僅比對段落開頭，理論上仍可能誤判以「第一條」開頭但實為一般敘述的句子（例如
  「第一條款相關規定」）；目前三份 fixture 未觸發此情況，列為已知限制而非阻斷性 bug。
