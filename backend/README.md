# Backend — 合約審閱助手

後端實作，目前涵蓋：

- Feature 001（DOCX 條款抽取）— [../specs/001-docx-clause-extraction/spec.md](../specs/001-docx-clause-extraction/spec.md)
- Feature 002（LLM 條款分類與白話摘要）— [../specs/002-llm-clause-classification/spec.md](../specs/002-llm-clause-classification/spec.md)
- Feature 003（雙視角風險規則與 Evidence 驗證）— [../specs/003-dual-perspective-risk-review/spec.md](../specs/003-dual-perspective-risk-review/spec.md)

## 安裝與啟動

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

呼叫 `POST /api/documents/{document_id}/classify` 或 `POST /api/documents/{document_id}/review` 前，需在
專案根目錄建立 `.env`（複製自 `.env.example`）並填入 `OLLAMA_API_KEY`；未設定時該端點會直接失敗
（fail fast），不影響上傳／解析相關端點。

## 測試

```bash
cd backend
uv run pytest
```

測試全程使用 `FakeLLMProvider`／`FakeRiskAssessmentProvider`（`tests/fakes/`），不呼叫真實 Ollama 服務，
CI 不需要 `OLLAMA_API_KEY`。

## 重新產生 fixtures

```bash
cd backend
uv run python tests/fixtures_gen/generate_fixtures.py
```

## 風險規則庫（`data/risk_rules.seed.json`）

- 內含 32 筆規則，涵蓋 `docs/DEVELOPMENT_SPEC.md` §8 的 10 大主題，**全數為 `status: "draft"`**。
- `POST /review` 只使用 `status == "reviewed"` 的規則；在人工審核並將對應規則改為 `"reviewed"` 之前，
  審閱功能對正式資料不會產生任何風險（刻意的安全預設，見 003 spec.md「已確認決策」）。
- 審核方式：直接編輯 `data/risk_rules.seed.json` 中對應規則的 `status` 欄位，不提供管理介面。
- `specs/003-dual-perspective-risk-review/fixtures/reviewed_test_rules.json` 是**僅供自動化測試與開發驗證**
  使用的獨立小型規則集（已標記 `reviewed`），與正式規則庫無關，不得作為實際審閱依據。

## API

| Method | Path | 說明 |
|---|---|---|
| `POST` | `/api/documents` | 上傳 `.docx`（`multipart/form-data`，欄位 `file`） |
| `POST` | `/api/documents/{document_id}/parse` | 解析文件為條款（MVP 同步完成） |
| `POST` | `/api/documents/{document_id}/classify` | 對已解析條款呼叫 LLM 分類與摘要（MVP 同步完成） |
| `POST` | `/api/documents/{document_id}/review` | 對已分類條款執行雙視角風險評估（MVP 同步完成） |
| `GET` | `/api/documents/{document_id}/clauses` | 取得條款清單；回應形狀依文件 `status` 而定（`parsed`／`classified`） |
| `GET` | `/api/documents/{document_id}/report` | 取得完整 `ReviewReport`（僅 `status == completed` 時可用） |
| `GET` | `/api/health` | 健康檢查 |

## 已知限制

### M1（001）

- Repository 為 in-memory；檔案存放於本機 `backend/var/documents/`（未納入版控）。
- Track Changes 一律拒絕上傳，不嘗試合併修訂版本。
- 子項條號（壹、一、1. 等）僅併入所屬主條原文，不建立獨立 chunk。

### M2（002）

- `POST /classify` 為整份文件的（重）分類操作，不提供單一 clause 重跑。
- 摘要防呆的金額／百分比比對已改為數值比較（`app/domain/services/chinese_numeral.py`），但日期仍為逐字
  子字串比對；合約編號、當事人名稱等其他實體暫不檢查。
- 沒有條號的前言／定義段落（`unstructured-*`）有時會被分類為實質條款類型而非 `other`；已於真實 LLM 覆核中
  觀察到，屬分類邊界模糊而非事實臆造，詳見 spec.md 已知限制。

### M3（003）

- 正式 `data/risk_rules.seed.json` 全數為 `draft`，尚待使用者人工審核為 `reviewed` 才會實際產生風險輸出。
- 檢索為決定性的 `clause_type` + `trigger_patterns` 子字串比對，非向量檢索；真正的 embedding 檢索與
  LLM judge gate 留待 005。
- 每個 `(clause, 命中規則)` 各呼叫一次 LLM，規則庫變大後呼叫數量會隨之成長，尚未做批次合併優化。
- **重要**：`with_structured_output()` 對 `gemma4:31b-cloud`（透過 Ollama Cloud）在複雜 schema 上不可靠
  （模型會忽略 schema、自創 JSON 結構），已在兩個 adapter（`ollama_provider.py`、`ollama_risk_provider.py`）
  的 system prompt 中明文寫出範例 JSON 修正；未來若更換模型或供應商，需重新驗證此手法是否仍必要。
