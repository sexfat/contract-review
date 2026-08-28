# 005：RAG 知識檢索與 Judge Gate

## Goal

在 003 已完成的「決定性規則比對＋雙視角風險評估」流程上，加入兩件事：

1. **RAG 檢索（`legal_sources` 層）**：對每個已比對到 `risk_rules` 的 clause，額外檢索台灣法規知識庫，取回
   相關法條摘要作為 LLM 產生風險說明時的外部依據，並在 `RiskAssessment.source_refs` 中可追溯引用。
2. **Judge gate（任務 C）**：在 003 既有的確定性驗證（evidence 子字串、source_refs allow-list、保守措辭黑
   名單）之後，加入一次獨立的 LLM judge 呼叫，檢查風險敘述是否超出原文與檢索依據支持、甲乙雙方風險是否互
   相矛盾、是否構成不當法律結論。

對應 `docs/DEVELOPMENT_SPEC.md` M3 的「任務 C：judge 驗證」與 §9「RAG 規格」第 2 層（`legal_sources`），以及
`docs/SDD_ARCHITECTURE.md` §7 的 LLM 契約管線：

```text
JSON parse → Pydantic validation → evidence substring validation
→ source ID allow-list validation → judge gate → persistence
```

003 spec.md「已確認決策 1」已明確把這兩項工作留到本 feature；`RiskAssessment` 的既有資料契約**不變**，本
feature 只新增 `source_refs` 可能引用的 ID 來源與一道額外驗證關卡。

## In scope

- **`RetrievalQuery` / `RetrievedKnowledge` schema**（`domain/schemas/`）：完全比照
  `docs/SDD_ARCHITECTURE.md` §7 既定欄位，不自行增減。
- **`KnowledgeRepository` port**（`application/ports/`）：`search(query: RetrievalQuery) -> list[RetrievedKnowledge]`，
  只回傳 `jurisdiction == query.jurisdiction` 且 `status == "reviewed"` 的條目，依向量相似度排序取前 `top_k`
  筆。
- **`EmbeddingProvider` port**（`application/ports/`）：`embed(texts: list[str]) -> list[list[float]]`，供檢
  索與離線索引建置共用。
- **本機輕量向量儲存（infrastructure）**：
  - `LocalVectorKnowledgeRepository` 實作 `KnowledgeRepository`：啟動時載入
    `data/legal_sources.seed.json`（條目 metadata，格式比照 `risk_rules.seed.json` 的人工可審閱風格）與
    `data/legal_sources.embeddings.npz`（對應 embedding 向量），純 Python + numpy 計算 cosine similarity，
    不依賴 Postgres／pgvector／Docker。
  - 離線索引建置腳本（`backend/scripts/build_legal_sources_index.py`）：讀取
    `data/legal_sources.seed.json`，呼叫 `EmbeddingProvider` 產生向量並寫出
    `data/legal_sources.embeddings.npz`。此腳本是開發時手動執行的建置步驟，**不在 API 執行流程中**，比照
    `data/risk_rules.seed.json` 是先由人工／腳本產生再提交進版控的模式。
  - `KnowledgeRepository` 的 port 介面與 `RetrievalQuery`/`RetrievedKnowledge` 契約與儲存後端無關；未來若要
    換成 pgvector，只需新增一個實作並替換依賴注入，不動 application／domain 層（見「已確認決策」）。
- **檢索時機**：只對「003 規則比對已命中至少一筆 `reviewed` risk rule」的 clause 觸發檢索（呼應
  `docs/DEVELOPMENT_SPEC.md` §9「RAG 僅取回外部依據，不用來尋找目前合約內容」），查詢文字使用
  `clause.original_text`，`clause_type` 帶入 query，`jurisdiction` 固定 `"TW"`，`top_k` 預設 5。
- **`RiskAssessmentRequest` 擴充**：新增 `retrieved_sources: list[RetrievedKnowledge]` 欄位，傳給 LLM 供其
  在 `concern`／`suggestion` 中參考其內容（措辭層面），但**不要求、也不信任 LLM 輸出 `source_refs`**——
  沿用 003 既有設計決策（design.md「設計決策」：`RiskAssessmentResult` 本身不含 `source_refs` 欄位，該值由
  應用層決定性設定為 `[rule.id]`）。本 feature 延伸同一原則：`RiskAssessment.source_refs` 由應用層設定為
  `[rule.id, *(s.knowledge_id for s in retrieved_sources)]`（即本次呼叫實際帶入 LLM 的規則與檢索結果 ID 全
  集），**不需要、也不做 LLM 輸出的 allow-list 驗證**——依構造即合法，與 003 的理由相同：不讓 LLM 自行決定
  它引用了什麼。
- **Judge gate（新 LLM 呼叫，任務 C）**：
  - 新 port `RiskJudgeProvider.judge(request: JudgeRequest) -> JudgeResult`，輸入為
    `clause.original_text` + 該筆 `RiskAssessmentResult`（含 evidence；`source_refs` 尚未產生，因為它是
    003／本 feature 都採用的「應用層決定性設定」欄位，不屬於 LLM 輸出，judge 不需要也不應該檢查它）+
    `retrieved_sources`。
  - `JudgeResult` 至少含 `passed: bool`、`reason: str`（不通過時的原因，供 log／debug，不得含合約原文全
    文）。
  - 檢查項目（比照 `docs/DEVELOPMENT_SPEC.md` §10）：evidence 是否確實存在於條款、風險描述是否超出原文與
    檢索依據支持、甲乙雙方風險是否互相矛盾、措辭是否構成不當法律結論（斷言型用語的語意檢查，作為 003 靜態
    黑名單的第二層防護，非取代）。
  - Judge gate 接在 003 既有的確定性驗證**之後**，兩者都通過才產生該筆 `RiskAssessment`；judge 不通過視同
    003 既有的「驗證失敗」，走相同的重試（最多一次）與捨棄邏輯，不產生佔位或降級版本的風險輸出。
- `data/legal_sources.seed.json`：至少 10 筆台灣法規摘要條目（涵蓋民法承攬、消費者保護法相關、政府採購法可
  能相關條文等軟體外包常見依據）。確切欄位、型別與必填規則見
  `contracts/legal_source.schema.json`；欄位為 `knowledge_id`、`corpus`（固定 `"legal_sources"`）、
  `parent_id`（見下方「chunking 政策」）、`title`、`source_title`、`content`、`clause_type`（可為 null，
  表適用多種類型）、`jurisdiction`、`source_url`、`effective_date`、`version`、`status`、`reviewed_by`、
  `updated_at`。**本 feature 完成時全部標記為 `status: "draft"`**，比照 003「已確認決策 2」的安全預設（詳
  見下方「已確認決策」）。範例見 `fixtures/example_legal_sources.json`。

### Chunking 政策（legal_sources 切分粒度）

法規原文有天生階層（法 > 條 > 項 > 款），切分粒度太粗會稀釋 embedding 語意、檢索不精準；切太細則可能把法
條的主要義務與但書（例外）拆散，導致 LLM 只引用到其中一半、產生誤導性結論。本 feature 採以下政策：

1. **不做演算法式自動切分**（sliding window／固定長度切段）。每筆 `legal_sources` 條目由人工撰寫或摘錄，
   比照 003 `risk_rules.seed.json` 的手寫模式；本 feature 的語料規模（≥10 筆）不需要自動化 chunking。
2. **一個 `knowledge_id` 對應一個語意完整的最小法律單元**——通常是一項（項次），但**不得**把同一句話裡的主
   要義務與但書／例外拆成兩筆（例如「應負賠償責任，但因不可抗力者不在此限」必須留在同一個 `content`
   內，不可只保留前半句）。
3. 若某條法規底下有多項、且各項對應到不同風險主題（因此需要各自被獨立檢索命中），才拆出多筆 child 條目，
   `parent_id` 指回代表整條完整原文的 parent 條目；parent 條目本身 `parent_id` 為 `null`。
4. **檢索命中 child 條目時，實際傳給 LLM 的 `retrieved_sources` 必須包含 parent 的完整 `content`**（呼應
   `docs/DEVELOPMENT_SPEC.md` §9「回傳 top-k child chunks 時，同時取回其 parent document」），避免子片段
   脫離上下文被誤讀；若命中的條目本身就是 `parent_id: null`（未拆分），則直接使用該條目。
5. 若一條法規本身語意單一、不需要拆項，直接建一筆、`parent_id: null` 即可，不強制拆分。

## Out of scope

- pgvector／PostgreSQL 儲存後端（留待正式導入資料庫的里程碑，即 `docs/DEVELOPMENT_SPEC.md` M5 前後；本
  feature 只確保 port 介面相容，不實作）。
- `practice_cases`、`organization_playbooks` 知識庫分層（文件 §9 第三、四層，留待後續版本）。
- 知識庫審核（`draft` → `reviewed`）的管理介面；比照 003，本 feature 仍是使用者直接編輯 JSON 檔案的
  `status` 欄位。
- Embedding 模型選型的系統性評估（如多模型比較、re-ranking）；本 feature 先選定一個可用模型讓流程跑通，模
  型品質評估留待 eval 里程碑。
- 向量索引的增量更新／版本管理工具；`legal_sources.embeddings.npz` 目前是整批重新產生。
- 法規內容本身的正確性與時效性審核（由使用者／法律背景者人工完成，見「待人工完成事項」）。
- 前端顯示檢索來源的 UI 變更（`RiskCard` 目前已顯示 `source_refs`，若 004 的呈現方式需要調整，另開 spec）。

## User scenarios

### 命中規則的條款，檢索到相關法規依據並通過 judge gate

Given 一個 clause 已比對到至少一筆 `reviewed` risk rule  
When 系統執行風險評估  
Then 系統以該 clause 原文向 `KnowledgeRepository` 查詢，取回 `status == "reviewed"` 的 `legal_sources` 條
目（可能為空），連同規則內容一起交給 LLM；產生的 `RiskAssessment` 若通過 003 既有驗證與本 feature 新增的
judge gate，才寫入報告，且其 `source_refs` 由應用層決定性設定為
`[rule.id, *(檢索回傳條目的 knowledge_id)]`（非 LLM 輸出，見「Judge gate」小節）。

### 檢索無相關法規依據

Given 某 clause 的檢索結果為空集合（無 `reviewed` 法規條目符合，或知識庫尚未建置）  
When 系統執行風險評估  
Then 流程比照沒有外部依據時的行為：LLM 僅依 clause 原文與 risk rule 內容作答，`RiskAssessment.source_refs`
不包含任何 `knowledge_id`；不得因檢索為空而中斷整份文件審閱。

### Judge gate 判定不通過

Given LLM 產生的 `RiskAssessmentResult` 通過 003 既有的確定性驗證，但 judge 判定其風險描述超出原文與檢索依
據支持  
When 系統執行 judge gate  
Then 該筆結果視為驗證失敗，走 003 既有的重試邏輯；重試一次仍不通過則捨棄該筆風險，不寫入報告，其餘 clause
與風險不受影響。

### 知識庫尚未審核

Given `data/legal_sources.seed.json` 全數為 `status: "draft"`（本 feature 完成時的預設狀態）  
When 系統執行檢索  
Then `KnowledgeRepository.search` 一律回傳空集合，行為等同「無外部依據」，不影響 003 既有的風險輸出邏輯（
安全預設，非 bug）。

## Functional requirements

1. `KnowledgeRepository.search` 只回傳 `jurisdiction` 相符且 `status == "reviewed"` 的條目；`draft` 條目不
   參與檢索與排序。
2. 檢索僅在「該 clause 已比對到至少一筆 reviewed risk rule」時觸發；未命中規則的 clause 不呼叫
   `EmbeddingProvider`／`KnowledgeRepository`（維持 003 的呼叫量特性，避免無謂的 embedding 成本）。
3. `LocalVectorKnowledgeRepository` 的排序邏輯（cosine similarity、`top_k` 截斷、`jurisdiction`／`status`
   過濾）須為確定性的純 Python／numpy 計算，可離線單元測試，不得呼叫外部服務。
4. `RiskAssessmentRequest.retrieved_sources` 只能包含本次 `KnowledgeRepository.search` 的回傳結果；LLM 不
   得看到未經檢索流程放行的知識庫條目。
5. `RiskAssessment.source_refs` 由應用層決定性設定為 `[rule.id, *(s.knowledge_id for s in
   retrieved_sources)]`，沿用 003 design.md「設計決策」的模式（`RiskAssessmentResult` 不含 `source_refs`
   欄位，不信任、也不需要驗證 LLM 輸出）；因此**不存在**「LLM 引用了未檢索到的 `knowledge_id`」這種失敗情
   境，本項需求取代原先「source_refs allow-list 驗證」的設計。
6. Judge gate 必須在 003 既有的確定性驗證（evidence 子字串、保守措辭黑名單）**全部通過之後**才呼叫，避免對
   明顯失敗的結果浪費一次額外 LLM 呼叫。
7. Judge 不通過時，`JudgeResult.reason` 可寫入技術 log／debug 用途，但不得包含合約原文全文或風險敘述全
   文，比照 003 Failure handling 的資料留存規則。
8. Judge gate 呼叫失敗（LLM provider 無法連線）比照 003 的 `LLMProviderUnavailableError` 語意：整份文件審
   閱失敗，不寫入任何部分結果。
9. `EmbeddingProvider` 呼叫失敗時（單一 clause 的檢索失敗，非整體 provider 無法連線），該 clause 視同「檢
   索結果為空」繼續走無外部依據的流程，不得讓單一 clause 的檢索失敗中斷整份文件審閱（除非底層是
   provider-level 無法連線，此時比照 FR8）。
10. `data/legal_sources.seed.json` 於本 feature 完成時，所有條目狀態一律為 `"draft"`（比照 003「已確認決
    策 2」）。
11. 檢索命中的條目若 `parent_id` 不為 `null`，`KnowledgeRepository.search` 回傳給呼叫端的
    `RetrievedKnowledge` 必須是該 child 對應的 **parent 條目完整內容**（依 `parent_id` 展開），而非 child
    自身的片段 `content`；`knowledge_id` 仍記錄為實際命中的 child ID，供 `source_refs` 可追溯引用（見「
    Chunking 政策」第 4 點）。
12. `data/legal_sources.seed.json` 的單筆 `content` 不得將同一法律主張的主要義務與但書／例外拆成兩筆不同
    `knowledge_id`（見「Chunking 政策」第 2 點）；此規則以 code review／人工審核把關，非自動化檢查。

## Failure handling

| Error code | 對使用者訊息 |
|---|---|
| `DOCUMENT_NOT_READY` | 沿用 003（文件尚未完成分類）。 |
| `LLM_PROVIDER_UNAVAILABLE` | 沿用 003；judge gate 呼叫失敗時比照相同語意與訊息。 |
| `KNOWLEDGE_INDEX_UNAVAILABLE`（新增，可選） | 僅用於「已選擇使用 `LocalVectorKnowledgeRepository`，但
`data/legal_sources.embeddings.npz` 格式錯誤或與 `legal_sources.seed.json` 的 `knowledge_id` 對不上」——
比照 001 對 fixture 缺漏的處理方式，啟動期即報錯而非執行期靜默降級。**索引檔完全不存在（尚未執行離線建置腳
本）不算這個錯誤**：dependency 組裝層（design.md）改用 `NullKnowledgeRepository`（一律回傳空集合）優雅降
級，讓 003 既有的審閱流程在 005 剛部署、索引尚未建置時仍可正常運作，行為等同「知識庫為空」。 |

錯誤 log 僅記錄 `document_id`、`clause_id`（如適用）、`knowledge_id`（如適用）、error code 與技術堆疊；不
得記錄合約原文、法規全文、風險敘述全文或 judge 的完整 rationale。

## Acceptance criteria

1. 針對至少一份 001 fixture 搭配 003 已審核的測試規則集，手動將 `data/legal_sources.seed.json` 中對應條目
   標記為 `reviewed` 後執行 `POST /review`，可觀察到至少一筆 `RiskAssessment.source_refs` 包含檢索到的
   `knowledge_id`。
2. 針對「檢索結果為空」情境，有自動化測試確認流程正常完成且不影響既有風險輸出。
3. 有自動化測試確認 `RiskAssessment.source_refs` 是應用層依 `[rule.id, *(檢索回傳條目的 knowledge_id)]`
   決定性組成，不受 LLM 輸出內容影響（例如 fake provider 回傳的 `RiskAssessmentResult` 即使不含
   `source_refs` 概念，組出的 `source_refs` 仍正確）。
4. 針對「judge 判定不通過」情境，有自動化測試確認重試一次仍不通過時該筆風險被捨棄，不出現在報告中。
5. 針對「judge provider 無法連線」情境，有自動化測試確認文件標記為 `failed` 且無殘留部分結果。
6. `LocalVectorKnowledgeRepository` 的排序（cosine similarity + top_k + 過濾條件）有不呼叫外部服務的 unit
   test。
7. 無任何測試快照、log 或錯誤訊息包含合約原文、法規全文或風險敘述全文。
8. Pydantic contract validation、unit、integration 與 API contract tests 全部通過；既有 001–004 測試不受
   影響（`FakeRiskAssessmentProvider` 模式擴充為同時提供 fake `KnowledgeRepository`／`RiskJudgeProvider`）。
9. `data/legal_sources.seed.json` 至少 10 筆條目，涵蓋軟體外包常見的法規依據，且每筆含
   `title`／`content`／`source_url`／`effective_date`，並通過 `contracts/legal_source.schema.json` 驗證。
10. 針對「檢索命中 child 條目（`parent_id` 不為 null）」情境，有自動化測試確認回傳給 LLM 的
    `retrieved_sources` 內容為 parent 的完整原文，而非 child 片段。

## Non-functional requirements

- 單一 clause 的檢索（embedding + 本機向量排序）應在可忽略的時間內完成（本機計算，無網路 I/O，除非
  `EmbeddingProvider` 走遠端 API）；judge gate 的 LLM 呼叫比照 003 的 30 秒逾時策略。
- `LocalVectorKnowledgeRepository` 的排序邏輯不得呼叫外部服務，須可離線單元測試。
- API response 沿用 001–003 的慣例：繁中可讀訊息搭配英文 machine error code。
- `data/legal_sources.embeddings.npz` 與 `data/legal_sources.seed.json` 需保持筆數與順序可對應（例如以
  `knowledge_id` 為 key 存成 `.npz` 的具名陣列，避免單純依賴陣列 index 對應而在條目增刪時錯位）。

## 已確認決策

1. **向量儲存先採本機輕量方案，不導入 Postgres／pgvector／Docker**：`data/legal_sources.embeddings.npz`
   （離線腳本產生，比照 `risk_rules.seed.json` 是人工可審閱、可提交進版控的資料）+
   `LocalVectorKnowledgeRepository`（numpy cosine similarity，啟動時全量載入）。此決策僅影響
   `infrastructure` 層的其中一個實作；`KnowledgeRepository` port 與 `RetrievalQuery`/`RetrievedKnowledge`
   契約維持 `docs/SDD_ARCHITECTURE.md` §7 既定介面，未來若語料量成長需要 pgvector，只需新增一個實作並替換
   dependency injection，不需更動 application／domain 層或 `RiskAssessment` 的資料契約。
2. **`data/legal_sources.seed.json` 於本 feature 完成時，所有條目狀態一律為 `"draft"`**，比照 003 對
   `risk_rules.seed.json` 的相同安全預設：在使用者（建議搭配法律／合約背景者）人工審核並將 `status` 改為
   `"reviewed"` 之前，`KnowledgeRepository.search` 一律回傳空集合，`POST /review` 的行為等同「無 RAG 依
   據」，不會因未審核的法規內容影響風險輸出。
3. **Judge gate 與 003 既有的確定性驗證共用同一組重試次數（`max_retries`，預設 1）**，不額外增加重試預
   算，避免單一 clause 的 LLM 呼叫次數過度增長（003 已知限制：呼叫量隨 clause 數 × 命中規則數成長；本
   feature 每筆候選風險最多再加一次 judge 呼叫，重試時兩者一併重跑）。
4. **`legal_sources` 不做演算法式自動 chunking，改採人工撰寫＋ `parent_id` 分層**：語料規模小（≥10 筆）時
   人工撰寫可完整掌控「不拆散但書」的品質風險，優於用固定長度或 sliding window 切分法規原文。若未來語料量
   顯著成長（例如引入完整法規資料庫），需重新評估是否導入自動化 chunking pipeline，屆時應另開 spec，且不
   影響 `KnowledgeRepository` port 介面（見「Chunking 政策」）。

## 待人工完成事項

- `data/legal_sources.seed.json` 的法規條目內容（法條原文摘要、`source_url`、`effective_date`）由本
  feature 起草，**需使用者（建議搭配具法律背景者）逐條核實來源與時效性後，將 `status` 改為 `"reviewed"`，
  本 feature 的 RAG 檢索才會實際產生輸出**。未審核前，系統行為等同「知識庫為空」。
- ~~`EmbeddingProvider` 實際採用的模型／服務需使用者確認~~ **已確認（2026-08-28）**：Ollama Cloud 完全不
  提供 embedding 模型（即時查詢 ollama.com/search?c=cloud，16 個 cloud 模型全為對話／推理模型），因此改採
  **本機 Ollama** 執行 `qwen3-embedding:0.6b`（639MB、0.6B 參數、輸出 1024 維、支援 100+ 語言）。
  `OLLAMA_EMBEDDING_BASE_URL`（預設 `http://localhost:11434`）與雲端的 `OLLAMA_BASE_URL` 分開設定。**已於
  2026-08-28 實際跑過一次**：本機安裝 Ollama、`ollama pull qwen3-embedding:0.6b`，執行
  `build_legal_sources_index.py` 產生 `data/legal_sources.embeddings.npz`（15 筆、1024 維，與 seed 的
  `knowledge_id` 完全對應）。抽查繁體中文檢索品質：瑕疵修補情境的查詢命中 `civil-493`／`civil-514`／
  `civil-498`（皆為瑕疵／時效相關條文，`civil-493` 排第一）；著作財產權情境命中 `copyright-12` 排第一——
  Qwen3-Embedding 對繁體中文法規文字的檢索品質符合預期。

## 已知限制（預期，實作完成後補充驗收紀錄）

- 本機向量儲存為整批載入，法規語料量顯著成長後，記憶體與啟動時間會線性增加，尚未做分頁或近似最近鄰索引優
  化。
- 索引更新流程為手動重新執行離線腳本，無增量更新或版本比對工具。
- 待實作完成後，比照 003 補上真實 LLM 流程的驗證紀錄與已知限制。
