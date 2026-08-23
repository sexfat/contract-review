# 002：條款分類與白話摘要

## Goal

對已解析（`parsed`）的合約條款（[001-docx-clause-extraction](../001-docx-clause-extraction/spec.md) 的輸出），
透過 LLM 為每個 clause 產生 `ClauseType` 分類與白話摘要，並以 Pydantic 驗證輸出，作為後續雙視角風險審閱
（003）的輸入。本 feature 對應 `docs/DEVELOPMENT_SPEC.md` 的 M2 里程碑與「任務 A：條款分類與白話摘要」。

## In scope

- 定義並實作 `app/application/ports/llm_provider.py`（`LLMProvider` port），與一個 Ollama Cloud adapter。
- 對每個 `ParsedClause` 呼叫 LLM，輸出 `clause_type`（完整 `ClauseType` enum）與 `plain_summary`、`confidence`。
- Pydantic schema 驗證 LLM 輸出；解析失敗時最多重試一次；仍失敗則標記該條款「無法可靠分析」。
- 白話摘要的機讀防呆檢查：摘要中出現的金額／日期字串必須能在該條款 `original_text` 中找到，否則視為驗證失敗。
- 新增 `POST /api/documents/{document_id}/classify` API 與擴充 `GET /api/documents/{document_id}/clauses` 回應。
- LLM provider 設定（model、base URL、API key）一律由環境變數讀取，不寫死在程式碼。
- 至少 3 份 fixture（沿用 001 的三份 DOCX）的分類結果人工覆核記錄。

## Out of scope

- 雙視角風險評估、風險規則庫、RAG 檢索、judge gate（留待 003 / 005）。
- 前端顯示（留待 004）。
- 非同步任務佇列；MVP 可同步處理，但需保留可改背景任務的介面（沿用 001 的 `status` 欄位模式）。
- 對 `original_text` 本身做任何改寫、修正錯字或格式調整（001 已保證原文不可變）。
- 多語言／多法域；僅處理繁體中文。

## User scenarios

### 正常分類

Given 一份狀態為 `parsed` 的文件  
When 呼叫 `POST /api/documents/{document_id}/classify`  
Then 系統為每個 clause 產生受驗證的 `clause_type`、`plain_summary`、`confidence`，並可透過
`GET /api/documents/{document_id}/clauses` 取得完整結果。

### LLM 輸出驗證失敗後重試成功

Given 某條款首次 LLM 回應無法通過 Pydantic 驗證或摘要防呆檢查  
When 系統依規則重試一次  
Then 若重試通過驗證，採用重試結果；不得沿用第一次的無效輸出。

### 兩次重試皆失敗

Given 某條款兩次 LLM 呼叫（含重試）皆無法通過驗證  
When 分類流程處理該條款  
Then 該條款輸出 `clause_type=other`、`confidence=0`，`plain_summary` 明確標示「無法可靠分析」，且不得包含臆測內容；
分類流程對其餘條款繼續執行，不因單一條款失敗而中止整份文件。

### LLM provider 整體無法連線

Given LLM provider（Ollama Cloud）連線逾時或回傳錯誤，導致所有條款皆無法處理  
When 呼叫 `POST /api/documents/{document_id}/classify`  
Then 文件狀態標記為 `failed`，錯誤碼為 `LLM_PROVIDER_UNAVAILABLE`，不寫入任何猜測性分類結果。

## Functional requirements

1. 分類只能在文件狀態為 `parsed` 或 `classified`（重新分類）時觸發；其餘狀態回傳 `DOCUMENT_NOT_READY`。
2. 每次呼叫 LLM 僅提供單一 clause 的 `original_text` 及必要的 enum／schema 說明；不得夾帶其他條款原文或使用者其他文件內容。
3. LLM 輸出必須符合固定 JSON Schema（`clause_id`、`clause_type`、`plain_summary`、`confidence`）；後端一律以 Pydantic 再驗證一次，不信任 LLM 自稱的格式正確性。
4. `plain_summary` 不得包含原文未出現的金額、日期、條號或義務描述；至少對金額與日期樣式做子字串比對防呆（正規表示式擷取 + 原文比對）。
5. `confidence` 需為模型回傳或系統依驗證結果（如重試次數、防呆失敗）調整後的 0–1 浮點數。
6. `clause_id` 必須沿用 001 產生的既有 ID，不可由本 feature 重新產生或變更。
7. LLM provider 相關設定（`OLLAMA_API_KEY`、`OLLAMA_BASE_URL`、`OLLAMA_MODEL`）一律從環境變數讀取；預設模型為
   `gemma4:31b-cloud`（見 `.env.example`）。
8. LLM 呼叫、prompt 組裝與 SDK（`langchain_ollama` 或其他）皆封裝於 `app/infrastructure/llm/` 的單一 adapter；
   `application`／`domain` 層不得直接 import LLM SDK。
9. 單一條款分類失敗（重試後仍失敗）不得中止其餘條款處理；LLM provider 完全無法連線時整份文件標記 `failed`。
10. 每份 `ExtractedClause` 須記錄使用的 `model_id`（供後續 debug／reproducibility），但不可記錄完整 prompt 內容於一般 log。

## API contract

### `POST /api/documents/{document_id}/classify`

- Response `202`：`{document_id, status: "classifying"}`（本機 MVP 可同步完成，但 response contract 不變，比照 001 的
  `/parse` 端點慣例）。
- Response `409`：文件尚未解析完成，`error_code=DOCUMENT_NOT_READY`。
- Response `404`：文件不存在。
- Response `502`：LLM provider 無法連線或整體失敗，`error_code=LLM_PROVIDER_UNAVAILABLE`。

### `GET /api/documents/{document_id}/clauses`（擴充）

- 文件狀態為 `parsed` 時，行為與 001 相同（`clause_type` 皆為 `other`，無 `plain_summary`／`confidence`）。
- 文件狀態為 `classified` 時，回傳每個 clause 完整的 `clause_type`（完整 enum 值）、`plain_summary`、`confidence`。
- 確切 response schema 差異（新增欄位是否為 optional）於 design.md 與新的
  `contracts/extracted_clause.schema.json` 中定義。

## Failure handling

| Error code | 對使用者訊息 |
|---|---|
| `DOCUMENT_NOT_READY` | 文件尚未完成解析，請稍後再試。 |
| `LLM_PROVIDER_UNAVAILABLE` | 分析服務暫時無法使用，請稍後再試。 |
| `CLASSIFICATION_FAILED` | 部分條款無法可靠分析，已標示待人工確認。（非阻斷性，隨結果一併回傳） |

錯誤 log 僅記錄 `document_id`、`clause_id`、error code 與技術堆疊；不得記錄 `original_text`、`plain_summary` 或完整
prompt 內容。

## Acceptance criteria

1. 對 001 的三份 fixture 執行分類後，每個 clause 皆有受 Pydantic 驗證的 `clause_type`（非固定 `other`，除非
   LLM 判斷確實無法分類）與 `plain_summary`。
2. 人工覆核至少 10 個 clause 的分類結果與摘要，確認摘要未包含原文未提及的金額／日期／義務。
3. 針對「重試後仍失敗」情境有自動化測試（以 fake/stub `LLMProvider` 模擬），確認輸出
   `clause_type=other`、`confidence=0` 且不中止其餘條款。
4. 針對「LLM provider 整體無法連線」有自動化測試，確認文件標記為 `failed` 且無殘留猜測性資料。
5. `clause_id` 在分類前後保持不變（以 001 的既有測試延伸驗證）。
6. 無任何測試快照、log 或錯誤訊息包含合約原文或摘要全文。
7. Pydantic contract validation、unit、integration 與 API contract tests 全部通過。

## Non-functional requirements

- 單一 clause 的 LLM 呼叫（含一次重試）應在 30 秒內完成或逾時失敗，避免整份文件卡死。
- LLM adapter 需可替換（interface-based），未來若換模型或供應商不得更動 application 層呼叫方式。
- 所有 LLM 呼叫必須可由設定關閉重試次數或改用 fake provider，供測試與 CI 使用，不依賴真實外部服務。
- API response 沿用 001 的慣例：繁中可讀訊息搭配英文 machine error code。

## 已確認決策

1. **`GET /clauses` 為同一端點的受控演進**：不建立新版路徑；回應完整度依文件目前 `status` 而定（`parsed` 時仍為
   001 的 `other`-only 形狀；`classified` 時回傳完整 `clause_type`／`plain_summary`／`confidence`）。舊有 001
   contract 測試（`status=parsed` 情境）維持有效，不視為 breaking change。
2. **`DocumentStatus` 新增 `classifying`／`classified`**，使 002 可獨立於 003（風險評估）之外完成驗收；
   `completed` 狀態留待 003 導入 `ReviewReport` 後才使用。
3. **摘要金額／日期防呆範圍**：以正規表示式擷取（a）阿拉伯數字金額（含千分位、`NT$`、`新臺幣`、`元`、`%`、
   `百分之` 等常見標記）、（b）中文數字金額（一～九＋十百千萬＋元）、（c）常見日期樣式（`YYYY年MM月DD日`、
   `民國╱西元` 年份、`YYYY/MM/DD`）。逐一比對是否為該 clause `original_text` 的子字串；比對失敗即視為驗證失敗，
   觸發重試或標記無法可靠分析。合約編號、當事人名稱等其餘實體暫不納入本階段防呆，留待後續 feature 視需要擴充。
4. **`POST /classify` 為整份文件的（重）分類操作**，會重新分類該文件所有 clause；不在本 feature 提供
   「僅重跑單一 clause」的端點，此需求留待有實際使用情境時再開新 feature。
