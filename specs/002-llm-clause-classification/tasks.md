# 002：條款分類與白話摘要工作清單

## Domain

- [ ] 新增 `ClauseType` enum（`app/domain/schemas/clause_type.py`），值沿用 `docs/DEVELOPMENT_SPEC.md` §7。
- [ ] 新增 `ExtractedClause` schema（`app/domain/schemas/extracted_clause.py`），含 `requires_human_review`、`model_id`。
- [ ] 新增 `LLMClassificationRequest`／`LLMClassificationResult` schema（`app/domain/schemas/llm_classification.py`）。
- [ ] 新增 `LLMOutputInvalidError`、`LLMProviderUnavailableError`（`app/domain/errors.py`），並加入
      `error_for_code` 對照表。
- [ ] 實作 `SummaryGuard.find_ungrounded_amounts_and_dates`（`app/domain/services/summary_guard.py`）。
- [ ] `DocumentStatus` 新增 `CLASSIFYING`、`CLASSIFIED`（`app/domain/entities/document.py`）。

## Ports 與 Repository

- [ ] 新增 `LLMProvider` port（`app/application/ports/llm_provider.py`）。
- [ ] 新增 `ClauseClassificationRepository` port（`app/application/ports/clause_classification_repository.py`）。
- [ ] 實作 `InMemoryClauseClassificationRepository`（`app/infrastructure/repositories/memory_repository.py`）。

## LLM Provider Adapter

- [ ] `backend/pyproject.toml` 新增依賴：`langchain-ollama`、`python-dotenv`、`pydantic-settings`。
- [ ] 實作 `LLMSettings`（`app/infrastructure/llm/config.py`），讀取 `OLLAMA_API_KEY`／`OLLAMA_BASE_URL`／
      `OLLAMA_MODEL`；缺少 `OLLAMA_API_KEY` 時 fail fast。
- [ ] 實作 `OllamaClassificationProvider`（`app/infrastructure/llm/ollama_provider.py`）：組 prompt、逾時控制、
      JSON parse + Pydantic 驗證、例外分類（`LLMOutputInvalidError` vs `LLMProviderUnavailableError`）。
- [ ] 實作測試用 `FakeLLMProvider`（`backend/tests/fakes/fake_llm_provider.py`），可依呼叫順序 script 回傳值／例外。

## 應用層

- [ ] 實作 `ClassifyClausesCommand`（`app/application/commands/classify_clauses.py`）：狀態檢查、重試迴圈、
      fallback clause、整份文件失敗處理。
- [ ] 擴充 `GetClausesQuery`（`app/application/queries/get_clauses.py`）：依 `status` 回傳
      `ClauseListResponse` 或 `ClassifiedClauseListResponse`。

## API

- [ ] 新增 `app/api/routes_classification.py`：`POST /api/documents/{document_id}/classify`。
- [ ] 新增 `ClassifiedClauseListResponse`／`ExtractedClauseResponse`（`app/api/schemas.py` 或
      `app/domain/schemas/extracted_clause.py` 覆用）。
- [ ] `routes_documents.py` 的 `GET /clauses` `response_model` 改為
      `ClauseListResponse | ClassifiedClauseListResponse`。
- [ ] `app/main.py` 的錯誤碼對照表新增 `LLM_PROVIDER_UNAVAILABLE → 502`；`app/api/dependencies.py` 新增
      `get_llm_provider()`、`get_classification_repository()`、`get_classify_clauses_command()`。

## 測試

- [ ] Unit：`SummaryGuard` 金額／日期比對（正例／反例，含全形數字正規化）。
- [ ] Unit：`ClassifyClausesCommand` 以 `FakeLLMProvider` 驗證：首次成功、重試後成功、兩次皆失敗 → fallback、
      `LLMProviderUnavailableError` → 整份文件 `failed` 且不寫入 classification repository。
- [ ] Integration：001 三份 fixture 的 `ParsedClause` 經 `FakeLLMProvider` 分類後，`clause_id`／`location`／
      `original_text` 與 001 輸出一致；`ExtractedClause` 通過 `contracts/extracted_clause.schema.json`。
- [ ] API contract：`POST /classify` 狀態碼（202／404／409／502）；`GET /clauses` 在 `parsed`／`classified`
      兩種狀態下皆符合對應 schema；未設定 `OLLAMA_API_KEY` 時應用程式啟動失敗（設定驗證測試，不需真的呼叫外部
      服務）。

## 驗收

- [ ] 執行完整測試套件（`uv run pytest`），確認全數通過且未依賴真實 Ollama 服務。
- [ ] 以 001 三份 fixture 人工覆核至少 10 個 clause 的分類與摘要，確認未包含原文未提及的金額／日期／義務
      （spec.md 驗收 2），結果記錄於 spec.md。
- [ ] 確認無任何測試快照、log 或錯誤訊息包含合約原文、摘要全文或 `OLLAMA_API_KEY`。
- [ ] 更新 `specs/002-llm-clause-classification/spec.md` 的驗收紀錄與已知限制。
- [ ] 建議請 Codex（或等同的獨立驗證流程）覆核實作是否符合 spec.md／design.md，特別是重試/fallback 邏輯與
      錯誤碼對照。
