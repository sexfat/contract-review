# 合約審閱助手（Contract Review Assistant）

針對「軟體開發／系統委外承攬合約」的審閱助手。使用者上傳 `.docx` 合約草稿，系統將條款結構化、
產生白話摘要，並同時以**甲方（業主）**與**乙方（接案方／開發商）**雙視角呈現風險分級、原因與建議。

> 本服務僅提供輔助審閱與風險提示，**非法律意見**。完整產品原則與範圍見
> [docs/DEVELOPMENT_SPEC.md](docs/DEVELOPMENT_SPEC.md)。

## 技術棧

```text
frontend/  Vue 3 + Vite + TypeScript + Pinia + Vue Router
backend/   Python 3.12 + FastAPI + Pydantic v2
llm/       Ollama Cloud（gemma4:31b-cloud）
data/      本機 JSON 風險規則庫（risk_rules.seed.json）
```

MVP 階段後端資料為 in-memory／本機檔案系統，尚未接資料庫；詳見
[docs/SDD_ARCHITECTURE.md](docs/SDD_ARCHITECTURE.md) 的分層架構與依賴規則。

## 快速開始

### 後端

```bash
cd backend
uv sync
cp ../.env.example ../.env   # 填入 OLLAMA_API_KEY 才能跑 classify／review
uv run uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev -- --port 5173
```

開發模式下前端已在 `vite.config.ts` 設定 `/api` proxy 轉發到 `http://127.0.0.1:8000`
（可用 `VITE_DEV_API_PROXY_TARGET` 覆寫），不需另外處理 CORS。正式環境改由
`VITE_API_BASE_URL` 指定後端網址（預設同源 `/api`）。

瀏覽 <http://localhost:5173> 上傳 `.docx` 即可跑完整 parse → classify → review 流程。

### 測試

```bash
cd backend && uv run pytest
cd frontend && npm test -- --run
```

## 專案狀態（依 spec 編號）

| Spec | 說明 | 狀態 |
|---|---|---|
| [001](specs/001-docx-clause-extraction/) | DOCX 條款抽取 | 完成 |
| [002](specs/002-llm-clause-classification/) | LLM 條款分類與白話摘要 | 完成 |
| [003](specs/003-dual-perspective-risk-review/) | 雙視角風險規則與 Evidence 驗證 | 完成 |
| [004](specs/004-frontend-review-workbench/) | Vue 合約審閱工作台（前端） | 完成 |

詳細變更歷史見 [CHANGELOG.md](CHANGELOG.md)。

## 已知限制

- **正式風險規則庫（`data/risk_rules.seed.json`）全數為 `status: draft`**，需使用者人工審核並改為
  `reviewed` 後，`POST /review` 才會針對正式資料產生風險輸出（刻意的安全預設）。手動驗證用的
  已審核規則集在 `specs/003-dual-perspective-risk-review/fixtures/reviewed_test_rules.json`。
  審核方式：直接編輯規則的 `status` 欄位，目前無管理介面。
- 僅支援 `.docx`；不支援 PDF、掃描檔、`.doc` 舊格式，偵測到 Track Changes 會直接拒絕上傳。
- 後端 MVP 為 in-memory repository，重新啟動後已上傳的 `document_id` 即失效。
- 風險檢索為決定性的 `clause_type` + `trigger_patterns` 子字串比對，非向量／embedding 檢索。

各 spec 目錄下的 `spec.md`「已知限制」段落有更完整、逐一功能的細節。

## 開發流程

本專案採 Spec-Driven Development（SDD）：每個 feature 先有 `spec.md` → `design.md` → `contracts/`
→ `tasks.md`，才進入實作與測試。規則與目錄慣例見 [specs/README.md](specs/README.md)。
