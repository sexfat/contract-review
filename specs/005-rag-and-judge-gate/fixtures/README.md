# 005 Fixtures

- `example_legal_sources.json`：僅供開發／測試參考的 `legal_sources` 格式範例（3 筆，已標記
  `reviewed`），示範 `contracts/legal_source.schema.json` 的欄位用法與 parent／child chunking 政策：
  - `civil-227` / `civil-227-2`：parent／child 範例——`civil-227-2` 是針對「加害給付」語意較窄的 child
    片段（供 embedding 精準命中），`parent_id` 指回 `civil-227`；依 spec.md FR11，檢索命中 child 時應回傳
    parent 的完整原文，而非 child 片段。
  - `civil-492`：語意單一、不需拆項的範例，`parent_id: null`。

  與正式 `data/legal_sources.seed.json` 無關，不得作為實際審閱依據；正式資料的內容與 `status` 審核見
  spec.md「待人工完成事項」。

不得放入客戶合約、個資、真實金額、簽章或可識別的商業機密。
