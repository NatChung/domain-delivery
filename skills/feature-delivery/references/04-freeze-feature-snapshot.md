# 04 · 凍結 domain 或 UI Feature Snapshot

狀態：v0.1，可執行。`.domain-delivery/kernel/scripts/kernel.py freeze` 與 `verify-snapshot` 機械式 enforce committed graph reconstruction、confirmed L3 closure、authority、digests、repository-scoped required checks 與 immutable publication。Step 02 report 的比較品質與人類 confirmation 仍是 `prose-only, unenforced`；kernel 只相信 canonical Domain Graph 的已確認內容。

## 目的

把 active feature 所需的 confirmed Domain Graph closure 凍結為 immutable execution basis。Snapshot 後的 BDD、contracts、repository packets、implementation 與 evidence 都必須綁同一個 `snapshot_digest`。

## Domain kind 進入條件

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

Domain kind 只有 exit `0` 才通過 Domain Gate。UI verification 不代表 Domain Gate。Verification 會檢查：

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

## Domain kind 完成判準

Step 04 domain kind 只有在以下條件全部成立才完成：

- version directory 是新建立且未修改；
- `verify-snapshot` exit `0`；
- manifest 的 `feature`、roots、lanes、repositories、required checks 與 Step 02 ready report 一致；
- 記錄 `snapshot_digest`，供 Steps 05–08 使用。

最後一項一致性在 v0.1 是 `prose-only, unenforced`，因為 manifest 尚未 pin Step 02 digest。

## Domain kind 失敗與停止條件

- `freeze` 因 candidate/L2/unknown authority 失敗：回 Step 02／decision packet；
- repo/check declaration 不完整：補 delivery routing；若 business acceptance requirement 改變，回 Domain lane；
- output version 已存在：選擇新 version，必要時使用 `--supersedes`；
- graph/index/commit 不一致：重新 compile/commit，不改 manifest；
- Hub 的真實 graph 尚無符合條件的 active slice 時，清楚回報 blocker，不用 synthetic fixture 冒充可交付 snapshot。

## 邊界

本步不產生 BDD、checker files、task packets 或 product code，也不執行 release。成功只建立 execution basis；它不代表 implementation 或 rollout 已完成。

## UI kind：accepted request → immutable Snapshot

此 additive contract 見 [ADR 0010](../../../docs/adr/0010-ui-feature-snapshot-kind.md)
（Proposed）。純 UI／copy／style／明確 bug 可走 UI；含業務規則、跨系統、資料或權限
變更，以及不確定範圍者，必須回 domain 流程。明確 bug 只修復既有明確接受行為。
UI 路徑不要求 Step 02 Domain Comparison、Graph journey/capability 或 L3 closure。
不得把 UI verification 稱為 domain confirmation 或 Domain Gate。

先由具名人類接受原始 request、全部 AC 及分類；接受文件必須含：

- `request` 原文、`request_digest`（精確 UTF-8 bytes 的 SHA-256，不 trim）；
- `acceptance_criteria` 非空陣列，每項 `id`（唯一 `ac:` ID）、`text` 原文及 `digest`；
- `accepted_by`（具名 `human:`，不可 agent／role）、帶時區 `accepted_at`、`source`；
- `scope.category`（ui/copy/style/explicit_bug）、`rationale`，以及全部為 boolean false 的
  `business_rules`／`cross_system`／`data_changes`／`permission_changes`。

Kernel 拒絕缺接受、digest 不符、excluded scope、domain nodes/roots 或 Graph flags。
人類對分類的誠實性、source 真實性與身分驗證是 **prose-only, unenforced**：本機 parser
不能判斷任意文字的業務語意，也不能驗證人類身分。接受前須審查全部原文；後續發現
excluded scope 就停止並建立 domain Snapshot，不在 UI check 中私加業務規則。

```bash
python3 -B .domain-delivery/kernel/scripts/kernel.py freeze \
  --kind ui --accepted-request <accepted-request-json> \
  --feature <feature> --version <v1> \
  --delivery-lane <lane> --repository <repository-id> \
  --required-check <repository-id/check-id> --trusted-attestor <kind:name> \
  --output specs/<feature>/snapshot/<v1>
```

輸出為 schema v2 `kind: ui` manifest、`UI.md`、`ui-payload.json`，nodes/roots 為空。
Lanes/repos/checks/attestors 與 domain 相同要求。UI 不使用 Graph pin；其 acceptance
basis 是凍結的 accepted request，不是 Graph 規則。使用同一 `verify-snapshot` 指令
驗證原文 digests、payload、rendered bundle、routing 與 snapshot digest，exit 0 才能進
Step 05。輸出目錄不可覆寫；更正以 `--supersedes` 新版本處理，Graph drift 不適用。
既有 v1 missing-kind domain Snapshot 的 bytes 與語意維持不變。

### UI kind 完成判準與失敗路由

- 具名 human 接受全部 request/AC 原文與分類，source 可追溯；
- 新 version directory 未被改寫，UI `verify-snapshot` exit `0`；
- manifest 的 feature、lanes/repos/checks/attestors 與接受的交付範圍一致；
- 記錄 snapshot digest，Step 05 以全部 AC 做 coverage。

人類接受 source／分類真實性與交付範圍一致性是 `prose-only, unenforced`，因為
外部來源與人類意圖不由本機 kernel 認證；text/bundle/routing digests 由 kernel 檢查。
缺接受或 digest 不符就補正未凍結的 inputs；excluded/uncertain scope 回 domain；
既有 output 或已凍結內容有錯，就建立 superseding version。UI 不要求 Step 02 report。
