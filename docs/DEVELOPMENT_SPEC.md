# 軟體開發合約審閱助手：開發規格與交接文件

> 狀態：MVP 規格（本地開發優先）  
> 語言／法域：繁體中文／台灣  
> 產品定位：輔助審閱與風險提示工具，**不是法律意見或法律結論**。

本文件定義產品需求；系統分層、規格目錄與 SDD 開發流程見
[SDD_ARCHITECTURE.md](./SDD_ARCHITECTURE.md)。所有功能實作前，須先建立對應 feature spec。

## 1. 目標與範圍

建立一個針對「軟體開發／系統委外承攬合約」的審閱助手。系統讀取合約草稿，將條款結構化，提供白話摘要，並同時以業主（甲方）與接案方／開發商（乙方）觀點呈現風險及應注意事項。

### MVP 必做

- 輸入 `.docx` 合約檔。
- 保留條號、段落、表格文字與原始位置。
- 將文件切分為完整語意條款。
- 將條款分類、產生白話摘要，並輸出受 Pydantic 驗證的 JSON。
- 以甲／乙雙視角產生風險分級、原因、建議與原文依據。
- 前端左側顯示合約原文、右側顯示審閱結果；點選風險可跳至對應條款。
- 視角切換不可重新解析文件或重新呼叫 LLM，只改變前端顯示的風險排序與凸顯。
- 初版 RAG：人工審核的雙視角風險規則庫。

### MVP 不做

- PDF、掃描檔與 OCR（後續版本）。
- `.doc` 舊格式；要求使用者先轉為 `.docx`。
- 合約版本比對、公司範本比對、自動產生修約條文。
- 多國法域、多種合約類型、多人協作與帳務功能。
- 以 AI 替代律師作出條款有效性／無效性或訴訟結果判斷。

## 2. 核心產品原則

1. **原文優先**：合約原文、金額、日期、條號不可由 LLM 改寫或杜撰。
2. **可追溯**：每一個摘要與風險都必須回指 `clause_id`、條號與段落位置。
3. **雙視角是資料層能力**：同一份條款只抽取一次；資料同時儲存甲方與乙方風險。
4. **Python 管結構、LLM 管語意**：切分、資料驗證、規則過濾與輸出彙整由程式控制。
5. **RAG 提供外部依據，不用來尋找目前合約內容**：目前合約須直接按完整條款分析。
6. **保守措辭**：使用「可能有疑慮」「建議確認」「可考慮協商」；禁止使用「本條無效」「一定會賠償」等斷言。
7. **最小資料留存**：合約內容不可寫入 console、一般 application log 或錯誤追蹤服務。

## 3. 使用者流程

```text
上傳 DOCX
  → 後端解析段落、標題、清單、表格
  → 推斷條號與階層，切成條款
  → LLM 分類與摘要（Pydantic 驗證）
  → 依條款類型檢索風險規則／法規依據
  → LLM 產生雙視角風險評估
  → judge 驗證每項判斷是否有原文支持
  → 儲存結果
  → 前端顯示原文與審閱面板
```

### 前端行為

- 預設視角可為「乙方」。
- 視角切換：`甲方` / `乙方`。
- 風險顏色：高＝紅色；中＝橘／黃色；低＝灰／藍灰；無＝不凸顯。
- 點擊風險卡片後，左欄捲動到對應 `clause_id` 並高亮。
- 每張風險卡都要顯示條號、風險等級、原文引用、說明、建議及來源（如有）。
- 永遠顯示「本服務僅提供輔助審閱與風險提示，非法律意見」免責聲明。

## 4. 建議本地技術棧

```text
frontend/  Vue 3 + Vite + TypeScript + Pinia + Vue Router + PDF.js（PDF 版才需）
backend/   Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy + Alembic
database/  PostgreSQL 16 + pgvector（Docker Compose）
storage/   本機檔案系統；之後可換 MinIO / Cloud Storage
llm/       Ollama API：gemma4:31b-cloud
docx/      python-docx + lxml（必要時讀取 OOXML metadata）
testing/   pytest、httpx、Vitest、Playwright（後期 E2E）
```

初期不需要 GPU，模型走 Ollama Cloud。所有 LLM 呼叫集中在一個 provider adapter，避免業務程式直接綁定特定模型或 SDK。

## 5. 專案建議目錄

```text
contract-review/
├── docs/
│   └── DEVELOPMENT_SPEC.md
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── stores/
│   │   ├── services/
│   │   └── types/
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── docx_parser.py
│   │   │   ├── clause_splitter.py
│   │   │   ├── llm_client.py
│   │   │   ├── review_service.py
│   │   │   ├── judge_service.py
│   │   │   └── retrieval_service.py
│   │   └── main.py
│   ├── tests/
│   └── pyproject.toml
├── data/
│   └── risk_rules.seed.json
├── docker-compose.yml
├── .env.example
└── README.md
```

## 6. 文件解析與條款切分

### DOCX 解析要求

- 讀取段落、Heading 樣式、編號清單與表格儲存格文字。
- 保留文件順序；不可只讀取 `document.paragraphs` 而遺漏表格中的條款。
- 上傳時產生不可變的文件快照與 `document_id`。
- 對每個原始段落產生 `source_index`；必要時保存 OOXML path。
- 若支援 Track Changes，必須明確要求使用者選擇「目前顯示版本」或「僅已接受修訂版本」；MVP 可先偵測到修訂後拒絕上傳並要求另存乾淨版本。

### 條號辨識

至少支援下列模式，並由階層高到低排序：

- `第壹條`、`第一條`、`第 1 條`
- `壹、`、`一、`、`1.`、`1、`
- `（壹）`、`(一)`、`（1）`、`(1)`

切分規則：

- 一個主條（例如「第五條 驗收」）是 parent clause。
- 條內子項可作 retrieval chunk，但風險顯示時要帶回主條完整內容。
- 沒有條號的前言、定義、附件必須保留，分類為 `other` 或作為上下文。
- 切分失敗時不可丟棄文字，建立 `unstructured-*` 條款並標記為待確認。

### Clause 位置資料

```python
class ClauseLocation(BaseModel):
    article_no: str | None = None
    heading: str | None = None
    source_start_index: int
    source_end_index: int
    paragraph_ids: list[str]
    table_refs: list[str] = []
```

## 7. 共享資料模型

所有枚舉值採用英文 machine value；前端再轉為繁中顯示。

```python
from enum import Enum
from pydantic import BaseModel, Field


class ClauseType(str, Enum):
    SCOPE = "scope"
    ACCEPTANCE = "acceptance"
    PAYMENT = "payment"
    IP = "ip"
    WARRANTY = "warranty"
    LIABILITY = "liability"
    TERMINATION = "termination"
    PENALTY = "penalty"
    CONFIDENTIALITY = "confidentiality"
    OTHER = "other"


class RiskLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class ExtractedClause(BaseModel):
    clause_id: str
    clause_type: ClauseType
    original_text: str = Field(min_length=1)
    location: ClauseLocation
    plain_summary: str
    confidence: float = Field(ge=0, le=1)


class EvidenceRef(BaseModel):
    clause_id: str
    quote: str = Field(min_length=1)
    rationale: str


class RiskAssessment(BaseModel):
    risk_id: str
    clause_id: str
    clause_type: ClauseType
    risk_for_client: RiskLevel
    risk_for_vendor: RiskLevel
    concern: str
    suggestion: str
    evidence: list[EvidenceRef] = Field(min_length=1)
    source_refs: list[str] = []
    confidence: float = Field(ge=0, le=1)
    requires_human_review: bool = False


class ReviewReport(BaseModel):
    document_id: str
    contract_title: str
    overall_summary: str
    disclaimer: str
    clauses: list[ExtractedClause]
    risks: list[RiskAssessment]
```

### 強制驗證規則

- `EvidenceRef.quote` 必須是 `original_text` 的子字串，否則拒絕該風險輸出。
- 每個 `RiskAssessment.clause_id` 必須存在於 `clauses`。
- `source_refs` 僅可引用 retrieval service 回傳的 ID，禁止 LLM 自行編造 URL 或法條。
- 模型輸出失敗時：最多修正重試一次；仍失敗則標記該條款「無法可靠分析」，不可輸出猜測結果。

## 8. 雙視角風險規則

每筆規則描述「觸發模式」及其對兩方的不同意義；不要寫成單一絕對好／壞判斷。

### 初始涵蓋主題

1. 工作範圍是否明確。
2. 是否有需求變更、追加報價與工期調整流程。
3. 驗收標準、期限與視為驗收。
4. 訂金、里程碑、尾款比例與逾期付款。
5. 成果、既有元件、第三方套件的智慧財產權。
6. 保固期間與 bug 修正／新增功能的邊界。
7. 賠償責任上限、間接損失及無上限責任。
8. 解約原因、已完成工作計價與交接。
9. 遲延罰則上限、不可歸責事由與付款遲延的對等性。
10. 保密義務、例外與競業限制範圍。

### 規則資料格式

`data/risk_rules.seed.json` 的每筆資料格式：

```json
{
  "id": "liability-unlimited-001",
  "version": 1,
  "jurisdiction": "TW",
  "clause_type": "liability",
  "topic": "無上限賠償責任",
  "trigger_patterns": [
    "應負一切損害賠償責任",
    "不限於直接或間接損失",
    "不以契約金額為限"
  ],
  "risk_for_client": "low",
  "risk_for_vendor": "high",
  "risk_explanation": "乙方可能承擔高於契約報酬的賠償風險。",
  "review_questions": [
    "是否設有賠償責任上限？",
    "是否排除間接損失、營業損失或預期利益？"
  ],
  "suggestion_template": "可考慮確認賠償責任是否設有合理上限，並釐清損害範圍。",
  "source_refs": [],
  "status": "reviewed",
  "updated_at": "2026-08-23"
}
```

## 9. RAG 規格

### 正確使用方式

- **不**把使用者當前上傳的合約放入向量庫，再用 RAG 找回條款。
- 對已切分的當前條款直接分析。
- RAG 僅取回外部依據：風險規則、台灣法規、經人工審核的案例與未來的公司標準條款。

### 知識庫分層與資料優先級

1. `risk_rules`：人工撰寫、人工審核的軟體合約風險規則（MVP 必做）。
2. `legal_sources`：官方法規原文、條號、生效日、官方 URL（第二階段）。
3. `practice_cases`：去識別化案例、判決摘要、經審核專業文章（第三階段）。
4. `organization_playbooks`：單一公司的範本與不可接受條件（企業版）。

不得將未審核網路文章、論壇內容或 LLM 自行生成的文字直接寫入知識庫。

### pgvector metadata

```text
knowledge_id, corpus, parent_id, title, content, clause_type,
jurisdiction, source_url, source_title, effective_date,
version, status, reviewed_by, updated_at, embedding
```

查詢時先以 `jurisdiction=TW`、`status=reviewed`、`clause_type` 過濾，再做向量檢索；回傳 top-k child chunks 時，同時取回其 parent document 與來源資料。

## 10. LLM 呼叫設計

### 模型角色

- 預設模型：`gemma4:31b-cloud`。
- 任務 A：條款分類與白話摘要。
- 任務 B：依條款原文與 RAG 依據產生雙視角風險。
- 任務 C：judge 檢查結論與原文引用是否相符。
- 高風險、低信心或 OCR（未來）案件可導向更高階模型或人工確認。

### Prompt 不可違反的規則

- 僅就提供的條款原文與檢索依據作答。
- 原文不可重寫為事實依據；所有事實引述必須逐字摘自輸入條款。
- 資訊不足時輸出 `requires_human_review=true`。
- 不得臆造法律、判決、法條、連結、金額、條號或當事人義務。
- 僅輸出符合 JSON Schema 的資料；後端仍須再做 Pydantic 與商業邏輯驗證。

### Judge gate

judge 的輸入為 `original clause + risk assessment + evidence + retrieved source IDs`。至少檢查：

- `evidence.quote` 是否存在於條款。
- 風險描述是否超出原文與來源支持。
- 甲／乙風險是否互相矛盾。
- 措辭是否構成不當法律結論。

未通過者：降低 confidence、標示人工確認，或移除該風險；不可靜默保留。

## 11. 初版 API

| Method | Path | 功能 |
|---|---|---|
| `POST` | `/api/documents` | 上傳 `.docx`，回傳 `document_id` 與處理狀態 |
| `GET` | `/api/documents/{document_id}` | 文件 metadata 與處理狀態 |
| `GET` | `/api/documents/{document_id}/clauses` | 原文條款與位置資訊 |
| `POST` | `/api/documents/{document_id}/review` | 啟動或重新啟動審閱工作 |
| `GET` | `/api/documents/{document_id}/report` | 取得完整 `ReviewReport` |
| `DELETE` | `/api/documents/{document_id}` | 刪除原始檔、解析資料、向量與報告 |
| `GET` | `/api/health` | 健康檢查，不可洩漏設定與金鑰 |

MVP 可採同步處理小文件；介面與資料表仍應保存 `status: uploaded | parsing | reviewing | completed | failed`，方便改成背景任務。

## 12. 安全與資料處理

- `.env` 僅供本機使用，建立 `.env.example`，並把 `.env` 放入 `.gitignore`。
- `OLLAMA_API_KEY` 不可出現在前端、Git、測試快照或 log。
- 限制上傳副檔名、MIME type 與檔案大小；解析前做惡意檔案防護。
- 合約文字不得寫入 access log、exception log、analytics 或 telemetry。
- 先實作資料刪除流程，確保可刪除原檔、抽取文字、條款、報告與向量資料。
- 若日後改用雲端 LLM，需在產品隱私告知中說明資料會送至模型服務；對資料不得出境的客戶，改採私有模型部署。

## 13. 實作里程碑與驗收條件

### M1：DOCX → 結構化條款

- 可上傳一份含標題、一般段落、條號與表格的繁中 `.docx`。
- 產出完整且排序正確的 clauses JSON。
- 每個條款有 `clause_id`、`original_text`、`location`。
- 不遺失表格文字；無法識別的內容標為 `unstructured`。

### M2：分類與摘要

- 每一條款都有受 Pydantic 驗證的 `ClauseType` 與摘要。
- 摘要不可出現原文未提及的金額、日期、義務或法律結論。
- 失敗時清楚顯示該條款無法可靠分析。

### M3：風險規則與雙視角審閱

- 建立至少 30 條 `reviewed` 風險規則。
- 每筆風險同時含 `risk_for_client` 與 `risk_for_vendor`。
- 所有風險至少有一段原文 evidence。
- 加入 judge gate，未通過的風險不可顯示為高可信結論。

### M4：Vue 審閱工作台

- 左側文件結構、右側風險清單。
- 甲／乙切換不發出新的分析 API request。
- 點擊風險能跳到並高亮相符的條款。
- 可依高／中／低風險與條款類型篩選。

### M5：本機容器化與可重現啟動

- `docker compose up` 可啟動 PostgreSQL + pgvector。
- 前後端 README 明確列出安裝、環境變數、migration 與啟動命令。
- 提供一份不含真實機密資料的測試 DOCX。

## 14. 後續版本

1. 原生 PDF：文字層擷取、頁碼與座標定位。
2. 掃描 PDF：逐頁文字層偵測、繁中 OCR、OCR 警示。
3. 台灣官方法規 RAG 與來源版本管理。
4. 公司標準範本／底線比對。
5. Word comments、Track Changes、修約建議與匯出附註版文件。
6. 登入、多租戶、權限、審計與雲端部署。

## 15. 給接手 Codex 的第一個任務

先不要做 RAG、帳號系統、PDF 或完整 UI。依 M1 實作以下垂直切片：

```text
上傳 DOCX → 擷取所有文字（含表格） → 依條號切成條款
→ 回傳符合 ExtractedClause 基本欄位的 JSON
→ Vue 顯示左欄條款清單
```

完成後，使用三份繁中軟體開發合約樣本測試：一份正常條號、一份條號混用、一份含重要表格條款。確認不遺失文字後，再進入 M2。
