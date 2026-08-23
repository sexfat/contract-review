# 004：Vue 合約審閱工作台工作清單

## 規格與契約

- [x] 閱讀 001、002、003 的 spec／design／tasks 結構與既有 SDD 文件。
- [x] 依 `backend/app/api/` 與 domain schemas 建立實際 API contract，並記錄不存在的口語路徑差異。
- [x] 定義視角切換為純 client-side sorting／highlighting 的驗收條件。

## 前端基礎與分層

- [x] 初始化 Vue 3 + Vite + TypeScript + Pinia + Vue Router + Vitest 專案設定。
- [x] 建立 shared HTTP client、contract-review API client、domain TypeScript types。
- [x] 建立 Pinia store，區隔 server state（report／workflow）與 UI state（perspective／selected clause）。

## 審閱工作台

- [x] 實作 DOCX 選檔與 upload → parse → classify → review → report workflow。
- [x] 實作左側合約原文 pane 與 risk-to-clause focus/highlight。
- [x] 實作右側甲方／乙方 toggle、依視角排序的 risk panel 與 empty／loading／error state。
- [x] 實作包含條號、風險等級、引用、說明、建議、來源的 risk card。
- [x] 實作永久可見的免責聲明與鍵盤可用的互動元件。

## 測試

- [x] 為 API client 加入 route／multipart／error mapping tests。
- [x] 為 store 加入排序與 toggle 不 re-fetch／不改 report 的 tests。
- [x] 為 RiskCard 加入所有必要欄位 rendering test。
- [x] 為 ReviewPage 加入 permanent disclaimer 與 local toggle test。

## 驗收

- [x] 執行 `npm run build`（通過）。
- [x] 執行 `npm test -- --run`（Codex 實作時 sandbox 無法安裝依賴；由 Claude 於有網路環境重新
      `npm install` 並執行，4 個測試檔、6 項測試全數通過）。
- [x] 將實際驗收命令與結果回填至 spec.md。
