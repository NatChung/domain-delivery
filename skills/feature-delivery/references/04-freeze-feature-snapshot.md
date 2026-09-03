# 04 · 通過 Domain Gate，凍結 Feature Snapshot

狀態：v0.1，可執行。`.domain-delivery/kernel/scripts/kernel.py freeze` 與 `verify-snapshot` 機械式 enforce committed graph reconstruction、confirmed L3 closure、authority、digests、repository-scoped required checks 與 immutable publication。Step 02 report 的比較品質與人類 confirmation 仍是 `prose-only, unenforced`；kernel 只相信 canonical Domain Graph 的已確認內容。

## 目的

把 active feature 所需的 confirmed Domain Graph closure 凍結為 immutable execution basis。Snapshot 後的 BDD、contracts、repository packets、implementation 與 evidence 都必須綁同一個 `snapshot_digest`。

## 進入條件

- `02-domain-comparison.md` 狀態為 `ready_for_snapshot`；
- selected roots 至少包含一個 capability 或 journey；
- roots、`requires` closure 與 authorities 全為 committed `confirmed L3`；
- 每個 executable node 有 preconditions、postconditions、invariants、invalid cases，且沒有 blocking question；
- Step 02 已為每個 selected executable rule 記錄 direct request trace，或 identified domain authority 的 whole-node acceptance reviewer、source 與 `accepted` decision；
- delivery lanes 與所有 affected repositories 已識別；
- 每個 repository 至少有一個 stable required check ID；
- 每個 required check 有 trusted attestor declaration。

Required check ID 在本步代表「交付前必須被證明的 obligation」。Step 05 只能 materialize 這些 IDs；若 Step 05 發現缺少 required check，必須建立 superseding snapshot，而不是在 snapshot 外新增 acceptance requirement。

## 1. 固定 graph basis

重新 compile 並取得 full graph commit：

```bash
python3 -B .domain-delivery/kernel/scripts/kernel.py compile \
  --source docs/domain --output domain-index/index.json

python3 -B .domain-delivery/kernel/scripts/kernel.py gate-index \
  --index domain-index/index.json

git rev-parse HEAD
```

必要 graph changes 必須已 commit。`freeze` 會從指定 commit 重建整份 index；working-tree-only 的確認內容、不同 commit 的 index 或被修改的 generated JSON 都會被拒絕。不要手改 `domain-index/index.json`。

## 2. 準備 freeze declaration

固定以下 inputs：

- lowercase feature ID；
- snapshot version，例如 `v1`；
- full 40/64-character graph commit；
- root node IDs；
- delivery lanes；
- repository IDs；
- `repository_id/check_id` required checks；
- trusted attestor identities；
- 新版本需要時的 prior `snapshot_digest`。

`app`、`web`、`server` 是 delivery lanes，不是 Bounded Contexts。Repository ID 只用於 delivery/evidence routing。

目前 CLI 的每個 `--trusted-attestor` 會套用到本次 freeze 的所有 required checks；若各 check 的 attestor policy 不同，先停止並調整 machine contract，不在 manifest 生成後手改。

## 3. 原子式 freeze

```bash
python3 -B .domain-delivery/kernel/scripts/kernel.py freeze \
  --feature <feature> \
  --version <v1> \
  --index domain-index/index.json \
  --node <root-node-id> \
  --delivery-lane <lane> \
  --repository <repository-id> \
  --required-check <repository-id/check-id> \
  --trusted-attestor <kind:name> \
  --graph-commit <full-commit> \
  --output specs/<feature>/snapshot/<v1>
```

多值 flags 重複傳入。Correction snapshot 加：

```text
--supersedes sha256:<prior-snapshot-digest>
```

Command 成功時一次產生：

```text
specs/<feature>/snapshot/<version>/
  DOMAIN.md
  domain-payload.json
  snapshot-manifest.json
```

既有 output directory 不會被覆寫。不要預先建立 version directory，也不要在 freeze 後修改其中任何檔案。

## 4. 驗證 snapshot

```bash
python3 -B .domain-delivery/kernel/scripts/kernel.py verify-snapshot \
  --snapshot specs/<feature>/snapshot/<version>/snapshot-manifest.json
```

只有 exit `0` 才通過 Domain Gate。Verification 會檢查：

- manifest/bundle/payload digests；
- exact committed root dependency closure；
- selected nodes 的 confirmed L3/authority coverage；
- graph commit 與 deterministic index；
- repositories、required checks、trusted attestors；
- snapshot self-digest。

`DOMAIN.md` 包含 selected closure 的完整 semantic fields/body，而不是 Step 02 自由改寫的摘要。v0.1 不支援從 node 中另選 statement subset：selected executable nodes 的全部 `scope`、`out_of_scope`、`preconditions`、`postconditions`、`invariants`、`invalid_cases` 都是 frozen acceptance basis，Step 05 必須全數覆蓋。若 whole node 太寬，先回 Domain lane refined node/slice，不在 Step 02 report 私下縮小。

Snapshot v0.1 不機械綁 Feature Intent/Domain Comparison digest；request-to-domain traceability 留在 `02-domain-comparison.md`，明標 `prose-only, unenforced`。

## 5. 變更與 drift

Snapshot 建立後，Domain Graph 可繼續更新。檢查 drift：

```bash
python3 -B .domain-delivery/kernel/scripts/kernel.py drift \
  --snapshot specs/<feature>/snapshot/<version>/snapshot-manifest.json \
  --index domain-index/index.json
```

- unrelated/global drift：報告，但不改 active snapshot；
- selected node drift：由人類分類是否 rebaseline；
- implementation 前發現錯誤 detail：建立 snapshot v2；
- implementation 中發現 contract 錯誤：停止 affected loops，建立 v2；
- 新 capability：新 feature/change request；
- code 違反有效 snapshot：bug fix。

## 完成判準

Step 04 只有在以下條件全部成立才完成：

- version directory 是新建立且未修改；
- `verify-snapshot` exit `0`；
- manifest 的 `feature`、roots、lanes、repositories、required checks 與 Step 02 ready report 一致；
- 記錄 `snapshot_digest`，供 Steps 05–08 使用。

最後一項一致性在 v0.1 是 `prose-only, unenforced`，因為 manifest 尚未 pin Step 02 digest。

## 失敗與停止條件

- `freeze` 因 candidate/L2/unknown authority 失敗：回 Step 02／decision packet；
- repo/check declaration 不完整：補 delivery routing；若 business acceptance requirement 改變，回 Domain lane；
- output version 已存在：選擇新 version，必要時使用 `--supersedes`；
- graph/index/commit 不一致：重新 compile/commit，不改 manifest；
- 真實 KC graph 尚無符合條件的 active slice 時，清楚回報 blocker，不用 synthetic fixture 冒充可交付 snapshot。

## 邊界

本步不產生 BDD、checker files、task packets 或 product code，也不執行 release。成功只建立 execution basis；它不代表 implementation 或 rollout 已完成。
