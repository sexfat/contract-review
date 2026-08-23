# 001：DOCX 條款抽取工作清單

## 規格與測試資料

- [x] 建立三份去識別化繁中 DOCX fixtures：正常條號、混合條號、含付款表格。
- [x] 為每份 fixture 建立預期 block／clause 驗收斷言，不將完整合約原文輸出至 snapshot。

## 後端基礎

- [x] 初始化 FastAPI、Pydantic v2 與 pytest。
- [x] 建立 Document、DocumentStatus、ClauseLocation、ParsedClause schemas。
- [x] 建立本機 FileStorage、DocumentRepository、ClauseRepository ports 與 adapter。

## 解析能力

- [x] 實作 DOCX 格式、大小、可讀性與 Track Changes 驗證。
- [x] 實作依 OOXML body 順序讀取 paragraph/table 的 `DocxBlockReader`。
- [x] 實作條號 regex、階層辨識與 `ClauseSplitter`。
- [x] 實作 deterministic `clause_id` 與 unstructured fallback。

## API 與驗證

- [x] 實作上傳、解析、讀取條款三個 API。
- [x] 將 response 對齊 `contracts/clause.schema.json`。
- [x] 實作錯誤 code 與不含原文的安全 logging。
- [x] 加入 unit、integration、API contract tests。

## 驗收

- [x] 執行完整測試套件。
- [x] 手動確認三份 fixture 的條款順序、表格文字與條號。
- [x] 更新本 spec 的驗收紀錄與已知限制。
