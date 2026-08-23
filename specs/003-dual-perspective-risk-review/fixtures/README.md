# 003 Fixtures

- `reviewed_test_rules.json`：僅供自動化測試與開發驗證使用的獨立小型規則集（已標記 `reviewed`），
  與正式 `data/risk_rules.seed.json` 無關，不得作為實際審閱依據。
- `risky-contract.docx`：自行建立、去識別化的測試合約，条款內容刻意命中
  `reviewed_test_rules.json` 全部 4 筆規則（`test-scope-change-001`／`test-acceptance-deemed-001`／
  `test-payment-currency-001`／`test-liability-cap-001`），供手動以真實 LLM 跑一次完整
  parse → classify → review 流程、驗證前端雙視角風險卡渲染時使用。

## 手動驗證步驟（前端視覺驗證用）

正式 `data/risk_rules.seed.json` 全數為 `draft`，直接跑只會得到 0 筆風險。若要重現有風險結果的畫面：

1. 備份 `data/risk_rules.seed.json`。
2. 暫時用本目錄的 `reviewed_test_rules.json` 覆蓋 `data/risk_rules.seed.json`。
3. 重啟後端（規則只在啟動時載入一次）。
4. 上傳 `risky-contract.docx`，執行完整審閱流程。
5. 驗證完成後，還原步驟 1 的備份並重啟後端；用 `git diff data/risk_rules.seed.json` 確認無殘留改動。

不得放入客戶合約、個資、真實金額、簽章或可識別的商業機密。
