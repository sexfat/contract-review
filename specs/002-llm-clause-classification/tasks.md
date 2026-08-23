# 002：條款分類與白話摘要工作清單

## Domain

- [x] 新增 `ClauseType` enum（`app/domain/schemas/clause_type.py`），值沿用 `docs/DEVELOPMENT_SPEC.md` §7。
- [x] 新增 `ExtractedClause` schema（`app/domain/schemas/extracted_clause.py`），含 `requires_human_review`、`model_id`。
- [x] 新增 `LLMClassificationRequest`／`LLMClassificationResult` schema（`app/domain/schemas/llm_classification.py`）。
- [x] 新增 `LLMOutputInvalidError`、`LLMProviderUnavailableError`（`app/domain/errors.py`），並加入
      `error_for_code` 對照表。
- [x] 實作 `SummaryGuard.find_ungrounded_amounts_and_dates`（`app/domain/services/summary_guard.py`）。
- [x] `DocumentStatus` 新增 `CLASSIFYING`、`CLASSIFIED`（`app/domain/entities/document.py`）。

## Ports 與 Repository

- [x] 新增 `LLMProvider` port（`app/application/ports/llm_provider.py`）。
- [x] 新增 `ClauseClassificationRepository` port（`app/application/ports/clause_classification_repository.py`）。
- [x] 實作 `InMemoryClauseClassificationRepository`（`app/infrastructure/repositories/memory_repository.py`）。

## LLM Provider Adapter

- [x] `backend/pyproject.toml` 新增依賴：`langchain-ollama`、`python-dotenv`、`pydantic-settings`。
- [x] 實作 `LLMSettings`（`app/infrastructure/llm/config.py`），讀取 `OLLAMA_API_KEY`／`OLLAMA_BASE_URL`／
      `OLLAMA_MODEL`；缺少 `OLLAMA_API_KEY` 時 fail fast。
- [x] 實作 `OllamaClassificationProvider`（`app/infrastructure/llm/ollama_provider.py`）：組 prompt、逾時控制、
      JSON parse + Pydantic 驗證、例外分類（`LLMOutputInvalidError` vs `LLMProviderUnavailableError`）。
- [x] 實作測試用 `FakeLLMProvider`（`backend/tests/fakes/fake_llm_provider.py`），可依呼叫順序 script 回傳值／例外。

## 應用層

- [x] 實作 `ClassifyClausesCommand`（`app/application/commands/classify_clauses.py`）：狀態檢查、重試迴圈、
      fallback clause、整份文件失敗處理。
- [x] 擴充 `GetClausesQuery`（`app/application/queries/get_clauses.py`）：依 `status` 回傳
      `ClauseListResponse` 或 `ClassifiedClauseListResponse`。

## API

- [x] 新增 `app/api/routes_classification.py`：`POST /api/documents/{document_id}/classify`。
- [x] 新增 `ClassifiedClauseListResponse`／`ExtractedClauseResponse`（實作為 `ExtractedClause`，於
      `app/domain/schemas/extracted_clause.py`）。
- [x] `routes_documents.py` 的 `GET /clauses` `response_model` 改為
      `ClauseListResponse | ClassifiedClauseListResponse`。
- [x] `app/main.py` 的錯誤碼對照表新增 `LLM_PROVIDER_UNAVAILABLE → 502`、`LLM_OUTPUT_INVALID → 400`；
      `app/api/dependencies.py` 新增 `get_llm_provider()`、`get_classification_repository()`、
      `get_classify_clauses_command()`。

## 測試

- [x] Unit：`SummaryGuard` 金額／日期比對（正例／反例，含全形數字正規化）— `tests/unit/test_summary_guard.py`。
- [x] Unit：`ClassifyClausesCommand` 以 `FakeLLMProvider` 驗證：首次成功、重試後成功、兩次皆失敗 → fallback、
      `LLMProviderUnavailableError` → 整份文件 `failed` 且不寫入 classification repository —
      `tests/unit/test_classify_clauses_command.py`。
- [x] Unit：`LLMSettings` 缺少 `OLLAMA_API_KEY` 時 fail fast — `tests/unit/test_llm_settings.py`。
- [x] Integration：001 三份 fixture 的 `ParsedClause` 經 `FakeLLMProvider` 分類後，`clause_id`／`location`／
      `original_text` 與 001 輸出一致；`ExtractedClause` 通過 `contracts/extracted_clause.schema.json` —
      `tests/integration/test_classification_fixture_flow.py`（parametrized over all 3 fixtures）。
- [x] API contract：`POST /classify` 狀態碼（202／404／409／502）；`GET /clauses` 在 `parsed`／`classified`
      兩種狀態下皆符合對應 schema — `tests/api/test_classification_api.py`。

## 驗收

- [x] 執行完整測試套件（`uv run pytest`）：58 passed，未依賴真實 Ollama 服務。
- [ ] 以 001 三份 fixture 人工覆核至少 10 個 clause 的分類與摘要，確認未包含原文未提及的金額／日期／義務
      （spec.md 驗收 2）。**尚未完成**：本開發環境未配置 `OLLAMA_API_KEY`，無法呼叫真實 Ollama Cloud
      服務；需在有金鑰的環境執行 `POST /classify` 後補做，結果記錄於 spec.md。
- [x] 確認無任何測試快照、log 或錯誤訊息包含合約原文、摘要全文或 `OLLAMA_API_KEY`。
- [x] 更新 `specs/002-llm-clause-classification/spec.md` 的驗收紀錄與已知限制。
- [x] 請 Codex 覆核實作是否符合 spec.md／design.md，特別是重試/fallback 邏輯與錯誤碼對照。
