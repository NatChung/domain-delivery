# 05 · 從 Snapshot 投影 BDD 與 Executable Checks

狀態：v0.1，可執行。[Delivery Plan validator](../scripts/validate_delivery_plan.py) 是 Step 05/06 executable shape 與 planning gate authority；[JSON Schema](05-06-delivery-plan.schema.json) 是由 parity test 守護的 machine-readable mirror。本步機械式檢查 verified snapshot binding、required-check set equality、full frozen-rule coverage 與 source-rule references。BDD scenario adequacy、contract completeness 與 repository-native checker design 是 `prose-only, unenforced`，因為需要 semantic/technical review。

## 目的

把 immutable Snapshot 的 observable behaviour 與 contracts 投影成可交給各 product repository 實作的 numbered specifications，並為 Snapshot 已宣告的每個 required check 建立唯一 mapping。

Step 05 materialize Step 04 已凍結的 check obligations；它不能新增 business rule、repository 或 required check。

## 輸入

- `specs/<feature>/snapshot/<version>/snapshot-manifest.json`；
- 同目錄的 `DOMAIN.md` 與 `domain-payload.json`；
- `.domain-delivery/kernel/scripts/kernel.py verify-snapshot` exit `0`；
- manifest 中的 `snapshot_digest`、repositories、required checks、trusted attestors。

先執行：

```bash
python3 -B .domain-delivery/kernel/scripts/kernel.py verify-snapshot \
  --snapshot specs/<feature>/snapshot/<version>/snapshot-manifest.json
```

非 exit `0` 就停止；不對 invalid snapshot 產生 projection。

## 1. 建立 contract stack

依固定順序檢查 frozen nodes：

1. BDD examples：actors 可觀察的 Given/When/Then；
2. Design-by-Contract：preconditions、postconditions、invariants、invalid cases；
3. wire/schema contracts：delivery lanes/repositories 間 request/event/schema；
4. architecture contracts：dependency direction、ownership、brownfield ratchet；
5. repository-native quality checks。

每個 specification statement 必須指向 `domain-payload.json` 中的 exact node ID、field 與 statement，或指向 product repo 的明確 rule file。Repository rule 只能決定 implementation quality，不能加入 snapshot 沒有的 business meaning。整份 projection 的 `snapshot_rule_refs` union 必須覆蓋 selected executable nodes 的全部 `scope`、`out_of_scope`、`preconditions`、`postconditions`、`invariants`、`invalid_cases` statements；同一 rule 可被多 repo/check 重複引用。

BDD 是 Snapshot projection，不用來反向決定 Snapshot。若合理 scenario 需要 snapshot 未包含的 rule，停止並由人類分類是否建立 v2。

## 2. 編寫 numbered specifications

使用 Step 編號與 sequence，例如：

```text
05-01-reminder-behaviour.feature
05-02-reminder-contracts.md
05-03-reminder-wire-contract.md
05-04-reminder-architecture-contract.md
```

每個 BDD scenario 至少包含可觀察 Given/When/Then，並涵蓋 success、invalid/denied 與 relevant boundary cases。不要把 UI click sequence、private method 或特定 framework 寫成 business behaviour。

每個 contract specification 包含：

- source rule refs；
- owning repository/context；
- consumer/provider 或 dependency direction；
- observable pass/fail condition；
- brownfield baseline/ratchet treatment（若適用）；
- unresolved item。Unresolved business rule 會 block readiness。

## 3. 建立 `05-check-projection.json`

以下是 non-canonical authoring example；欄位 authority 仍是 validator：

```json
{
  "schema_version": "check-projection/v0.1",
  "projection_status": "ready_for_task_planning",
  "feature": "reminder-digest",
  "snapshot_digest": "sha256:<digest>",
  "projections": [
    {
      "projection_id": "05-reminder-service-unit-tests",
      "repository_id": "reminder-service",
      "check_id": "unit-tests",
      "layers": ["bdd", "design_by_contract", "native_quality"],
      "snapshot_rule_refs": [
        {
          "node_id": "capability:reminder",
          "field": "scope",
          "statement": "save customer reminder intent"
        },
        {
          "node_id": "capability:reminder",
          "field": "out_of_scope",
          "statement": "notification delivery"
        },
        {
          "node_id": "capability:reminder",
          "field": "preconditions",
          "statement": "customer identity is known"
        },
        {
          "node_id": "capability:reminder",
          "field": "postconditions",
          "statement": "reminder intent is retrievable"
        },
        {
          "node_id": "capability:reminder",
          "field": "invariants",
          "statement": "one saved intent per customer and item"
        },
        {
          "node_id": "capability:reminder",
          "field": "invalid_cases",
          "statement": "unknown item is rejected"
        }
      ],
      "repository_rule_refs": ["AGENTS.md#testing"],
      "specification_paths": ["05-01-reminder-behaviour.feature"],
      "planned_checker_path": "scripts/test.sh",
      "notes": []
    }
  ],
  "blocking_reasons": [],
  "extensions": {}
}
```

Allowed `layers`：`bdd`、`design_by_contract`、`wire_contract`、`architecture_contract`、`native_quality`。`snapshot_rule_refs.field` 只能是 `scope`、`out_of_scope`、`preconditions`、`postconditions`、`invariants`、`invalid_cases`。

每個 manifest `(repository_id, check_id)` 必須在 `projections` 恰好出現一次；同一 `check_id` 出現在不同 repositories 時仍是不同 obligation。每個 projection 至少有一個 snapshot 或 repository rule ref、至少一個 numbered specification path，以及一個 planned checker path；所有 projections 合計必須覆蓋全部 frozen executable rules。

## Projection gate

- `ready_for_task_planning`：snapshot verified；feature/digest 相符；required-check set exact match；所有 source refs resolve；spec files 已存在且完成 review；沒有 blocking reason。
- `incomplete`：尚有 required check/frozen rule 未投影或 review blocker；省略尚未完整的 projection item，保留其餘 valid items 並列出 `blocking_reasons`。一旦 item 已出現在 array，它的 refs/paths/checker shape 必須完整；宣告不存在的 file 或空 required field 是 invalid。

Extra repository/check/projection 不是 `incomplete`，而是 invalid contract，因為它會繞過 frozen acceptance basis。

## Machine check

```bash
python3 -B .domain-delivery/skills/feature-delivery/scripts/validate_delivery_plan.py \
  --snapshot specs/<feature>/snapshot/<version>/snapshot-manifest.json \
  --projection specs/<feature>/delivery/<version>/05-check-projection.json \
  --require-ready
```

Exit `0` 表示 projection contract valid/ready；exit `1` 表示 structurally valid 但 `incomplete`；exit `2` 表示 JSON、snapshot verification、binding、rule reference 或 check-set equality invalid。Validator 成功時輸出 projection canonical digest，供 Step 06 綁定。

Validator 檢查 numbered path declarations，但不判斷 BDD/contract 文字是否充分。執行 Agent 必須實際讀取 referenced files，不能把 manifest pass 當成 content review。

## 完成判準

- `verify-snapshot` exit `0`；
- `05-check-projection.json` 通過 `--require-ready`；
- 每個 frozen required check 的 layer、source basis、numbered specs 與 planned checker path 已定義；
- fresh review 沒有發現新增 business rule 或缺失 snapshot rule。

## 邊界

本步不開始 product-repo red/green loop、不聲稱 checker 已通過，也不記 evidence。實際 checker/test files 由 Step 07 依 repo-native seams 實作；Step 05 的 planned path 必須在 Step 06 packet 中一致。Step 08 kernel 尚不讀 planning artifacts，operator 對 checker path 的最後比對是 `prose-only, unenforced`。
