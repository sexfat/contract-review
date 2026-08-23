# Backend — 合約審閱助手

後端實作，目前涵蓋：

- Feature 001（DOCX 條款抽取）— [../specs/001-docx-clause-extraction/spec.md](../specs/001-docx-clause-extraction/spec.md)
- Feature 002（LLM 條款分類與白話摘要）— [../specs/002-llm-clause-classification/spec.md](../specs/002-llm-clause-classification/spec.md)

## 安裝與啟動

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

呼叫 `POST /api/documents/{document_id}/classify` 前，需在專案根目錄建立 `.env`（複製自 `.env.example`）並填入
`OLLAMA_API_KEY`；未設定時該端點會直接失敗（fail fast），不影響上傳／解析相關端點。

## 測試

```bash
cd backend
uv run pytest
```

測試全程使用 `FakeLLMProvider`（`tests/fakes/fake_llm_provider.py`），不呼叫真實 Ollama 服務，CI 不需要
`OLLAMA_API_KEY`。

## 重新產生 fixtures

```bash
cd backend
uv run python tests/fixtures_gen/generate_fixtures.py
```

## API

| Method | Path | 說明 |
|---|---|---|
| `POST` | `/api/documents` | 上傳 `.docx`（`multipart/form-data`，欄位 `file`） |
| `POST` | `/api/documents/{document_id}/parse` | 解析文件為條款（MVP 同步完成） |
| `POST` | `/api/documents/{document_id}/classify` | 對已解析條款呼叫 LLM 分類與摘要（MVP 同步完成） |
| `GET` | `/api/documents/{document_id}/clauses` | 取得條款清單；回應形狀依文件 `status` 而定（`parsed`／`classified`） |
| `GET` | `/api/health` | 健康檢查 |

## 已知限制

### M1（001）

- Repository 為 in-memory；檔案存放於本機 `backend/var/documents/`（未納入版控）。
- Track Changes 一律拒絕上傳，不嘗試合併修訂版本。
- 子項條號（壹、一、1. 等）僅併入所屬主條原文，不建立獨立 chunk。

### M2（002）

- `POST /classify` 為整份文件的（重）分類操作，不提供單一 clause 重跑。
- 摘要防呆僅涵蓋常見金額／日期樣式（見 `app/domain/services/summary_guard.py`），合約編號、當事人名稱等其他
  實體暫不檢查。
- 真實 `OllamaClassificationProvider` 未在本機以真實 API key 執行過人工覆核（本開發環境未配置
  `OLLAMA_API_KEY`）；部署前應以至少 10 個 clause 的真實輸出覆核（spec.md 驗收 2）。
