# 004：Vue 合約審閱工作台

## Goal

讓使用者在瀏覽器中上傳 `.docx` 軟體開發合約、執行既有後端的解析／分類／審閱流程，並在同一個工作台左欄閱讀後端保存的合約原文、右欄以甲方或乙方視角檢視已取得的風險結果。此 feature 只消費 001–003 的 API，不修改任何後端行為。

## In scope

- 建立 Vue 3、Vite、TypeScript、Pinia 的前端專案與單一審閱工作台頁面。
- 透過既有 API 上傳文件，依序觸發 parse、classify、review，並取得 `ReviewReport`。
- 左欄以 `ReviewReport.clauses[].original_text` 依後端回傳順序顯示原文；點選風險可捲動並高亮其 `clause_id`。
- 右欄顯示 `ReviewReport.risks`；每張卡顯示條號、目前視角的風險等級、原文引用、說明、建議、來源。
- 甲方／乙方切換只在 Pinia UI state 改變既有風險的排序與強調色，不呼叫 API、不重新解析文件、不重新觸發 LLM。
- 永久可見的「本服務僅提供輔助審閱與風險提示，非法律意見。」免責聲明。
- Vitest 單元／元件測試與前端建置驗證。

## Out of scope

- 後端 API、LLM、風險規則、資料庫或任何 `backend/` 檔案的修改。
- 使用者帳號、持久化工作階段、歷史報告列表、報告匯出、PDF／OCR、條款編輯。
- 自行解析 `.docx` 或在瀏覽器重組／改寫原文。
- 對目前未存在的 `GET /api/documents/{id}` 或 `GET /api/clauses` 路由提出相容層；實際路由以本 feature 的 contracts 為準。

## User scenarios

### 上傳並檢視報告

Given 使用者選擇有效的 `.docx` 檔案  
When 使用者送出審閱  
Then 前端依序呼叫既有 upload、parse、classify、review、report API，完成後在左欄顯示原文並在右欄顯示報告風險。

### 切換視角而不重新審閱

Given 前端已取得一份 `ReviewReport`  
When 使用者從乙方切換到甲方或反向切換  
Then 前端只依 `risk_for_client` 或 `risk_for_vendor` 對記憶體中的 `risks` 排序與套用風險強調，不發送任何 HTTP request。

### 由風險定位原文

Given 右欄存在一張連到某 `clause_id` 的風險卡  
When 使用者點擊卡片  
Then 左欄捲動到該條款並顯示暫時高亮，且不改變後端資料。

### 顯示後端錯誤

Given 任一後端操作回傳 machine-readable error  
When 使用者執行審閱  
Then 前端顯示後端的繁中 `message`，不在 UI 或 console 顯示合約原文。

## Functional requirements

1. API client 必須集中在 `review.api.ts`；Vue components 不可直接使用 `fetch`。
2. Server state（document ID、report、進度、API error）由 Pinia store 管理；選定視角與高亮 clause 為前端 UI state。
3. 上傳請求必須是 `multipart/form-data`，欄位名稱為 `file`；不可手動設定 multipart `Content-Type`。
4. 前端工作流程必須依序使用既有路由：`POST /api/documents` → `POST /api/documents/{id}/parse` → `POST /api/documents/{id}/classify` → `POST /api/documents/{id}/review` → `GET /api/documents/{id}/report`。
5. 左欄原文只能來自後端回傳的 `clauses[].original_text`，不得自行剖析檔案或把摘要當作原文。
6. 風險卡至少顯示 `location.article_no`（若無則「未標示條號」）、目前視角的 level、`evidence[].quote`、`concern`、`suggestion`、`source_refs`；同時保留另一方等級的可讀標示。
7. 視角預設為乙方；切換 action 不得呼叫 API client 的任何方法，也不得變更 `report` 內容。
8. 高／中／低／無風險分別使用清楚可辨的紅、橘、藍灰、灰色視覺語意；不能只靠顏色傳達等級。
9. 無論載入、成功、失敗或尚未選檔，固定免責聲明都必須可見。
10. 前端應提供 loading、空結果與可理解的錯誤狀態；正式 API base URL 可由 `VITE_API_BASE_URL` 設定，預設同源 `/api`。

## API contract

實際路由及 request／response 詳細內容見 [contracts/api.md](./contracts/api.md) 與 [contracts/review-report.schema.json](./contracts/review-report.schema.json)。

本 feature 釐清先前口語路徑：目前後端**沒有** `GET /api/documents/{id}` 或 `GET /api/clauses`；查詢條款的已實作路由是 `GET /api/documents/{document_id}/clauses`。工作台在完整審閱後使用 `GET /report` 所回傳的 `clauses` 作為左欄資料來源。

## Failure handling

| HTTP / error code | 前端行為 |
|---|---|
| `400`（例如 `UNSUPPORTED_FILE_TYPE`） | 顯示 server `message`，保留目前已成功取得的 report。 |
| `404 DOCUMENT_NOT_FOUND` | 顯示文件不存在訊息，不嘗試自行建立 ID。 |
| `409 DOCUMENT_NOT_READY` | 顯示尚未完成的訊息；本機 MVP workflow 的各 POST 同步執行後再讀取 report，不實作盲目重試。 |
| `502 LLM_PROVIDER_UNAVAILABLE` | 顯示分析服務暫時無法使用；不得以假資料填補風險。 |
| 網路／未知錯誤 | 顯示泛用連線失敗訊息；不輸出檔案內容、條款或完整 report 至 console。 |

## Acceptance criteria

1. 使用有效 `.docx` 時，前端會依序呼叫 upload、parse、classify、review、report，並將 `ReviewReport.clauses` 與 `risks` 分別交給左右欄。
2. 每張呈現的風險卡都有條號、選定方風險等級、至少一段原文引用、說明、建議、來源；缺少條號或來源時有明確 fallback 文案。
3. 已載入報告後切換甲方／乙方，API mock 呼叫次數保持不變、report reference／內容不被修改，卡片排序依該方風險等級改變。
4. 點選風險卡可讓對應原文條款被選中並高亮，不產生 network request。
5. 任何 UI state 下都可見固定免責聲明。
6. API client、Pinia store、risk card rendering 與 perspective toggle 都有 Vitest 覆蓋。
7. `npm run build` 與 `npm test -- --run` 成功完成。

## Non-functional requirements

- 視角切換只處理已在記憶體中的風險排序，應在單一 animation frame 內完成常見 MVP 文件的更新。
- 原文、風險說明與上傳檔案不得寫入 console、測試 snapshot 或未遮罩的錯誤 telemetry。
- UI 對鍵盤可操作；切換按鈕提供可辨識的目前選取狀態，風險卡可聚焦。
- components、store、API client 依責任分離，讓後端 endpoint 演進時只需集中調整 API／types 層。

## 驗收紀錄

- 實作位置：`frontend/`；規格與契約位置：`specs/004-frontend-review-workbench/`。
- `npm run build`：通過（`vue-tsc -p tsconfig.app.json --noEmit && vite build`；44 modules transformed，產出 `dist/`）。
- `npm test -- --run`：通過。Codex 實作時 sandbox 無法解析 `registry.npmjs.org`（`ENOTFOUND`），
  之後由 Claude 於有網路環境執行 `npm install`（208 packages）並重跑測試：4 個測試檔、6 項測試全數通過。
- Acceptance criteria 1–7 皆已透過 API／store／component 分層、production build 與 Vitest 通過驗證。
- Claude 覆核程式碼：`review.api.ts` 僅用 `FormData` 上傳、不手動設定 `Content-Type`；`http.ts` 不在錯誤或
  網路例外訊息中夾帶檔案內容；`review.store.ts` 的 `setPerspective` 為同步 state 變更、`sortRisksForPerspective`
  回傳淺拷貝，不改變 `report` 參照；`RiskCard.vue` 對缺條號／來源皆有 fallback 文案並同時顯示另一方風險等級
  （不僅靠顏色）；`DisclaimerBanner.vue` 在任何狀態下都渲染固定文案；`src/`、`tests/` 皆無 `console.*` 呼叫。
  API route 路徑與 `backend/app/api/routes_*.py` 的實際 prefix／path 逐一核對一致。

## 已知限制

- 本機正式風險規則目前預設為 `draft`（見 003），因此實際報告可能合法地包含零筆風險；工作台會顯示空結果提示。
- 現有 backend 為 in-memory repository；重新啟動後端後，已上傳的 document ID 不可再取用。
