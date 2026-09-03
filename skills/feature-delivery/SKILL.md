---
name: feature-delivery
description: 將 PO 的 tracker request 依序轉成 Feature Intent、Domain Graph active slice、immutable Snapshot、executable check projection、repository packets、implementation loops 與 bound evidence。當使用者提供 ticket key/內容並要求理解需求、啟動 feature delivery，或要求從 Feature Delivery 的 numbered artifact/step 接續時使用；每個 gate 未通過即停止，不因啟動流程而自動取得外部寫入或 product-code mutation 權限。
---

# Feature Delivery

這是 Delivery Hub 的 Feature Delivery router。
[00 · artifact matrix](references/00-delivery-artifact-matrix.md) 擁有跨步 artifact
名稱、producer/consumer、authority、enforcement owner 與 failure routing；每個
numbered reference 擁有該步的 procedure、status computation、machine command 與
completion criterion。進入 Steps 02–08 前完整閱讀 matrix，再只讀當下 step reference。

## 先確認安裝版本

先讀 Hub root 的 `workflow.lock`。lock 的 tag/commit 與 `.domain-delivery/`
實際 checkout 不一致時停止，改用 `delivery-hub` 的 `doctor` 與 `upgrade`
([`../delivery-hub/SKILL.md`](../delivery-hub/SKILL.md))。Snapshot 與 evidence 會
綁定版本，版本不明時不freeze、不記錄 evidence。

## 選擇起點

- 使用者提供 ticket key/URL/content 且沒有 valid prior artifact：從 Step 01 開始。
- 使用者提供 numbered artifact 或明確指定 step：先驗證其 actual producer 的 gate；prose-only step 依該 reference 的 completion criteria，optional Step 03 依 report 指定回 Step 02，不以數字猜 predecessor。
- 使用者要求完整 delivery：依 01 → 02 → optional 03 → 02 → 04 → 05 → 06 → 07 → 08；第一個 non-ready/unauthorized state 立即停止。
- Skill-owned reference、feature planning artifact、spec、packet 與 raw output 使用 producer step prefix。Kernel-owned `DOMAIN.md`、`domain-payload.json`、`snapshot-manifest.json`、`check-ledger.jsonl` 與既有 schema/script 名稱保留 machine contract，不強加 prefix。

## Step routing

| Step | 何時完整讀取並執行 reference |
|---|---|
| 01 | 新 request：[01 · 理解需求 Ticket](references/01-understand-request.md) |
| 02 | 有 ready Feature Intent：[02 · 對照 Domain Graph](references/02-compare-domain-graph.md) |
| 03 | Step 02 指定 implementation investigation，包含 technical evidence 可能改變 domain decision packet 的 mixed case：[03 · Codegraph investigation](references/03-investigate-with-codegraph.md)；完成後回 Step 02 |
| 04 | Step 02 指定 snapshot：[04 · 凍結 Feature Snapshot](references/04-freeze-feature-snapshot.md) |
| 05 | 有 verified Snapshot：[05 · 投影 executable checks](references/05-project-executable-checks.md) |
| 06 | 有 ready projection：[06 · 建立 repository packets](references/06-create-repository-task-packets.md) |
| 07 | 有 ready task plan 且 active request 已授權 product mutations：[07 · Repository Agent Loops](references/07-run-repository-agent-loops.md) |
| 08 | 有 Step 07 raw results：[08 · Evidence 與 feedback](references/08-bind-evidence-and-feedback.md)；failed run 只能被綁定與回報，不能推進 delivery |

只讀當下需要的 numbered reference；不要預載後續細節來猜 output。Step 03 是 optional evidence loop，不是 Step 04 的替代入口。

Step 02 若發現需要新增/修改 canonical node、補 broad journey/capability discovery、解決 authority/boundary gap 或處理 contradiction，路由到 `$domain-graph`；只有 graph changes 已 commit 並提供 full SHA 後才回 Step 02 重新 gate。Step 08 的 domain feedback 也交給該 Skill，Feature Delivery 不在 evidence step 暗中維護 graph。這個 route 不轉移 Snapshot、product mutation 或 external-write authority。

## Authority 與 permission boundaries

- Ticket/PO statements 是 request evidence；只有 identified PM/domain authority 能 confirm domain meaning。
- Code explorer 與 code 是 implementation evidence；impact 只在單一 repo，cross-repo wire edges 要分別查證。
- Snapshot 只接受 committed `confirmed L3` closure。Agent 不自行填 human confirmation，也不以 synthetic fixture 代表真實 Hub readiness。
- Tracker/chat/repository external writes、product repo edits、commit/push/PR/release 各自需要 active request 授權；啟動本 Skill 不自動授權。
- 每個尚無 machine enforcement 的規則明標 `prose-only, unenforced` 與原因。

## Script ownership

- [`scripts/`](scripts/) 擁有 Step 01、05、06 的 intake/planning contracts。
- [`../../kernel/`](../../kernel/README.md) 擁有 repository-neutral Domain Graph、Snapshot 與 Evidence integrity contracts；skill validator 透過 kernel 公開的 Python seam 重用 snapshot verification、canonical digest 與 Git-root resolution。
- 執行 command、exit semantics 與 gate calculation 只在當下 numbered reference 定義；router 不快取副本。

修改本 Skill、numbered references、schemas、scripts、tests 或 eval cases 時，完整讀 [99 · 維護與 forward testing](references/99-maintain-skill.md)；正常 feature delivery 不讀它。這類修改屬於 shared package 的 release，不在 Hub 內就地改。

## 完成與停止

- 每一步回傳該 reference 定義的 artifact/result、status、阻擋原因與下一個合法 step；kernel-owned 與 product-repo outputs 保留其 machine contract 名稱。
- Non-ready state 不偷偷繼續；需要人類決定時準備 numbered decision packet，未獲寫回授權時只回傳內容。
- `verify-evidence` exit `0` 但缺 external actor authentication、artifact retention 或 terminal anchor 時，狀態是 `kernel_verified_unanchored`，不是完整完成。
- Domain feedback 只更新持續演進的 graph lane；永遠不修改 frozen Snapshot。
