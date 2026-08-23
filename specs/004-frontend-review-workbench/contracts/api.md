# 004 API Contract

此文件依 `backend/app/api/routes_documents.py`、`routes_classification.py`、`routes_review.py`、`schemas.py` 與 domain response schemas 編寫。所有路徑均為現有 backend 路由；frontend 不新增或假設其他路由。

## Common error response

除成功 response 外，domain error 統一為：

```json
{
  "error_code": "DOCUMENT_NOT_READY",
  "message": "文件尚未完成分類，請稍後再試。"
}
```

| error code | HTTP status |
|---|---:|
| `UNSUPPORTED_FILE_TYPE`, `FILE_TOO_LARGE`, `INVALID_DOCX`, `TRACKED_CHANGES_NOT_SUPPORTED`, `LLM_OUTPUT_INVALID` | 400 |
| `DOCUMENT_NOT_FOUND` | 404 |
| `DOCUMENT_NOT_READY` | 409 |
| `LLM_PROVIDER_UNAVAILABLE` | 502 |

## `POST /api/documents`

Create a document.

- Request `Content-Type`: `multipart/form-data` (browser supplies boundary)
- Form field: `file` (`UploadFile`)
- Success: `201 Created`

```json
{
  "document_id": "string",
  "status": "uploaded"
}
```

`status` is one of `uploaded`, `parsing`, `parsed`, `classifying`, `classified`, `reviewing`, `completed`, `failed` in the shared status response model.

## `POST /api/documents/{document_id}/parse`

Start parsing a previously uploaded document.

- Request body: none
- Success: `202 Accepted`

```json
{
  "document_id": "string",
  "status": "parsing"
}
```

The local MVP executes synchronously but intentionally returns `parsing` so the response remains forward compatible with a background job.

## `POST /api/documents/{document_id}/classify`

Classify parsed clauses.

- Request body: none
- Success: `202 Accepted`

```json
{
  "document_id": "string",
  "status": "classifying"
}
```

## `GET /api/documents/{document_id}/clauses`

Return parsed or classified clauses. This is the actual existing clause endpoint.

- Success: `200 OK`
- Parsed response has `status: "parsed"`; each clause has `clause_id`, `clause_type: "other"`, `original_text`, `location`.
- Classified (and completed) response has `status: "classified"`; each clause additionally has `plain_summary`, `confidence`, optional `requires_human_review`, optional `model_id`, and a full `clause_type` enum.

`location` is:

```json
{
  "article_no": "第一條",
  "heading": "工作範圍",
  "source_start_index": 0,
  "source_end_index": 2,
  "paragraph_ids": ["p-0001"],
  "table_refs": []
}
```

## `POST /api/documents/{document_id}/review`

Start dual-perspective review of classified clauses.

- Request body: none
- Success: `202 Accepted`

```json
{
  "document_id": "string",
  "status": "reviewing"
}
```

## `GET /api/documents/{document_id}/report`

Return the completed review report.

- Success: `200 OK`
- Response schema: [review-report.schema.json](./review-report.schema.json)

The response contains the canonical original text at `clauses[].original_text`, plus `risks[]`. A risk contains both `risk_for_client` (甲方) and `risk_for_vendor` (乙方); perspective selection is deliberately a frontend-only concern.

## Route clarification

The backend does **not** expose `GET /api/documents/{document_id}` or `GET /api/clauses`. Consumers must not call those paths. Use `GET /api/documents/{document_id}/clauses` or, after review, `GET /api/documents/{document_id}/report`.
