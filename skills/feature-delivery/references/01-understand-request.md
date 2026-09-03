# 01 · 理解需求 Ticket

狀態：v0.1，可執行。[Feature Intent validator](../scripts/validate_feature_intent.py) 是 executable shape、source traceability 與 Intake gate 的 authority；[JSON Schema](feature-intent.schema.json) 是由 parity test 守護的 machine-readable mirror。Tracker source acquisition 與語意解讀仍是 `prose-only, unenforced`。

## 目的

把一張進行中的 Ticket 轉換成可追溯、可機械驗證、可判定是否能進入 Domain Graph lookup 的 `Feature Intent`。

這個步驟只回答：

> PO 想要什麼？Ticket 實際寫了什麼？哪些內容是 Agent 推論的？哪些問題仍未確認？

Ticket 是需求證據。PO 可以確認這張 Ticket 的 request intent，但 Ticket、PO 陳述與 Agent 推論都不會因此成為已確認的 Domain Truth、Feature Snapshot 或實作計畫。

## 輸入與 freshness

輸入至少包含 Ticket key、URL 或使用者提供的 Ticket 內容。Hub 在 `hub.yaml` 的 `request_source.kind` 宣告 request 來自哪個 tracker；source ID 一律使用中性的 `ticket:` prefix，不綁定特定產品。

依下列順序取得內容：

1. 優先使用 live Ticket。
2. 無法存取 live tracker 時，可使用使用者在對話中提供的 Ticket 內容，並標記 `freshness: provided`。
3. 只能使用可能過期的 tracker snapshot 時，標記 `freshness: snapshot`，並將 `intake_status` 設為 `incomplete`。

Agent 在這個步驟維持 tracker read-only。輸出預設回傳在當前對話中；呼叫者要求持久化時使用 `01-feature-intent.json`，否則不建立檔案或回寫 tracker。

## 1. 建立 source coverage

### 必須檢查的 Ticket 內容

對每一類來源記錄 `reviewed`、`unavailable` 或 `not_applicable`：

- core fields：key、URL、project、issue type、status、summary、description；
- acceptance criteria，無論它位於獨立欄位、description 或其他自訂欄位；
- routing metadata：component、labels、delivery lane、parent 或 epic；
- 所有可取得的 comments；
- 所有 attachments 的 metadata，以及 Ticket 明確引用或可能改變需求含義、scope、constraint、dependency、預期結果的 attachment 內容；
- 所有 linked issues 的 relation 與 key；若 Ticket 以 linked issue 表達 requirement、dependency、duplicate 或 supersession，再讀取該 linked issue 的相關內容。

空白欄位仍要記為 `reviewed`；Tracker 未使用的欄位記為 `not_applicable`。無法開啟但可能影響需求的來源記為 `unavailable`，不得用推論補齊。

### Source ID

live tracker 使用：

```text
ticket:<KEY>/fields
ticket:<KEY>/comments
ticket:<KEY>/attachments
ticket:<KEY>/links
ticket:<KEY>/field/<field-name>
ticket:<KEY>/comment/<comment-id>
ticket:<KEY>/attachment/<attachment-id>#<page-or-section>
ticket:<KEY>/linked/<LINKED-KEY>/field/<field-name>
```

使用者提供的內容使用相同路徑，但將 prefix 改為 `provided:`：

```text
provided:<KEY>/field/description
```

使用 snapshot 時將 prefix 改為 `snapshot:`。使用者只提供內容、沒有 tracker key 時，以 `UNKEYED` 作為穩定識別，例如 `provided:UNKEYED/field/description`。

每個 `reviewed` source 記錄 `id`、`kind`、`material`；能取得時一併記錄 `author` 與 `updated_at`。每個 `unavailable` 或 `not_applicable` source 記錄 `id` 與 `reason`。

### 來源衝突

Ticket field、comment、attachment 與 linked issue 沒有固定的真實性優先順序。只有已識別的 PO 或 request authority 明確表示某陳述取代另一陳述時，才能將它視為目前的 request intent；仍須保留新舊 source IDs。

時間較新的 comment 不會自動覆蓋較舊內容。無法確認 supersession 時，將差異記為 `contradicted`。

**完成判準：**每一類必須檢查的內容都已出現在 `source_coverage.reviewed`、`unavailable` 或 `not_applicable`，且每個 material source 都有穩定的 source ID。

## 2. 抽出需求結構

不判斷 domain correctness 或技術實作，抽出：

- `business_outcomes`：PO 預期改變的業務或使用者結果；
- `actors`：觸發或受到行為影響的人、角色或系統；
- `triggers`：行為開始的事件或條件；
- `actions`：要求的動作及其 object；
- `observable_results`：完成後可以由使用者、系統或測試觀察到的結果；
- `scope.included` 與 `scope.excluded`；
- `constraints`；
- `dependencies`；
- `domain_hooks.terms`：下一步可用來查找 Domain Graph 的 Ticket 用語。

不要為了填滿欄位而補造內容。無法建立的內容保留空值或空陣列，並在 `evidence.unknown` 說明缺口及是否阻擋 Domain Graph lookup。

**完成判準：**上述每個欄位都有 Ticket 支持的值，或有對應的 `unknown` 解釋為何沒有值；每個 action 同時包含 `verb` 與 `object`。

## 3. 區分證據與 Agent 解讀

將內容分成：

- `observed`：Ticket source 明確表達的內容；
- `inferred`：Agent 為了連接 Ticket 陳述而做出的解讀；
- `unknown`：理解需求所需，但目前尚未確認的問題；
- `contradicted`：來源之間尚未解決的不相容陳述。

每一項 `observed` 必須包含 `source_ids`。每一項 `inferred` 必須包含 `basis` 與支持該推論的 `source_ids`。每一項 `unknown` 必須說明 `reason_required` 與 `blocks_domain_lookup`。每一項 `contradicted` 必須包含 `question`、至少兩項互相衝突的 `claims`、各 claim 的 `source_ids`，以及 `blocks_domain_lookup`；Agent 不替 PO 選擇答案。

**完成判準：**所有 material statements 都只出現在符合其證據狀態的分類中，而且沒有 inference 被表達成 observed 或 confirmed Domain Truth。

## 4. 產出固定 Feature Intent

輸出必須保留以下所有 keys。未知 scalar 使用 `null`，沒有項目的 array 使用 `[]`；每個影響需求理解的 `null` 必須有對應的 `unknown`。`constraints` 與 `dependencies` 都是 string arrays。額外資料只能放在 `extensions`，避免每次執行自行改變 schema。

下列 YAML 是 non-canonical authoring example；欄位 authority 仍是 validator，執行時必須將同一結構序列化成 JSON。

```yaml
schema_version: feature-intent/v0.1
intake_status: ready_for_domain_lookup

ticket:
  key: TCK-123
  url: https://tracker.example.com/browse/TCK-123
  project: SHOP
  issue_type: Story
  status: Open
  summary: 提醒商品時可選擇尺寸
  freshness: live

request_type: feature

business_outcomes:
  - 顧客提醒商品時，系統保留其感興趣的尺寸

request_shape:
  actors:
    - 顧客
  triggers:
    - 顧客將商品加入 Reminder
  actions:
    - verb: 選擇
      object: 尺寸
  observable_results:
    - Reminder item 顯示並保留顧客選擇的尺寸

scope:
  included: []
  excluded: []

constraints: []
dependencies: []

domain_hooks:
  terms:
    - Reminder
    - product
    - size

evidence:
  observed:
    - statement: 顧客提醒商品時可以選擇尺寸
      source_ids:
        - ticket:TCK-123/field/description
  inferred:
    - statement: 選擇尺寸可能不是必填
      basis: Ticket 使用「可以選擇」的表述
      source_ids:
        - ticket:TCK-123/field/description
  unknown:
    - question: 尺寸為選填或必填？
      reason_required: 會改變 invalid cases 與 acceptance criteria
      blocks_domain_lookup: false
  contradicted: []

source_coverage:
  reviewed:
    - id: ticket:TCK-123/fields
      kind: collection
      material: false
      author: null
      updated_at: null
    - id: ticket:TCK-123/comments
      kind: collection
      material: false
      author: null
      updated_at: null
    - id: ticket:TCK-123/attachments
      kind: collection
      material: false
      author: null
      updated_at: null
    - id: ticket:TCK-123/links
      kind: collection
      material: false
      author: null
      updated_at: null
    - id: ticket:TCK-123/field/description
      kind: field
      material: true
      author: null
      updated_at: null
  unavailable: []
  not_applicable: []

extensions: {}
```

`request_type` 使用 `feature | change | bug | discovery | unknown`。`ticket.freshness` 使用 `live | provided | snapshot`。

## Intake gate

只有同時符合以下條件，`intake_status` 才能設為 `ready_for_domain_lookup`：

- source coverage 的完成判準已通過；
- `source_coverage.unavailable` 為空；
- `ticket.freshness` 是 `live` 或 `provided`；
- 至少有一項 `business_outcomes`；
- 至少有一個同時包含 `verb` 與 `object` 的 action；
- 至少有一項 `observable_results`；
- `domain_hooks.terms` 非空；
- 沒有 `blocks_domain_lookup: true` 的 unknown；
- 沒有 `blocks_domain_lookup: true` 的 unresolved contradiction；
- 每一項 material statement 都符合 source traceability 與證據分類規則。

任一條件未通過時，仍然輸出完整 Feature Intent，但將 `intake_status` 設為 `incomplete`，並在 `unknown`、`contradicted` 或 `source_coverage.unavailable` 中指出原因。

## Machine checks

每次產出後都執行：

```bash
python3 -B .domain-delivery/skills/feature-delivery/scripts/validate_feature_intent.py --input <01-feature-intent.json>
```

準備交給 Step 02 時加上 `--require-ready`。Exit `0` 表示 contract 有效且符合呼叫條件；exit `1` 表示 contract 有效但仍是 `incomplete`；exit `2` 表示 JSON、schema、traceability 或 gate 計算無效。

**Step 01 完成判準：**已輸出符合 `feature-intent/v0.1` 的 Feature Intent，validator exit `0`，且 `intake_status` 能由規則重算得到相同結果。只有 `ready_for_domain_lookup` 可以成為 Step 02 的輸入。

## 邊界

這個步驟的輸出是 request interpretation，不是需求核准。Step 01 本身不確認 Bounded Context、不查詢 Domain Graph、不透過 Codegraph 查 code、不選擇 repositories、不建立 BDD、不凍結 Feature Snapshot，也不開始 implementation。只有 active request 明確要求繼續 delivery、且 `--require-ready` exit `0` 時，Skill router 才能把相同 artifact 交給 Step 02。

Step 01 只列出待確認問題，不自行在 tracker 留言或詢問 PO。後續步驟再判斷問題能否由 Domain Graph 或 implementation evidence 解答，以及哪些問題必須回到 Ticket 請 PO 或 request authority 決定。
