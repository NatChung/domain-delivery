# 06 · 為各 Repository 建立 Task Packets

狀態：v0.1，可執行。[Delivery Plan validator](../scripts/validate_delivery_plan.py) 是 Step 05/06 executable shape 與 planning gate authority；[JSON Schema](05-06-delivery-plan.schema.json) 是由 parity test 守護的 machine-readable mirror。本步機械式檢查 Snapshot、Step 05 projection 與 repository packets 的 exact coverage/binding。Task ordering feasibility、repo-local seam choice 與 human workload judgment 是 `prose-only, unenforced`。

## 目的

把同一份 verified Snapshot 與 Check Projection 切成每個 product repository 可獨立執行的 bounded packet，保留跨 repo dependencies、wire contracts、native guides 與 Step 08 evidence inputs。

Task packet 是 orchestration artifact，不建立新的 business meaning。Snapshot 決定 behaviour；product repo 決定 implementation/test/architecture mechanics。

## 輸入

- verified `snapshot-manifest.json`；
- validator exit `0` 的 `05-check-projection.json` 與 numbered specs；
- 每個 snapshot repository 的 `AGENTS.md`、`CLAUDE.md`、README 與 documented production branch；
- Step 03 已確認的 cross-repo wire edges（若有）。

在每個 `codebases/<repo>/` 讀現有 guides；本步只建立 packets，不修改 product code。Planning artifacts 預設放在 `specs/<feature>/delivery/<snapshot-version>/`；`repository_path` 永遠相對 hub Git root，因此仍寫 `codebases/<repo>`。

## 1. 建立 repository ownership

每個 snapshot `repositories` 恰好建立一個 packet。Packet 只包含該 repo 的：

- delivery lane；
- Step 05 projection IDs；
- required check IDs；
- 呼叫者已確認的 public test seams；
- repository-relative checker paths；
- native test/contract/architecture commands or guide refs；
- upstream repository dependencies；
- cross-repo contract responsibilities；
- completion criteria；
- Step 08 要讀取的 checker/output paths。

Snapshot v0.1 只保存 lanes set 與 repositories set，沒有 repo→lane mapping。Validator 只檢查 packet lane 屬於 snapshot lanes；正確 mapping 由 Step 02 routing evidence/review 判斷，屬於 `prose-only, unenforced`。

同名 `check_id` 在不同 repositories 仍是兩個 obligations。不要用一個「server packet」合併多個 backend repos。

## 2. 定義 execution order

`depends_on_repositories` 只表示 Step 07 必須先取得的 contract/implementation dependency，必須形成 acyclic ordering。雙向協作或共同 wire contract 寫入 `cross_repo_contracts`，不要建立 dependency cycle。

可以安全平行的 packets 保持無 dependency；跨 repo interface 先由 provider/contract owner 完成 red contract，再讓 consumers 對同一 contract 執行。Ordering 是 delivery coordination，不改 snapshot semantics。

## 3. 寫 completion criteria

每個 packet 的 criteria 至少包含：

- repo guides/production branch 已確認；
- 每個 assigned projection 有 red test/contract；
- minimal implementation 使 assigned checks green；
- refactor 後 native quality/architecture checks 仍 pass；
- brownfield ratchet 沒有新增 violation；
- snapshot contradiction 已停止並回報，不被 baseline 例外吞掉；
- fresh review 無 blocking finding；
- 每個 required check 的 checker/output file 可供 Step 08 綁定。

不要在 packet 寫泛稱「tests pass」；列出 stable `check_id`、guide/command source 與 observable output。

## 4. 建立 `06-repository-task-plan.json`

以下是 non-canonical authoring example；欄位 authority 仍是 validator：

```json
{
  "schema_version": "repository-task-plan/v0.1",
  "planning_status": "ready_for_repository_loops",
  "feature": "reminder-digest",
  "snapshot_digest": "sha256:<snapshot-digest>",
  "projection_digest": "sha256:<05-check-projection canonical digest>",
  "packets": [
    {
      "packet_id": "06-reminder-service",
      "repository_id": "reminder-service",
      "repository_path": "codebases/reminder-service",
      "delivery_lane": "server",
      "base_ref": "main",
      "repo_guides": ["AGENTS.md", "README.md"],
      "test_seams": ["public reminder command and query interfaces"],
      "projection_ids": ["05-reminder-service-unit-tests"],
      "required_checks": ["unit-tests"],
      "depends_on_repositories": [],
      "cross_repo_contracts": [],
      "completion_criteria": ["unit-tests produces a fresh exit code and output"],
      "evidence_inputs": [
        {
          "check_id": "unit-tests",
          "checker_file": "scripts/test.sh",
          "output_file": "/tmp/07-reminder-service-unit-tests.txt"
        }
      ],
      "notes": []
    }
  ],
  "blocking_reasons": [],
  "extensions": {}
}
```

`packet_id` 以 `06-` 開頭；由 Step 07 產生的 output filename 以 `07-` 開頭。`repository_path`、`repo_guides`、`checker_file` 都是相對對應 product repo/hub 的安全路徑；`output_file` 必須使用絕對 `/tmp/07-<descriptive-name>`，Step 08 前不可遺失，且長期 artifact retention 由外部 adapter 負責。

每個 packet 的 `required_checks` 與 `evidence_inputs.check_id` 必須完全等於 snapshot 對該 repo 宣告的 check set。`checker_file` 必須等於 Step 05 對同一 pair 的 `planned_checker_path`。所有 projection IDs 在整份 plan 恰好被指派一次。

## Planning gate

- `ready_for_repository_loops`：exactly one packet per snapshot repo；projection/check/evidence coverage exact；repo paths/guides exist；public test seams 已由呼叫者確認；dependency graph acyclic；所有 completion criteria 非空；沒有 blocker。
- `incomplete`：尚有 repository packet 未能完整建立；省略該 packet，保留其他 valid packets 並列出 `blocking_reasons`。一旦 packet 已出現在 array，它的 guide/base-ref/seam/criterion/evidence fields 必須完整且 paths 可解析；malformed declared packet 是 invalid。

Extra repo/check/projection、wrong digest、duplicate assignment、self/cyclic dependency 是 invalid contract，不是普通 incomplete。

## Machine check

```bash
python3 -B .domain-delivery/skills/feature-delivery/scripts/validate_delivery_plan.py \
  --snapshot specs/<feature>/snapshot/<version>/snapshot-manifest.json \
  --projection specs/<feature>/delivery/<version>/05-check-projection.json \
  --task-plan specs/<feature>/delivery/<version>/06-repository-task-plan.json \
  --require-ready
```

Exit `0` 表示 task plan valid/ready；exit `1` 表示 structurally valid 但 `incomplete`；exit `2` 表示 snapshot/projection invalid、binding mismatch 或 plan contract invalid。成功時輸出 task-plan canonical digest。

## 完成判準

- validator `--require-ready` exit `0`；
- 每個 product repo 的 guides 已讀，packet 沒有複製其他 repo 的 command；
- cross-repo contract ownership/order 明確，或明列 blocker；
- 每個 Step 08 evidence input 已對應 frozen repository/check 與 Step 05 checker path；
- 執行順序與可平行 packets 已向呼叫者說明。

## 邊界

本步不 checkout/修改 product repo、不執行 tests、不建立 pass result、不記 evidence。Task plan ready 只表示 work routing 完整；Step 07 必須在每個 repo 重新讀 guides、確認 branch/state，並執行 native Agent Loop。
