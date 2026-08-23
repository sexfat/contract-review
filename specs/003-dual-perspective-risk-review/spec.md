# 003：雙視角風險規則與 Evidence 驗證

## Goal

對已分類（`classified`）的合約條款，依「規則比對」找出可能適用的風險主題，透過 LLM 產生同時包含甲方（業主）與
乙方（開發商）視角的風險評估，並以確定性的 Python 規則驗證每筆風險的 evidence 與措辭，最終彙整成完整的
`ReviewReport`。對應 `docs/DEVELOPMENT_SPEC.md` M3 里程碑的「風險規則與雙視角審閱」與「任務 B：條款原文與
RAG 依據產生雙視角風險」。

本 feature **不包含**向量檢索（pgvector）與 LLM judge gate（任務 C）；依
`docs/SDD_ARCHITECTURE.md` §11 的建議順序，這兩項留待 005-rag-and-judge-gate。003 以決定性的
Python 規則比對取代向量檢索，並自行實作 evidence／措辭的確定性驗證（不涉及 LLM 二次判斷）。

## In scope

- `data/risk_rules.seed.json`：至少 30 筆規則，涵蓋 `docs/DEVELOPMENT_SPEC.md` §8 列出的 10 大主題，欄位
  格式沿用該文件範例；本 feature 完成時**全部標記為 `status: "draft"`**（見「已確認決策」）。
- 決定性的規則比對（`RiskRuleMatcher`）：依 clause 的 `clause_type`（002 的分類結果）與
  `trigger_patterns` 關鍵字是否出現於 `original_text`，篩出候選規則；只使用 `status == "reviewed"` 且
  `jurisdiction == "TW"` 的規則。
- LLM 呼叫（任務 B）：對每個「有比對到規則」的 clause，依原文與候選規則產生
  `RiskAssessment`（`risk_for_client`／`risk_for_vendor`／`concern`／`suggestion`／`evidence`／
  `source_refs`／`confidence`／`requires_human_review`）。
- 確定性驗證（domain，非 LLM）：
  - `evidence[].quote` 必須是該 clause `original_text` 的逐字子字串。
  - `source_refs` 只能引用該次比對實際回傳的規則 ID（allow-list），不得由 LLM 自行編造。
  - 保守措辭檢查：`concern`／`suggestion` 不得出現斷言型用語（如「本條無效」「一定會賠償」「保證勝訴」等）。
  - 三者任一失敗 → 視為該筆風險輸出失敗，走重試邏輯；重試後仍失敗則**捨棄該筆風險**（不輸出猜測結果，也不
    產生「無法分析」的假風險項目——與 002 的「每個 clause 都要有一筆分類結果」不同，風險本來就可能是零筆）。
- `POST /api/documents/{document_id}/review`、`GET /api/documents/{document_id}/report` API。
- `ReviewReport` 組裝：`contract_title`／`overall_summary`／`disclaimer` 由 Python 決定性邏輯產生（非
  LLM），`clauses` 沿用 002 的 `ExtractedClause`，`risks` 為驗證通過的 `RiskAssessment` 清單。
- `DocumentStatus` 新增 `REVIEWING`、`COMPLETED`。

## Out of scope

- pgvector／embedding 向量檢索、`knowledge_repository` 的 PostgreSQL 實作（留待 005）。
- LLM judge gate（任務 C：以 LLM 檢查風險敘述是否超出原文支持、甲乙風險是否互相矛盾）（留待 005）。
- `legal_sources`／`practice_cases`／`organization_playbooks` 知識庫分層（留待第二／三階段）。
- 前端顯示（留待 004）。
- 風險規則從 `draft` 審核為 `reviewed` 的流程與工具（由使用者人工完成，見「已確認決策」）。
- PostgreSQL 持久化（沿用 001／002 的 in-memory pattern，留待 006）。

## User scenarios

### 條款有比對到規則，風險驗證通過

Given 一份狀態為 `classified` 的文件，其中某 clause 的 `clause_type` 與原文命中至少一筆 `reviewed` 風險規則
的 `trigger_patterns`  
When 呼叫 `POST /api/documents/{document_id}/review`  
Then 系統為該 clause 產生至少一筆 `RiskAssessment`，`evidence[].quote` 可在原文找到，`source_refs` 僅引用
實際比對到的規則 ID。

### 條款沒有比對到任何規則

Given 某 clause 的 `clause_type`／原文未命中任何 `reviewed` 規則的 `trigger_patterns`  
When 系統執行風險評估  
Then 該 clause 不產生任何 `RiskAssessment`（不得為了「每條都要有結果」而臆造風險）。

### 風險驗證失敗後重試仍失敗

Given LLM 對某筆候選規則產生的風險評估，其 `evidence.quote` 不是原文子字串，或用了斷言型措辭  
When 系統重試一次仍未通過驗證  
Then 該筆風險被捨棄，不寫入 `ReviewReport`；其餘風險與 clause 的處理不受影響。

### 產生完整報告

Given 文件所有 clause 皆已完成風險評估流程（無論是否產生風險）  
When 呼叫 `GET /api/documents/{document_id}/report`  
Then 回傳 `ReviewReport`，包含 `contract_title`、依風險等級與數量產生的 `overall_summary`、固定的
`disclaimer`、完整 `clauses` 與通過驗證的 `risks`。

## Functional requirements

1. `POST /review` 只能在文件狀態為 `classified` 或 `completed`（重新審閱）時觸發；其餘狀態回傳
   `DOCUMENT_NOT_READY`。
2. `RiskRuleMatcher` 僅使用 `status == "reviewed"` 且 `jurisdiction == "TW"` 的規則；`draft` 規則不參與比對
   （因此 003 完成當下，除非使用者已審過部分規則，否則比對結果會是空集合——見「已知限制」）。
3. 規則比對邏輯必須是決定性的 Python code（`clause_type` 相等 + `trigger_patterns` 子字串命中），不得呼叫
   LLM 或向量服務。
4. LLM 只能根據「原文＋比對到的規則內容（`risk_explanation`／`review_questions`／`suggestion_template`）」作
   答；不得引用其他 clause 或未比對到的規則。
5. 每筆 `RiskAssessment.evidence` 至少一筆，且 `quote` 必須逐字出現在該 clause 的 `original_text`。
6. `RiskAssessment.source_refs` 只能是本次比對到、且傳入 LLM 的規則 ID；不在候選清單中的 ID 一律視為驗證
   失敗。
7. `concern`／`suggestion` 不得使用斷言型措辭（初版黑名單：「本條無效」「一定會賠償」「保證勝訴」「絕對」
   「必然」等，可擴充）。
8. 驗證失敗的風險最多重試一次；重試後仍失敗則捨棄該筆風險，不寫入報告，也不得靜默保留無效版本。
9. `RiskAssessment.clause_id` 必須存在於該文件的 `clauses` 清單中。
10. `contract_title`、`overall_summary`、`disclaimer` 由 Python 決定性邏輯產生，不呼叫 LLM（呼應「Python 管
    結構、LLM 管語意」原則）。
11. LLM provider 整體無法連線時（同 002 的 `LLMProviderUnavailableError` 語意），整份文件審閱失敗，不寫入
    任何部分結果。

## API contract

### `POST /api/documents/{document_id}/review`

- Response `202`：`{document_id, status: "reviewing"}`（同 001／002 慣例：MVP 同步執行完畢，但回應字面契約
  固定回報處理中狀態）。
- Response `409`：`DOCUMENT_NOT_READY`（文件尚未 `classified`）。
- Response `404`：文件不存在。
- Response `502`：`LLM_PROVIDER_UNAVAILABLE`。

### `GET /api/documents/{document_id}/report`

- 文件狀態為 `completed` 時回傳 `200` + `ReviewReport`。
- 其餘未完成狀態回傳 `409 DOCUMENT_NOT_READY`。
- 確切 schema 見 `contracts/review_report.schema.json`（design.md 階段建立）。

## Failure handling

| Error code | 對使用者訊息 |
|---|---|
| `DOCUMENT_NOT_READY` | 文件尚未完成分類，請稍後再試。 |
| `LLM_PROVIDER_UNAVAILABLE` | 分析服務暫時無法使用，請稍後再試。 |

錯誤 log 僅記錄 `document_id`、`clause_id`（如適用）、error code 與技術堆疊；不得記錄合約原文、風險敘述全文
或規則內容全文。

## Acceptance criteria

1. 針對至少一份 001 fixture，手動將對應的候選規則標記為 `reviewed` 後執行 `POST /review`，可產生至少一筆
   `RiskAssessment`，且 `evidence.quote` 可在原文找到。
2. 針對「規則比對為空」的 clause，有自動化測試確認不產生風險。
3. 針對「evidence 不是原文子字串」「source_refs 引用未比對到的規則」「措辭違反黑名單」三種驗證失敗情境，
   各有自動化測試確認：重試一次仍失敗時該筆風險被捨棄，不出現在報告中。
4. 針對「LLM provider 整體無法連線」有自動化測試，確認文件標記為 `failed` 且無殘留部分結果。
5. `ReviewReport` 的 `contract_title`／`overall_summary`／`disclaimer` 由確定性邏輯產生，有對應的 unit test
   （不需呼叫 LLM 即可驗證）。
6. 無任何測試快照、log 或錯誤訊息包含合約原文、風險敘述全文或規則內容全文。
7. Pydantic contract validation、unit、integration 與 API contract tests 全部通過。
8. `data/risk_rules.seed.json` 至少 30 筆規則，涵蓋 `docs/DEVELOPMENT_SPEC.md` §8 的 10 大主題，且每筆規則
   含 `risk_for_client`／`risk_for_vendor`／`risk_explanation`／`suggestion_template`。

## Non-functional requirements

- 單一 clause 的風險評估 LLM 呼叫（含一次重試）應在 30 秒內完成或逾時失敗（沿用 002 的逾時策略）。
- 規則比對（Python 決定性邏輯）不得呼叫外部服務，須可離線單元測試。
- API response 沿用 001／002 的慣例：繁中可讀訊息搭配英文 machine error code。

## 已確認決策

1. **003 的「檢索」採決定性規則比對，不做向量檢索**：以 clause 的 `clause_type` 相等 + `trigger_patterns`
   子字串命中篩選候選規則，純 Python、可離線測試。真正的 embedding 向量檢索與 LLM judge gate 留待
   005-rag-and-judge-gate，屆時會取代／強化本 feature 的比對邏輯，但不需更動 `RiskAssessment` 的資料契約。
2. **`data/risk_rules.seed.json` 於本 feature 完成時，所有規則狀態一律為 `"draft"`**，不得標記為
   `"reviewed"`。`RiskRuleMatcher` 只使用 `reviewed` 規則，因此在使用者實際審核並手動將規則改為 `reviewed`
   之前，`POST /review` 對任何文件都不會產生風險（這是刻意的安全預設，而非 bug）。使用者審核規則的方式：
   直接編輯 `data/risk_rules.seed.json` 中對應規則的 `status` 欄位；本 feature 不提供審核用的管理介面。

## 待人工完成事項

- `data/risk_rules.seed.json` 的 30+ 筆規則內容（觸發樣式、雙方風險說明、建議用語）由本 feature 起草，
  **需使用者（建議搭配具法律／合約背景者）逐條審核後，將 `status` 改為 `"reviewed"`，本 feature 的風險評估
  流程才會實際產生輸出**。未審核前，系統行為等同「規則庫為空」，不會顯示任何風險（符合「保守措辭」與
  「不得將未審核內容當作依據」原則，見 `docs/DEVELOPMENT_SPEC.md` §2、§9）。

## 驗收紀錄

- 實作位置：`backend/app`（domain/application/infrastructure/api，沿用 001/002 的分層）；測試位置：
  `backend/tests`。
- `uv run pytest`：108 passed（001/002 既有測試維持通過 + 003 新增 36 個 unit／integration／API contract
  測試），全程使用 `FakeRiskAssessmentProvider`，不呼叫真實 Ollama 服務。
- `data/risk_rules.seed.json`：32 筆規則，涵蓋 10 大主題，全數 `status: "draft"`（符合「已確認決策」2）。
- 以 `specs/003-dual-perspective-risk-review/fixtures/reviewed_test_rules.json`（測試用、非正式規則庫）搭配
  使用者提供的 `OLLAMA_API_KEY`，對 001 的 `normal-numbering.docx`／`mixed-numbering.docx` 執行完整
  parse → classify → review 真實流程：
  - 共產生 4 筆 `RiskAssessment`，`evidence.quote` 逐一比對後皆為原文子字串，`source_refs` 皆僅含單一實際
    使用的規則 ID。
  - 措辭皆為保守用語（「可能」「建議確認」「可考慮」），未出現黑名單斷言詞。
  - **重要發現並修正**：`with_structured_output()` 對 `gemma4:31b-cloud`（透過 Ollama Cloud）在較複雜的
    `RiskAssessmentResult` schema（含巢狀 `evidence` 陣列）上**不可靠**——模型會自創 JSON 結構（例如巢狀
    `analysis`／`review_results`），完全忽略指定的 Pydantic schema，甚至曾直接回覆「請提供 JSON Schema」；
    可重現、非偶發。修正方式：在 system prompt 中明文寫出範例 JSON（含欄位名稱與型別），而非只依賴
    `with_structured_output` 的自動 schema 注入。修正後穩定產生正確格式。
  - 同時發現：`applicable=false` 時模型會對 `risk_for_client`／`risk_for_vendor`／`concern`／`suggestion`
    填入空字串，導致 enum／`min_length=1` 驗證失敗；已在 prompt 中明確給出「不適用」情境的範例 JSON
    （`risk_for_client`/`risk_for_vendor` 填 `"none"`，`concern`/`suggestion` 填 `"不適用"`）修正，
    修正後穩定通過。
  - 002 的 `OllamaClassificationProvider` 因 schema 較簡單、欄位命名恰好符合模型直覺，過去未觸發此問題，
    但屬僥倖而非可靠保證；已比照套用相同的「prompt 內明文 JSON 範例」寫法強化，並確認強化後分類功能不受
    影響（重跑 002 的即時驗證與既有測試皆通過）。
- Acceptance criteria 1–7：以上述自動化測試與真實 LLM 流程共同涵蓋。

## 已知限制

- **`data/risk_rules.seed.json` 全數為 `draft`，尚未經使用者審核為 `reviewed`**；在使用者完成審核前，
  `POST /review` 對正式資料不會產生任何風險（刻意的安全預設，見「已確認決策」2）。
- `RiskAssessmentResult` 依賴 prompt 內明文 JSON 範例而非可信賴的 schema 強制約束（因 Ollama Cloud 對
  `gemma4:31b-cloud` 未可靠支援 `format=json_schema`）；若更換模型或供應商，需重新驗證此手法是否仍必要。
- 每個 `(clause, matched rule)` 各呼叫一次 LLM；規則庫變大後呼叫數量會隨 clause 數 × 命中規則數成長，
  尚未做批次合併優化（design.md「不確定事項」已記錄）。
- 保守措辭黑名單為初版靜態清單，未涵蓋所有可能的斷言語氣；正式 judge gate（005）上線後可作為第二層防護。
- 尚未實作前端顯示；留待 004-vue-review-workbench。
