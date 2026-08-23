# 003：雙視角風險規則與 Evidence 驗證工作清單

## 風險規則資料

- [x] 撰寫 `data/risk_rules.seed.json`：32 筆規則，涵蓋 `docs/DEVELOPMENT_SPEC.md` §8 的 10 大主題，
      全部標記 `status: "draft"`（見 spec.md「已確認決策」）。
- [x] 於 `specs/003-dual-perspective-risk-review/fixtures/reviewed_test_rules.json` 建立一份「測試用
      reviewed 規則」子集，供自動化測試與真實 LLM smoke test 使用（不影響正式
      `data/risk_rules.seed.json` 的 draft 狀態）。

## Domain

- [x] 新增 `RiskLevel` enum（`app/domain/schemas/risk_level.py`）。
- [x] 新增 `RiskRule` schema（`app/domain/schemas/risk_rule.py`）。
- [x] 新增 `EvidenceRef`／`RiskAssessment`／`ReviewReport` schema（`app/domain/schemas/risk_assessment.py`）。
- [x] 新增 `RiskAssessmentRequest`／`LLMEvidenceItem`／`RiskAssessmentResult`
      （`app/domain/schemas/llm_risk_assessment.py`）。
- [x] 抽出共用 `text_normalize`（`app/domain/services/text_normalize.py`），並讓 002 的
      `summary_guard.py` 改用它（重構，不改變既有測試結果）。
- [x] 實作 `RiskRuleMatcher.match_rules`（`app/domain/services/risk_rule_matcher.py`）。
- [x] 實作 `ConservativeLanguageGuard.find_banned_phrase`
      （`app/domain/services/conservative_language_guard.py`）。
- [x] 實作 `build_review_report`（`app/domain/services/review_report_builder.py`）。
- [x] `DocumentStatus` 新增 `REVIEWING`、`COMPLETED`（`app/domain/entities/document.py`）。

## Ports 與 Repository

- [x] 新增 `RiskAssessmentProvider` port（`app/application/ports/risk_assessment_provider.py`）。
- [x] 新增 `RiskRuleRepository` port（`app/application/ports/risk_rule_repository.py`）。
- [x] 新增 `RiskAssessmentRepository` port（`app/application/ports/risk_assessment_repository.py`）。
- [x] 實作 `JsonRiskRuleRepository`（`app/infrastructure/repositories/json_risk_rule_repository.py`）：
      載入 `data/risk_rules.seed.json`、以 `RiskRule` 驗證、`list_reviewed()` 過濾 `status`／`jurisdiction`。
- [x] 實作 `InMemoryRiskAssessmentRepository`（`app/infrastructure/repositories/memory_repository.py`）。

## LLM Provider Adapter

- [x] 抽出共用例外分類邏輯（`app/infrastructure/llm/exception_mapping.py` 的 `raise_mapped_llm_exception`），
      並讓 002 的 `ollama_provider.py` 改用它（重構，不改變既有測試結果）。
- [x] 實作 `OllamaRiskAssessmentProvider`（`app/infrastructure/llm/ollama_risk_provider.py`）：組 prompt
      （原文＋單一候選規則）、逾時控制、JSON parse + Pydantic 驗證、例外一律 `from None` 切斷 chain。
- [x] 實作測試用 `FakeRiskAssessmentProvider`（`backend/tests/fakes/fake_risk_assessment_provider.py`），
      比照 `FakeLLMProvider` 可 script 回傳值／例外。

## 應用層

- [x] 實作 `ReviewDocumentCommand`（`app/application/commands/review_document.py`）：狀態檢查、
      `(clause, rule)` 逐筆評估、重試迴圈、evidence／措辭驗證後捨棄、整份文件失敗處理、`risk_id` 決定性產生。
- [x] 實作 `GetReviewReportQuery`（`app/application/queries/get_review_report.py`）。
- [x] 調整 `GetClausesQuery`（002）：`GET /clauses` 判斷條件擴充為
      `status in (CLASSIFIED, COMPLETED)` 才回傳分類形狀。

## API

- [x] 新增 `app/api/routes_review.py`：`POST /api/documents/{document_id}/review`、
      `GET /api/documents/{document_id}/report`。
- [x] `app/api/dependencies.py` 新增 `get_risk_rule_repository()`、`get_risk_assessment_repository()`、
      `get_risk_assessment_provider()`、`get_review_document_command()`、`get_review_report_query()`。
- [x] `app/main.py` 註冊新 router；既有錯誤碼對照表涵蓋 `DOCUMENT_NOT_READY`／`DOCUMENT_NOT_FOUND`／
      `LLM_PROVIDER_UNAVAILABLE`，無需新增 error code。

## 測試

- [x] Unit：`RiskRuleMatcher`（clause_type 相符、trigger_patterns 命中、只吃 reviewed 規則）—
      `tests/unit/test_risk_rule_matcher.py`。
- [x] Unit：`ConservativeLanguageGuard`（黑名單正例／反例）— `tests/unit/test_conservative_language_guard.py`。
- [x] Unit：`build_review_report`（純 Python，不需 LLM）— `tests/unit/test_review_report_builder.py`。
- [x] Unit：`ReviewDocumentCommand` 以 `FakeRiskAssessmentProvider` 驗證：`applicable=false` 跳過、
      evidence 不在原文重試後捨棄、措辭違規重試後捨棄、`LLMProviderUnavailableError` 整份文件失敗且不寫入
      `RiskAssessmentRepository` — `tests/unit/test_review_document_command.py`。
- [x] Integration：測試用 reviewed 規則集 + 002 fixture 的 `ExtractedClause`，經 `FakeRiskAssessmentProvider`
      產生 `RiskAssessment`，驗證符合 `contracts/review_report.schema.json` —
      `tests/integration/test_review_fixture_flow.py`。
- [x] API contract：`POST /review`（202／404／409／502）、`GET /report`（200／409）；`GET /clauses` 在
      `completed` 狀態下仍回傳分類形狀的回歸測試 — `tests/api/test_review_api.py`。

## 驗收

- [x] 執行完整測試套件（`uv run pytest`）：108 passed，未依賴真實 Ollama 服務。
- [x] 以測試用 reviewed 規則集，使用真實 `OLLAMA_API_KEY` 對 001 兩份 fixture 執行完整
      parse → classify → review 流程，人工覆核產出的 4 筆 `RiskAssessment`（見 spec.md 驗收紀錄）。
      **正式 `data/risk_rules.seed.json` 仍全數為 `draft`，尚待使用者實際審核並改為 `reviewed`**——這步驟依
      spec.md 決策由使用者手動完成，不由本次實作代勞。
- [x] 確認無任何測試快照、log 或錯誤訊息包含合約原文、風險敘述全文或規則內容全文。
- [x] 更新 `specs/003-dual-perspective-risk-review/spec.md` 的驗收紀錄與已知限制。
- [ ] 請 Codex 覆核實作是否符合 spec.md／design.md，特別是 `(clause, rule)` 逐筆重試/捨棄邏輯、
      `source_refs` 決定性設定是否確實未信任 LLM 輸出、`build_review_report` 是否真的不呼叫 LLM。
