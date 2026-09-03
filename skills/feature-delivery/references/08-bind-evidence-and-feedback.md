# 08 · 收集 Evidence，完成交付並回饋 Domain Graph

狀態：v0.1，可執行。`.domain-delivery/kernel/scripts/kernel.py` 機械式綁定 Snapshot、repository/check、checker bytes、repo commit/dirty state、output bytes、performer declaration、independent attestation declaration與 hash chain。Actor authentication、artifact retention、terminal-hash anchoring、release decision 與 Domain feedback confirmation 是 `prose-only, unenforced`，因為它們屬於外部平台或人類 authority。

## 目的

把 Step 07 的真實 checker/output/repo state 追加為可驗證 evidence，確認所有 frozen required checks 都有 exit `0` 與 trusted independent attestation，並把 delivery 新知送回持續演進的 Domain lane；不重寫 active Snapshot。

## 進入條件

- Step 04 snapshot `verify-snapshot` exit `0`；
- Step 05/06 validator `--require-ready` exit `0`；
- 每個 required check 都有 Step 07 fresh checker、raw `/tmp/07-...` output 與真實 exit code；
- performer identity 與 snapshot trusted attestor identity 分離；
- surrounding adapter 能 authentication identities、保存 artifacts，並 retain/sign terminal hash。

若只能做 local declaration，仍可建立 ledger，但最終狀態必須寫 `kernel_verified_unanchored`，不能聲稱 cryptographic proof 或完整可信交付。

Step 07 exit `1/2/3` 可進本步只為保存 failed-run evidence；這條路最後狀態必須是 `failed`，不會讓 delivery progress 越過 non-ready gate。

## 1. 建立 numbered run

每次 delivery/evidence attempt 使用新 run ID，例如：

```text
evidence/<feature>/08-run-001/check-ledger.jsonl
```

Ledger 是 append-only hash chain。不要共用不同 snapshot digest 的 ledger，也不要手改、排序或刪除既有 entries。

## 2. 記錄每個 required result

先從 snapshot manifest 列出 exact `(repository_id, check_id)`。只記錄這些 frozen pairs；目前 kernel 可 append extra pair，但 extra result 不受 Snapshot 授權，也不能作為 completion evidence。

對每個 pair，operator 依 Step 06 確認：

- `checker_file` 等於 Step 05 `planned_checker_path`；
- `output_file` 等於 Step 06 `evidence_inputs`；
- exit code 是 Step 07 同一次 fresh run 的真實結果。

這個 planning→evidence checker-path linkage 在 v0.1 是 `prose-only, unenforced`：kernel 會 hash caller 提供的 checker bytes，但不讀 `05-check-projection.json` 或 `06-repository-task-plan.json`。路徑不一致就停止，不把 kernel entry valid 誤稱為 planned check valid。

然後執行：

```bash
python3 -B .domain-delivery/kernel/scripts/kernel.py record-result \
  --ledger evidence/<feature>/08-run-001/check-ledger.jsonl \
  --snapshot specs/<feature>/snapshot/<version>/snapshot-manifest.json \
  --repository-id <repository-id> \
  --check-id <check-id> \
  --exit-code <0|1|2|3> \
  --repo-path codebases/<repository> \
  --checker-file codebases/<repository>/<checker-file> \
  --output-file /tmp/07-<repository>-<check>.txt \
  --performed-by <kind:name>
```

Kernel 會計算 checker/output digest、repo full commit 與 dirty-state digest；呼叫者不能自行提供這些值。保存 stdout 回傳的 result entry hash。

同一 pair 重跑時可 append 新 result；`verify-evidence` 以 ledger 中最後一筆該 pair result 判定 required gate，因此 attestation 必須指向最新要採用的 result。

## 3. 加入 independent attestation declaration

Trusted attestor 先由外部 adapter 驗證身份、獨立檢查 result/output，並產生 numbered artifact，例如 `/tmp/08-<repo>-<check>-attestation.json`。再執行：

```bash
python3 -B .domain-delivery/kernel/scripts/kernel.py declare-attestation \
  --ledger evidence/<feature>/08-run-001/check-ledger.jsonl \
  --snapshot specs/<feature>/snapshot/<version>/snapshot-manifest.json \
  --result-hash <result-entry-hash> \
  --declared-by <trusted-kind:name> \
  --declaration-mode <ci_declaration|signature_declaration|human_declaration> \
  --attestation-file /tmp/08-<repo>-<check>-attestation.json
```

Performer 不能 attest 自己的 result。Kernel 驗證 declared identity 是否列在該 check 的 trusted attestors，但 identity string 本身不是 authentication；attestation bytes digest 也不自動證明內容真實。

## 4. 驗證 evidence gate

```bash
python3 -B .domain-delivery/kernel/scripts/kernel.py verify-evidence \
  --ledger evidence/<feature>/08-run-001/check-ledger.jsonl \
  --snapshot specs/<feature>/snapshot/<version>/snapshot-manifest.json
```

只有 exit `0` 表示 kernel evidence gate 通過。Required check 必須同時有：

- exact snapshot/repository/check binding；
- latest result exit `0`；
- trusted、independent、指向該 result 的 attestation declaration；
- valid chain/digests。

Exit `1`、`2`、`3`、missing result、untrusted/self attestation 都不通過。`record-result` 成功只代表一筆 valid entry 被追加，不代表 check pass 或整體 delivery complete。

## 5. 保存 artifacts 與 anchor terminal hash

Ledger 只保存 digests，不保存 checker/output/attestation bytes。External adapter 必須：

- 保存每筆 result 使用的 checker、raw output 與 attestation artifact；
- 綁定 artifact URI/retention policy（目前在 hub 外，`prose-only, unenforced`）；
- 取得 ledger 最後一筆 `entry_hash`；
- 將 terminal hash retain 或 sign 到可信外部系統；
- 記錄 authenticated performer/attestor context。

若 `/tmp` artifacts 尚未保存，不刪除或宣稱 run 可重現。沒有 external anchor 時，ledger 只有 tamper-evident，不是 tamper-proof。

## 6. 產出 `08-domain-feedback.md`

把 delivery 中發現的 domain learnings 使用 numbered file 回到 Domain lane：

```markdown
# 08 · <feature> Domain Feedback

- Snapshot digest: sha256:<digest>
- Evidence run: evidence/<feature>/08-run-001/check-ledger.jsonl
- Evidence status: failed | kernel_verified_unanchored | verified_and_anchored
- Terminal hash: sha256:<entry-hash>
- External anchor: <URI/reference or unavailable>

## Confirmed implementation observations
## Domain candidates
## Contradictions
## Proposed node changes
## Decision packets
## Drift classification
## Release/rollout handoff
## Enforcement notes
```

名稱中的「Confirmed implementation observations」只表示 code/evidence 已觀察，不是 confirmed Domain Truth。新 business meaning 在 handoff 中列為 candidate/disputed input；decision packet、canonical node 與 authority confirmation 都路由 `$domain-graph`，Step 08 不直接建立或更新它們。

把完成的 `08-domain-feedback.md` 交給 `$domain-graph`。該 Skill 可在另有
graph-write authority 時更新 `docs/domain/**`、regenerate index 並回傳
committed full SHA；Feature Delivery 本步永遠不修改 canonical graph 或已凍結
Snapshot。若 correction 影響 active/released basis，由人類依 workflow 分類
bug、corrective change、new feature 或 snapshot v2。

## 7. Drift 與 delivery status

Domain Skill 完成 graph update 後，drift calculation 也由該 Skill 依 exact
Snapshot path 執行：

```bash
python3 -B .domain-delivery/kernel/scripts/kernel.py compile \
  --source docs/domain --output domain-index/index.json

python3 -B .domain-delivery/kernel/scripts/kernel.py drift \
  --snapshot specs/<feature>/snapshot/<version>/snapshot-manifest.json \
  --index domain-index/index.json
```

Drift 只報告 global/selected node change，不自動 rebaseline。Release/rollout 仍由 delivery/release owner 決定；evidence gate pass 不等於 deployment success。

## 完成判準

Step 08 狀態依序為：

- `failed`：`verify-evidence` 非 exit `0`；
- `kernel_verified_unanchored`：kernel exit `0`，但 actor authentication、artifact retention 或 terminal anchor 未完成；
- `verified_and_anchored`：kernel exit `0`，artifacts retained、actors authenticated、terminal hash 已由可信外部系統 retain/sign。

只有最後一個狀態可稱為這套 evidence contract 的完整完成。即使如此，release/rollout acceptance 仍是獨立的人類/平台決策。

## 邊界

本步不把 ledger 當成 Domain authority、不自動 confirm feedback、不原地修改 Snapshot，也不因歷史 success、N/A 或缺少 check 而放行。Ticket discussion 仍先留在 ticket；需要 Slack 通知時只請對方去看 ticket，不在 Slack 複述完整決策內容。
