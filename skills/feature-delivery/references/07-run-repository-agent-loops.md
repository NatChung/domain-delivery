# 07 · 各 Repository 執行 Agent Loops

狀態：v0.1，可執行。每個 product repository 的 native tests/contracts/static/architecture commands 機械式檢查自身 behaviour；中央 hub 不重複產生 `Repository Loop Result` JSON。Red/green 歷程、semantic compliance、fresh review 與 brownfield ratchet classification 是 `prose-only, unenforced`，除非該 product repo 已提供對應 machine checks。

## 目的

依 `06-repository-task-plan.json` 在每個 product repository 執行 test-first implementation loop，產出真實 checker file 與 numbered raw output，供 Step 08 直接從 repo state/bytes 綁定 evidence。

## 進入條件

- Step 04 snapshot 再次 `verify-snapshot` exit `0`；
- Step 05/06 validator `--require-ready` exit `0`；
- 呼叫者已確認每個 packet 的 public `test_seams`；
- active request 授權修改列入 scope 的 product repositories；
- packet ordering/dependencies 已滿足。

若目前只被要求研究、review 或寫 hub artifacts，沒有 product-code mutation authority，就停在 Step 06。

## 1. 啟動一個 repository packet

進入 packet 的 `repository_path`，重新讀取列出的 guides，確認：

- current branch/base ref；
- full commit 與 dirty/untracked state；
- repo-native install/test/lint/architecture commands；
- packet 指定的 public test seams；
- checker/output paths；
- upstream packet/contract 已就緒。

保留使用者既有 changes。若需要 checkout、pull 或 branch switch，先確認不會覆蓋 work；HEAD 移動後直接執行 `codegraph sync`。Code location、impact 或 affected symbols 先用該 repo 的 `codegraph_explore(projectPath=...)`。

## 2. 執行 vertical red → green cycles

每次只取一個 Snapshot rule / Step 05 contract：

1. 在 packet 已確認的 public seam 寫一個 observable test/contract；
2. 執行最小 command，確認它因缺少該 behaviour 而 red；測試環境或 syntax failure 不算有效 red；
3. 寫最小 implementation 使同一 test green；
4. 執行相關 native checks，確認沒有破壞已完成 slice；
5. 依上一個 cycle 的結果選下一個 rule。

Expected values 來自 frozen Snapshot/numbered spec，不用 production implementation 重算。Mock 只放在真正 system boundaries；不 mock 自己的 internal collaborators 來證明 call count。

Provider/consumer contract 依 Step 06 ordering 執行。Cross-repo behaviour 要在各 repo 有各自可觀察的 contract seam；單邊 test pass 不證明整條 wire 相容。

## 3. Review、refactor 與 architecture checks

Behaviour cycles 全部 green 後：

- 對完成的 slice 做 fresh review；
- 只在 observable behaviour 仍受 tests 保護時 refactor；
- 執行 packet 的 full native quality/static/architecture commands；
- 若 repo 有 fingerprinted brownfield baseline，確認 violation set 沒增加，並在減少時 ratchet baseline；
- Snapshot contradiction 不能列為 brownfield exception。

Fresh review 找到 blocking bug 時回 red/green cycle；找到 Snapshot contract 錯誤時停止 affected packets，回 Step 04 由人類決定 rebaseline。

## 4. 產生 Step 08 inputs

每個 packet `evidence_inputs` 指定一個 frozen `(repository_id, check_id)`、planned checker path 與 `/tmp/07-<repo>-<check>.txt` output。以真實 checker 執行並保存 stdout/stderr 與 exit code；不要手寫成功文字或把歷史 log 當成本次 output。

建議 adapter 形狀：

```bash
<repo-native-check-command> > /tmp/07-<repo>-<check>.txt 2>&1
check_exit=$?
```

實際 shell wrapper 必須保留真實 exit code，並把相同數字傳給 Step 08 `record-result --exit-code`。Exit contract：`0` pass、`1` fail、`2` invalid、`3` not applicable；required check 的 `3` 永遠不能完成 delivery。

Checker file 必須是 Step 05/06 已規劃的同一路徑。若實作時需要換 checker，先更新 Step 05/06 artifacts並重新 validation；若 stable required check meaning 改變，建立 snapshot v2。

## 5. Packet completion

一個 packet 只有在以下條件全成立才完成：

- assigned projections 都有有效 red observation 與 green result；
- packet completion criteria 全部可觀察地滿足；
- native behaviour/contract/architecture/quality checks 已 fresh run；
- fresh review 沒有 blocking finding；
- checker files 與 `/tmp/07-...` outputs 存在；
- current repo commit/dirty state 已記錄；
- 沒有未分類 Snapshot contradiction。

Output 是 product-repo code/tests/contracts、checker files、raw outputs 與真實 exit codes。不要另寫中央 `07-repository-loop-result.json`：Step 08 kernel 會直接計算 checker digest、repo commit、dirty-state digest 與 output digest，避免兩份結果漂移。

## Parallelism

只平行執行沒有 `depends_on_repositories` edge、也不共同修改相同 product repo/worktree 的 packets。每個 packet 可交給獨立 Agent，但它只能修改自己的 repository，並回傳 exact commands/exit codes/paths；主流程負責 dependency ordering 與 Step 08 binding。

## Failure / stop rules

- red test 無法在 agreed seam 表達：回 Step 05/06 調整 projection/packet；
- native check fail：留在該 repo loop，不記 pass evidence；可進 Step 08 只綁定/report failed run；
- check invalid或環境缺失：保存 exit `2` output，可先進 Step 08 綁定 failed run，再修復環境後 fresh rerun；
- N/A：保存 exit `3`，可進 Step 08 綁定 failed run，但 required gate 保持 fail；
- code/contract 與 Snapshot 衝突：停止 affected repos，回 Step 04；
- 額外 capability/request：建立新的 change request，不擴張 active snapshot。

## 邊界

本步不自行 commit/push/開 PR/改 ticket，除非 active request 明確包含這些外部或 Git mutations。即使所有 repo checks exit `0`，也要到 Step 08 綁定 trusted independent attestation 並 `verify-evidence` exit `0` 才完成 evidence gate。
