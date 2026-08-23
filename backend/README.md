# Backend — 合約審閱助手

Feature 001（DOCX 條款抽取）的後端實作。範圍與驗收條件見
[../specs/001-docx-clause-extraction/spec.md](../specs/001-docx-clause-extraction/spec.md)。

## 安裝與啟動

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

## 測試

```bash
cd backend
uv run pytest
```

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
| `GET` | `/api/documents/{document_id}/clauses` | 取得結構化條款清單 |
| `GET` | `/api/health` | 健康檢查 |

## 已知限制（M1 範圍）

- 所有 clause 的 `clause_type` 固定為 `other`；分類與摘要留待 002。
- Repository 為 in-memory；檔案存放於本機 `backend/var/documents/`（未納入版控）。
- Track Changes 一律拒絕上傳，不嘗試合併修訂版本。
- 子項條號（壹、一、1. 等）僅併入所屬主條原文，不建立獨立 chunk。
