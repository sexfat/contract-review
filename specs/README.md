# Feature Specs

本目錄依 Spec-Driven Development 管理可獨立驗收的功能規格。

## 編號規則

- 格式：`NNN-kebab-case-feature-name`。
- 編號依建立順序遞增，已刪除的 spec 編號不重用。
- 每個 feature 必須有 `spec.md`、`design.md`、`tasks.md`；需要對外資料格式時另建 `contracts/`。

## 開發順序

1. 完成 `spec.md` 並確認範圍與驗收條件。
2. 完成 `design.md`，記錄模組、資料、契約與測試策略。
3. 將工作拆入 `tasks.md`。
4. 依 tasks 實作與測試。
5. 在 spec 補上驗收結果與已知限制。

第一個 feature 為 `001-docx-clause-extraction`。
