# 02 · 對照 Domain Graph

狀態：v0.1，可執行。Domain Graph compile/index shape 由 `.domain-delivery/kernel/scripts/kernel.py` 機械式檢查；Feature Intent 與 Domain Graph 的語意 matching、decision packet 品質及 human confirmation 是 `prose-only, unenforced`，因為這些需要 PM/domain judgment。真正的 active-slice Domain Gate 由 Step 04 的 `freeze` 原子式執行，不是 `gate-index`。

## 目的

把 Step 01 的 request interpretation 對照目前 Domain Graph，找出可直接採用的 confirmed rules、缺少或衝突的 domain meaning，以及只靠 implementation evidence 才能回答的技術問題。

這個步驟只產生比較與決策輸入，不把 Ticket、code 或 Agent 推論提升為 Domain Truth。

## 輸入

- 一份 `feature-intent/v0.1` JSON；
- `docs/domain/**` canonical Markdown；
- 由相同工作樹產生的 `domain-index/index.json`；
- 必要時使用 `CONTEXT-MAP.md`、`docs/domain/INDEX.md` 與 repo workflow 文件理解 graph maturity。

先執行：

```bash
python3 -B .domain-delivery/skills/feature-delivery/scripts/validate_feature_intent.py \
  --input <01-feature-intent.json> --require-ready

python3 -B .domain-delivery/kernel/scripts/kernel.py compile \
  --source docs/domain --output domain-index/index.json

python3 -B .domain-delivery/kernel/scripts/kernel.py gate-index \
  --index domain-index/index.json
```

任一 command 非 exit `0` 就停止。`gate-index` 只表示整份 index 結構與引用有效；candidate/disputed/L0–L2 nodes 仍可通過，不能稱為 Domain Gate passed。

## 1. 建立 comparison set

用 Feature Intent 的 `domain_hooks.terms`、business outcomes、actors、actions、objects、observable results、scope、constraints 與 dependencies 尋找相關 nodes。檢查 `related_nodes` 只作 navigation；沿 `requires` 建立可能進入 snapshot 的 dependency closure。

每個相關 node 分為：

- `exact`：現有 node 明確涵蓋 request statement；
- `partial`：只有部分語意或 boundary 相符；
- `missing`：graph 沒有可承載該 statement 的 node；
- `conflicting`：request 與 graph、或 graph nodes 彼此不相容；
- `context_only`：有助導航，但不屬於 active slice。

每項 comparison 記錄 Feature Intent statement/source、node ID、node status/readiness、匹配理由及未涵蓋部分。只有 `confirmed` node 是已接受語意；`candidate`、`disputed` 與 `superseded` 都不能當作 acceptance basis。

**完成判準：**Feature Intent 中每個 material business outcome、action、observable result、included/excluded scope、constraint 與 dependency 都有 comparison 結果，或明確列為 graph gap。

## 2. 提出 active slice

以 capability 或 journey 作為 root candidate，列出：

- root node IDs；
- `requires` closure；
- 每個 non-authority node 的 authority reference；
- selected nodes 的 status/readiness；
- selected executable nodes 的全部 scope/out-of-scope、preconditions、postconditions、invariants 與 invalid cases，並標示哪些直接對應 request；v0.1 snapshot 凍結 whole-node basis，不另切 statement subset；
- delivery lanes、repositories 與跨 repo wire contracts 的已知/未知狀態。

`related_nodes` 不自動進入 slice。repository、service、App/Web/Server lane 不能被當成 Bounded Context。若 feature-specific rule 沒有存在於 confirmed Domain Graph node，先補 candidate/decision，而不是把它只寫進 comparison report 後直接 snapshot。

對 whole-node basis 做 authority review：

- `reviewed_by` 必須是 selected closure 已識別的 PM/domain authority；request authority 只有在同時具備該 domain authority 身分時才可接受 domain meaning；
- `review_source` 必須是可追溯的 tracker comment、decision record、知識庫章節 或其他穩定 evidence ref；
- 每個未直接對應 Feature Intent 的 executable rule 都記錄 `accepted` 或 `blocking`、reviewer、source 與理由；Agent 不能代填接受結果；
- 這個 review record 是 `prose-only, unenforced`，因為 kernel 只能驗證 node confirmation 與 closure，不能驗證某位 authority 是否實際 review 本 feature 的 whole-node basis。

**完成判準：**每個 proposed root 的 dependency/authority closure 都已列出；每項 feature acceptance statement 都能追到 selected node 的明確欄位，或被列成 blocking question；每個 selected executable rule 都有 direct request trace，或有 identified domain authority 的 `accepted` review record。任何缺少 reviewer、source 或 decision 的 rule 都是 blocker。

## 3. 分流問題

每個未解問題只選一個 owner type：

- `request_authority`：Ticket 想要什麼、scope 或 observable result 不清楚；回既有 ticket；
- `domain_authority`：business meaning、policy、boundary、term、exception 或 ownership 需確認；建立 numbered question/evidence handoff，路由 `$domain-graph` 準備 decision packet；
- `implementation_investigation`：目前 caller/callee、wire contract、受影響 symbols、repo routing 或 brownfield constraint 未知；進 Step 03；
- `delivery_owner`：capacity、release、rollout 或 operational sequencing；不靠 Domain Graph 決定。

Codegraph 只能回答 `implementation_investigation`。它不能替 request/domain authority 選擇語意答案。

## 4. 建立 Domain lane handoff

每個 domain blocker 使用編號檔名，例如 `02-domain-question-01-reminder-identity.md`，並包含：

- exact question；
- candidate answer 與 alternatives；
- evidence for/against，保留 Feature Intent source IDs、Domain node IDs 或 code evidence refs；
- affected journeys、contracts、repositories；
- delay consequence；
- named authority；未知時寫 `unknown`，node 維持 `candidate`。

把 handoff 交給 `$domain-graph`。該 Skill 擁有 decision packet、authority
outcome record、canonical `docs/domain/**` write、compile/gate-index 與 graph
commit readiness；Feature Delivery 不在 Step 02 直接修改 graph。Authority
回答後也由 Domain Skill 驗證 confirmation metadata、scope 與 L3 rules。只有
Domain Skill 回傳實際 committed full SHA 後，才回本步重讀 current index、
重做 matching 與 status calculation。

新 graph rule 若尚無 machine enforcement，必須在相關文件標記 `prose-only, unenforced` 與原因。

## 5. 產出 `02-domain-comparison.md`

輸出使用以下固定 sections；預設回傳於對話，呼叫者要求保存時使用 `02-domain-comparison.md`：

```markdown
# 02 · <feature> Domain Comparison

- Status: needs_domain_decision | needs_implementation_evidence | ready_for_snapshot
- Feature Intent: <path or conversation artifact ID>
- Feature Intent SHA-256: sha256:<digest of exact JSON bytes>
- Graph commit: <full commit or pending>
- Graph index digest: sha256:<digest>

## Comparison coverage
## Proposed active slice
## Selected feature rules
## Whole-node acceptance review
## Blocking questions
## Implementation questions
## Domain lane handoffs
## Delivery routing
## Enforcement notes
## Next step
```

若 Domain Graph 有尚未 commit 的必要確認內容，`Graph commit` 寫 `pending`，狀態不能是 `ready_for_snapshot`。Digest 記錄只提供 traceability，v0.1 尚未由 machine validator 綁入 snapshot，因此標記 `prose-only, unenforced`。

## Status rule

依下列順序決定唯一狀態：

1. 有 blocking request-authority question：`needs_domain_decision`；implementation evidence 不能代替 request clarification。
2. 有 blocking domain question，且某個已編號 technical question 的 expected evidence 能區分 alternatives 或實質改變 decision packet：`needs_implementation_evidence`，並保留 domain question 等 Step 03 回來後決定。
3. 有 blocking domain question，但沒有前項 evidence dependency：`needs_domain_decision`。
4. 沒有 request/domain blocker，但有會改變 node selection、routing、contract 或 impact 的 implementation question：`needs_implementation_evidence`。
5. selected roots 與完整 closure 均為 committed `confirmed L3`、每個 selected executable rule 都有 direct request trace 或完整的 whole-node authority review record、沒有 blocking contradiction，且 lanes/repositories/required check declarations 足以 freeze：`ready_for_snapshot`。

這個 precedence 讓 mixed case 只有在 technical evidence 對 domain decision 有明確用途時才先進 Step 03，避免無目的掃 code。

## Machine checks

Graph 更新由 `$domain-graph` 執行 `compile`、`gate-index` 並提供 committed
full SHA。回到本步後重新讀該 commit 的 index。準備 Step 04 時使用 report
中的 roots、lanes、repositories、required checks 與 attestors 執行
`freeze`；只有 `freeze` 成功且 `verify-snapshot` exit `0` 才是機械式
Domain Gate pass。

## 邊界與停止條件

- `needs_implementation_evidence` 只進 Step 03，完成後必須回本步重做 comparison。
- `needs_domain_decision` 停止自動推進，路由 `$domain-graph` 並將完整問題留在正確 ticket；沒有明確寫回授權時不自行留言。
- `ready_for_snapshot` 才能進 Step 04。
- 本步不建立 BDD、不修改 product code、不凍結 snapshot，也不把 `gate-index` exit `0` 表述成 business approval。
