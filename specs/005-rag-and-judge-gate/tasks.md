# 005：RAG 知識檢索與 Judge Gate 工作清單

## 知識庫資料

- [x] 撰寫 `data/legal_sources.seed.json`：15 筆法規條目，涵蓋民法承攬（瑕疵／驗收／遲延）、著作權法、消保
      法、政府採購法、個資法；欄位符合 `contracts/legal_source.schema.json`。
- [x] 逐筆核對官方來源（全國法規資料庫）並修正文字誤差；`status` 經人工審核後設為 `"reviewed"`，
      `reviewed_by` 記錄審核者。
- [x] 建立 `contracts/legal_source.schema.json`。
- [x] 建立 `fixtures/example_legal_sources.json`（+ `README.md`）：示範格式與 parent／child chunking 用法，
      供開發／測試參考，不影響正式 `data/legal_sources.seed.json`。
- [ ] 評估 `cpa-12`／`cpa-19`（消保法）與 `ppa-22-1-9`／`ppa-72`（政府採購法）四筆的適用性疑慮（消保法主要
      保護個人消費者、政府採購法只在甲方為政府機關時適用），決定是否保留、加註適用條件，或移出正式知識庫
      （spec.md「已知限制」待補）。

## Domain

- [x] 新增 `RetrievalQuery`／`RetrievedKnowledge`（`app/domain/schemas/retrieval.py`）。
- [x] 新增 `LegalSource`（`app/domain/schemas/legal_source.py`）。
- [x] 新增 `JudgeRequest`／`JudgeResult`（`app/domain/schemas/judge.py`）。
- [x] `RiskAssessmentRequest` 新增 `retrieved_sources: list[RetrievedKnowledge] = []`
      （`app/domain/schemas/llm_risk_assessment.py`）。
- [x] 實作 `rank_by_similarity`／`_cosine_similarity`（`app/domain/services/knowledge_ranking.py`）。
- [x] 實作 `resolve_retrieved_knowledge`（同檔 `knowledge_ranking.py`）。
- [x] 新增 `KnowledgeIndexUnavailableError`（`app/domain/errors.py`），加入 `_ERROR_CODE_REGISTRY`。

## Ports 與 Repository

- [x] 新增 `KnowledgeRepository` port（`app/application/ports/knowledge_repository.py`）。
- [x] 新增 `EmbeddingProvider` port（`app/application/ports/embedding_provider.py`）。
- [x] 新增 `RiskJudgeProvider` port（`app/application/ports/risk_judge_provider.py`）。
- [x] 實作 `LocalVectorKnowledgeRepository`（`app/infrastructure/repositories/local_vector_knowledge_repository.py`）：
      載入 `legal_sources.seed.json` + `.npz`、`knowledge_id` 對不上時 fail fast、`search()` 呼叫
      `EmbeddingProvider` + `rank_by_similarity` + `resolve_retrieved_knowledge`。
- [x] 實作 `NullKnowledgeRepository`（同檔）：一律回傳空集合。
- [x] 新增 `backend` 依賴 `numpy`（`backend/pyproject.toml`）。

## LLM / Embedding Provider Adapter

- [x] `LLMSettings` 新增 `ollama_embedding_model: str | None`（`OLLAMA_EMBEDDING_MODEL`，預設 `None`）與
      `ollama_embedding_base_url`（`OLLAMA_EMBEDDING_BASE_URL`，預設 `http://localhost:11434`——Ollama
      Cloud 不提供 embedding 模型，見下方，因此獨立於雲端的 `ollama_base_url`）
      （`app/infrastructure/llm/config.py`）。
- [x] `.env.example` 新增 `OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b`／`OLLAMA_EMBEDDING_BASE_URL=`。**已
      確認（2026-08-28）**：Ollama Cloud 完全不提供 embedding 模型，`qwen3-embedding:0.6b`（639MB、輸出
      1024 維、支援 100+ 語言）需在本機 Ollama 執行。
- [x] 實作 `OllamaEmbeddingProvider`（`app/infrastructure/llm/ollama_embedding_provider.py`），沿用
      `raise_mapped_llm_exception`。
- [x] 實作 `OllamaRiskJudgeProvider`（`app/infrastructure/llm/ollama_risk_judge_provider.py`）：prompt 明文
      JSON 範例（沿用 003 對 `gemma4:31b-cloud` 的教訓）、四項檢查（evidence／風險描述是否超出依據支持／
      甲乙矛盾／不當法律結論）。
- [x] 實作測試用 `FakeRiskJudgeProvider`（`backend/tests/fakes/`），比照 `FakeRiskAssessmentProvider` 的
      script 模式（key 改用 `clause_original_text`，見檔案內註解說明原因）。
- [x] 實作測試用 `FakeKnowledgeRepository`（`backend/tests/fakes/`）：可設定固定回傳的
      `list[RetrievedKnowledge]`。
- [x] 撰寫離線索引建置腳本 `backend/scripts/build_legal_sources_index.py`：讀
      `data/legal_sources.seed.json` → `EmbeddingProvider.embed()`（對每筆自己的 `content`，非 parent 展開
      後內容）→ `np.savez(data/legal_sources.embeddings.npz, **{knowledge_id: vector})`。
- [x] 本機安裝 Ollama（`brew install ollama` + `brew services start ollama`）、
      `ollama pull qwen3-embedding:0.6b`，實際執行離線腳本產生 `data/legal_sources.embeddings.npz`（15 筆，
      1024 維，與 seed 的 `knowledge_id` 完全對應）。抽查兩個查詢的檢索排序：瑕疵修補情境命中
      `civil-493`／`civil-514`／`civil-498`（皆為瑕疵/時效相關條文）；著作財產權情境命中 `copyright-12`
      排第一——繁體中文法規文字的檢索品質符合預期。

## 應用層

- [x] 擴充 `ReviewDocumentCommand`（`app/application/commands/review_document.py`）：新增
      `knowledge_repository`／`judge_provider` 欄位；`execute()` 迴圈改為「命中規則才檢索一次、迴圈內重複
      使用」；`_assess_one` 通過 003 既有驗證後呼叫 judge，不通過視同驗證失敗（共用同一組 `max_retries`）；
      `_to_risk_assessment` 的 `source_refs` 改為 `[rule.id, *(s.knowledge_id for s in retrieved_sources)]`。

## API / Dependency Wiring

- [x] `app/api/dependencies.py` 新增 `get_embedding_provider()`（設定缺漏／建構失敗回傳 `None`，不拋例外中
      止應用程式）、`get_knowledge_repository()`（索引檔不存在或 embedding provider 為 `None` 時回傳
      `NullKnowledgeRepository()`；否則建構 `LocalVectorKnowledgeRepository`）、`get_risk_judge_provider()`。
- [x] `get_review_document_command()` 新增 `knowledge_repository`／`judge_provider` 參數。
- [x] `KNOWLEDGE_INDEX_UNAVAILABLE` 走既有的 `DomainError` → HTTP 錯誤對照邏輯，無需新增路由層特殊處理
      （沿用 `_ERROR_CODE_REGISTRY`／`error_for_code`，`app/main.py` 不需改動）。

## 測試

- [x] Unit：`rank_by_similarity`（過濾條件、cosine 排序、top_k 截斷）—
      `tests/unit/test_knowledge_ranking.py`。
- [x] Unit：`resolve_retrieved_knowledge`（parent 展開／原樣回傳兩種情境）— 同檔。
- [x] Unit：`LocalVectorKnowledgeRepository`（`knowledge_id` 缺漏 fail fast、單次查詢失敗視同空結果、
      provider-level 例外往上傳播）— `tests/unit/test_local_vector_knowledge_repository.py`。
- [x] Unit：`ReviewDocumentCommand` 以 `FakeKnowledgeRepository`／`FakeRiskJudgeProvider` 驗證：未命中規則
      不檢索、命中規則觸發檢索且 `source_refs` 含 `knowledge_id`、judge 不通過重試後捨棄、judge 通過後成
      功、judge provider 無法連線整份文件失敗 — 擴充 `tests/unit/test_review_document_command.py`。
- [x] Contract：`data/legal_sources.seed.json`／`fixtures/example_legal_sources.json` 通過
      `contracts/legal_source.schema.json` — `tests/unit/test_legal_source_schema.py`。
- [x] Integration：既有 `tests/integration/test_review_fixture_flow.py` 擴充傳入
      `FakeKnowledgeRepository`／`FakeRiskJudgeProvider`（沿用既有 fixture，未另建向量檔案）。
- [x] API contract：`tests/api/test_review_api.py` 擴充 `_override_review_provider` 傳入
      `FakeKnowledgeRepository`／`FakeRiskJudgeProvider`，既有測試案例本身無需修改即可通過。

`uv run pytest`：**127 passed**（既有 108 + 005 新增 19，涵蓋 domain／application／infrastructure／API 各
層），未依賴真實 Ollama 服務。

## 驗收

- [x] 執行完整測試套件（`uv run pytest`），確認既有 001–004 測試不受影響（108 passed → 127 passed，無既有
      測試被修改斷言邏輯，只有新增 import／建構參數）。
- [ ] 以 `data/legal_sources.seed.json`（已 `reviewed`）+ 003 測試用 `reviewed` 規則集，對 001 fixture 執行
      真實 `parse → classify → review` 流程，人工覆核至少一筆 `RiskAssessment.source_refs` 含法規
      `knowledge_id`，且 `concern`／`suggestion` 用語仍為保守措辭（待本機 Ollama + embedding 索引就緒後執
      行）。
- [x] 驗證 `OLLAMA_EMBEDDING_MODEL` 未設定時，`POST /review` 行為與 003 完全一致（`NullKnowledgeRepository`
      生效，不影響既有風險輸出）——`get_knowledge_repository()` 邏輯 + 既有 API/整合測試預設未設定該環境變
      數即涵蓋此情境。
- [x] 確認無任何測試快照、log 或錯誤訊息包含合約原文、法規全文、風險敘述全文或 judge 完整 rationale（
      `JudgeRequest`／`JudgeResult` 不記錄合約原文全文於 log，`raise_mapped_llm_exception` 沿用既有
      `from None` 慣例切斷 exception chain）。
- [ ] 更新 `specs/005-rag-and-judge-gate/spec.md` 的驗收紀錄與已知限制（待本機 embedding 索引跑過一次真實
      流程後補完整驗收紀錄）。
- [ ] 請 Codex（或等效覆核）確認實作是否符合 spec.md／design.md，特別是：`source_refs` 是否確實為應用層決
      定性組成而非信任 LLM 輸出、judge gate 是否真的接在 003 既有驗證之後才呼叫、
      `NullKnowledgeRepository` fallback 是否讓索引未建置時的行為與 003 一致。
