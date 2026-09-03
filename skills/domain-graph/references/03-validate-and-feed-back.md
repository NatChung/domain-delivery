# 03 · Validate graph readiness and feed delivery learning back

## 何時讀

Canonical Domain Markdown 已變更、需要判斷 graph commit readiness，或 `$feature-delivery`/released implementation 帶回 drift、contradiction、missing rule 或 new business learning 時讀本檔。

## Enforcement note

Feedback semantic classification、bug/domain-change routing、release treatment
與 unresolved-blocker interpretation 是 `prose-only, unenforced`，因為需要
domain/release judgment。Kernel 可機械驗證 graph、Snapshot、drift 與 Evidence
integrity；它不會替人決定 feedback 的 business meaning 或處理方式。

## A. Validate canonical graph changes

### 進入條件

- Semantic changes 已寫入 `docs/domain/**`，且 `docs/domain/INDEX.md` 反映 current maturity/navigation；
- confirmation metadata（若有）來自可追溯的 human authority outcome；
- 沒有用 generated JSON 代替 Markdown meaning。

從 repo root 執行 shared deterministic seam：

```bash
python3 -B .domain-delivery/kernel/scripts/kernel.py compile \
  --source docs/domain --output domain-index/index.json

python3 -B .domain-delivery/kernel/scripts/kernel.py gate-index \
  --index domain-index/index.json
```

任何 nonzero exit 都停止 readiness，回報原始錯誤與 affected node。修 semantic/source Markdown，再 regenerate；不要手改 index 讓它過。`gate-index` 允許 coherent candidate/L2 nodes，所以 exit `0` 只表示 schema、references與 machine graph gate一致，不表示 human acceptance、Feature Domain Gate 或可 freeze。

Validation 後檢查 scoped diff：canonical Markdown與 regenerated `domain-index/index.json` 必須同一 proposed commit；不混入 product repos、Snapshots 或 unrelated user changes。Unresolved question與 `unknown` 可以是誠實的 candidate content，也不必阻擋 candidate graph commit，但必須明列它阻擋的是 confirmation、delivery selection或其他後續 gate，不能被 completion wording藏起來。

只有以下全部成立才回報 `graph commit ready`（此文字是 Skill 的 prose outcome，`prose-only, unenforced`，不是 kernel status）：

- `compile` exit `0`；
- `gate-index` exit `0`；
- generated index 與 Markdown 是同一 working-tree change；
- confirmed claims 有有效 human provenance；
- unresolved blockers 沒被誤稱 accepted truth；
- diff scope與 requested write permission一致。

Commit/push 需另外明確授權。未 commit 時不要提供假的 graph version；實際 commit 後才回傳 full commit SHA、changed node IDs與 machine results給 `$feature-delivery`。Feature Skill 仍須重新選 active slice、算 `requires` closure並執行自己的 gate。

## B. Consume drift and implementation feedback

接受 `08-domain-feedback.md`、evidence/drift report、production observation或 human correction作為新 evidence。標題中的「confirmed implementation observation」只表示 implementation 已觀察，不是 confirmed Domain Truth。

若使用者明確要求計算某 frozen Snapshot 對 current index 的 drift，且已提供 exact snapshot path，可執行：

```bash
python3 -B .domain-delivery/kernel/scripts/kernel.py drift \
  --snapshot specs/<feature>/snapshot/<version>/snapshot-manifest.json \
  --index domain-index/index.json
```

Drift output 只分類 global/selected node change，不自動 rebaseline、confirm feedback或決定 release。接著依 feedback 分流：

- missing journey/capability/boundary evidence → 01；
- new meaning、contradiction、policy/term/authority question → 02 的 candidate/disputed node或 decision packet；
- implementation bug against unchanged snapshot → 回 `$feature-delivery`/human owner分類與處理，不改 domain meaning；
- confirmed graph correction影響 frozen basis → 保留 Snapshot immutable，由 human owner決定 corrective change、new feature、rebaseline或 v2。

任何 graph write 都重新走本檔 A 的 compile/gate-index/readiness。不要修改 evidence ledger、Snapshot或 product code來消除 drift。

## 完成判準

本路徑完成時回傳：

- exact commands、exit results與 generated index path；
- graph commit ready / not ready、machine/scope blocker，以及不阻擋 candidate commit但仍阻擋 confirmation/delivery 的 domain blocker；
- feedback 的 observed/inferred/disputed/confirmed 分類與下一個 Domain path；
- 若已獲授權並實際 commit，full graph commit SHA；否則明確寫 uncommitted；
- 給 Feature Delivery 或 human owner 的 handoff，包含 changed node IDs、drift scope與仍需重新 gate 的項目。

本路徑完成不等於 Snapshot freeze、evidence gate、deployment或 release acceptance。
