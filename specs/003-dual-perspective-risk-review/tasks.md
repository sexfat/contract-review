# 003：雙視角風險規則與 Evidence 驗證工作清單

## 風險規則資料

- [ ] 撰寫 `data/risk_rules.seed.json`：至少 30 筆規則，涵蓋 `docs/DEVELOPMENT_SPEC.md` §8 的 10 大主題，
      全部標記 `status: "draft"`（見 spec.md「已確認決策」）。
- [ ] 於 `specs/003-dual-perspective-risk-review/fixtures/`（或 README）建立一份「測試用 reviewed 規則」
      子集，供自動化測試使用（不影響正式 `data/risk_rules.seed.json` 的 draft 狀態）。

## Domain

- [ ] 新增 `RiskLevel` enum（`app/domain/schemas/risk_level.py`）。
- [ ] 新增 `RiskRule` schema（`app/domain/schemas/risk_rule.py`）。
- [ ] 新增 `EvidenceRef`／`RiskAssessment`／`ReviewReport` schema（`app/domain/schemas/risk_assessment.py`）。
- [ ] 新增 `RiskAssessmentRequest`／`LLMEvidenceItem`／`RiskAssessmentResult`
      （`app/domain/schemas/llm_risk_assessment.py`）。
- [ ] 抽出共用 `text_normalize`（`app/domain/services/text_normalize.py`），並讓 002 的
      `summary_guard.py` 改用它（重構，不改變既有測試結果）。
- [ ] 實作 `RiskRuleMatcher.match_rules`（`app/domain/services/risk_rule_matcher.py`）。
- [ ] 實作 `ConservativeLanguageGuard.find_banned_phrase`
      （`app/domain/services/conservative_language_guard.py`）。
- [ ] 實作 `build_review_report`（`app/domain/services/review_report_builder.py`）。
- [ ] `DocumentStatus` 新增 `REVIEWING`、`COMPLETED`（`app/domain/entities/document.py`）。

## Ports 與 Repository

- [ ] 新增 `RiskAssessmentProvider` port（`app/application/ports/risk_assessment_provider.py`）。
- [ ] 新增 `RiskRuleRepository` port（`app/application/ports/risk_rule_repository.py`）。
- [ ] 新增 `RiskAssessmentRepository` port（`app/application/ports/risk_assessment_repository.py`）。
- [ ] 實作 `JsonRiskRuleRepository`（`app/infrastructure/repositories/json_risk_rule_repository.py`）：
      載入 `data/risk_rules.seed.json`、以 `RiskRule` 驗證、`list_reviewed()` 過濾 `status`／`jurisdiction`。
- [ ] 實作 `InMemoryRiskAssessmentRepository`（`app/infrastructure/repositories/memory_repository.py`）。

## LLM Provider Adapter

- [ ] 抽出共用例外分類邏輯 `classify_llm_exception`（`app/infrastructure/llm/exception_mapping.py`），並讓
      002 的 `ollama_provider.py` 改用它（重構，不改變既有測試結果）。
- [ ] 實作 `OllamaRiskAssessmentProvider`（`app/infrastructure/llm/ollama_risk_provider.py`）：組 prompt
      （原文＋單一候選規則）、逾時控制、JSON parse + Pydantic 驗證、例外一律 `from None` 切斷 chain。
- [ ] 實作測試用 `FakeRiskAssessmentProvider`（`backend/tests/fakes/fake_risk_assessment_provider.py`），
      比照 `FakeLLMProvider` 可 script 回傳值／例外。

## 應用層

- [ ] 實作 `ReviewDocumentCommand`（`app/application/commands/review_document.py`）：狀態檢查、
      `(clause, rule)` 逐筆評估、重試迴圈、evidence／措辭驗證後捨棄、整份文件失敗處理、`risk_id` 決定性產生。
- [ ] 實作 `GetReviewReportQuery`（`app/application/queries/get_review_report.py`）。
- [ ] 調整 `GetClausesQuery`（002）：`GET /clauses` 判斷條件擴充為
      `status in (CLASSIFIED, COMPLETED)` 才回傳分類形狀。

## API

- [ ] 新增 `app/api/routes_review.py`：`POST /api/documents/{document_id}/review`、
      `GET /api/documents/{document_id}/report`。
- [ ] `app/api/dependencies.py` 新增 `get_risk_rule_repository()`、`get_risk_assessment_repository()`、
      `get_risk_assessment_provider()`、`get_review_document_command()`、`get_review_report_query()`。
- [ ] `app/main.py` 註冊新 router（既有錯誤碼對照表應已足夠涵蓋 `DOCUMENT_NOT_READY`／
      `DOCUMENT_NOT_FOUND`／`LLM_PROVIDER_UNAVAILABLE`，確認無需新增 error code）。

## 測試

- [ ] Unit：`RiskRuleMatcher`（clause_type 相符、trigger_patterns 命中、只吃 reviewed 規則）。
- [ ] Unit：`ConservativeLanguageGuard`（黑名單正例／反例）。
- [ ] Unit：`build_review_report`（純 Python，不需 LLM，驗證 contract_title／overall_summary／disclaimer）。
- [ ] Unit：`ReviewDocumentCommand` 以 `FakeRiskAssessmentProvider` 驗證：`applicable=false` 跳過、
      evidence 不在原文重試後捨棄、措辭違規重試後捨棄、`LLMProviderUnavailableError` 整份文件失敗且不寫入
      `RiskAssessmentRepository`。
- [ ] Integration：測試用 reviewed 規則集 + 002 fixture 的 `ExtractedClause`，經 `FakeRiskAssessmentProvider`
      產生 `RiskAssessment`，驗證符合 `contracts/review_report.schema.json`。
- [ ] API contract：`POST /review`（202／404／409／502）、`GET /report`（200／409）；`GET /clauses` 在
      `completed` 狀態下仍回傳分類形狀的回歸測試。

## 驗收

- [ ] 執行完整測試套件（`uv run pytest`），確認全數通過且未依賴真實 Ollama 服務。
- [ ] 使用者審核 `data/risk_rules.seed.json` 中至少涵蓋 001/002 fixture 會命中的規則，手動改為
      `status: "reviewed"`，以真實 `OLLAMA_API_KEY` 執行 `POST /review` 並人工覆核產出的
      `RiskAssessment`（含 evidence、雙視角風險等級、措辭是否保守）。
- [ ] 確認無任何測試快照、log 或錯誤訊息包含合約原文、風險敘述全文或規則內容全文。
- [ ] 更新 `specs/003-dual-perspective-risk-review/spec.md` 的驗收紀錄與已知限制。
- [ ] 請 Codex 覆核實作是否符合 spec.md／design.md，特別是 `(clause, rule)` 逐筆重試/捨棄邏輯、
      `source_refs` 決定性設定是否確實未信任 LLM 輸出、`build_review_report` 是否真的不呼叫 LLM。
