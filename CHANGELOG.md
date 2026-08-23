# Changelog

本檔案記錄本專案的重大變動，格式參考 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)。
專案目前尚未切版號／發版，所有項目暫列於 `Unreleased`，依 [SDD spec 編號](specs/README.md) 分組；
每筆記錄末尾的 hash 對應對應的 git commit。

## Unreleased

### 004 前端審閱工作台（`specs/004-frontend-review-workbench/`）

- Added：新增 `frontend/` — Vue 3 + Vite + TypeScript + Pinia 審閱工作台；左欄顯示合約原文、
  右欄以甲方／乙方雙視角顯示風險卡，切換視角僅本地排序、不重新呼叫 API。含 Vitest 單元／元件測試。
  由 Codex 依 spec/design 規劃並實作，Claude 覆核程式碼、跑通 `npm install`／`npm test -- --run`。
  （`737fc12`）
- Fixed：`vite.config.ts` 加入 dev-only `/api` proxy，解決前端 dev server（`:5173`）呼叫後端
  （`:8000`）時被瀏覽器 CORS 擋下的問題；正式環境 `VITE_API_BASE_URL` 同源預設行為不變，未改動
  後端程式碼。（`f22e3e3`）
- Added：`specs/003-.../fixtures/risky-contract.docx` 測試合約與說明 README，供手動以真實 LLM
  驗證前端風險卡渲染、evidence 引用與點擊定位條款等互動。（`7ccb1ae`）

### 003 雙視角風險規則與 Evidence 驗證（`specs/003-dual-perspective-risk-review/`）

- Added：`RiskRule`／`EvidenceRef`／`RiskAssessment`／`ReviewReport` 等 domain schema；
  `RiskRuleMatcher`、`ConservativeLanguageGuard`、`build_review_report`（純 Python，不呼叫 LLM）。
  （`452abdc`）
- Added：`OllamaRiskAssessmentProvider`、`ReviewDocumentCommand`（逐 (clause, rule) 評估、
  evidence／措辭驗證失敗最多重試一次後捨棄）、`POST /review`、`GET /report` API。（`452abdc`）
- Added：`data/risk_rules.seed.json`（32 筆規則，全數 `status: draft`，待人工審核）。（`452abdc`）
- Fixed：`ReviewDocumentCommand.max_retries` 加上 `__post_init__` 上限驗證（`0 <= max_retries <= 1`），
  對應 spec FR8「驗證失敗的風險最多重試一次」；由 Codex 覆核發現。（`1399c8c`）

### 002 LLM 條款分類與摘要（`specs/002-llm-clause-classification/`）

- Added：條款分類與白話摘要的 LLM provider adapter 與應用層命令。（`bf90f86`）
- Fixed：修正百分比數字 grounding 檢查的 false positive（真實 LLM 驗收時發現）。（`7ca8343`）

### 001 DOCX 條款抽取（`specs/001-docx-clause-extraction/`）

- Added：後端 DOCX 解析、條款切分與抽取。（`f5bfd1f`）

## 維護方式

新增功能或修 bug 時，於對應（或新增）spec 分類下加一行 `Added`／`Changed`／`Fixed`／`Removed`，
並附上 commit hash；不需為每個 commit 逐一列出，只記錄對使用者或後續開發者有意義的變動。
