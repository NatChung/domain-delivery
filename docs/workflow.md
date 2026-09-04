# AI Coding Agent 交付工作流程

狀態：Accepted，version 1.0

審查日期：2026-09-03 — 已逐節對照 16-part teaching reader；未發現語意偏移。
本文件是方法的唯一來源；reader 保留為教學材料。

Owner：delivery-method maintainers
決策紀錄：[ADR 0005](adr/0005-versioned-domain-graph-and-feature-snapshot.md)
結構紀錄：[ADR 0006](adr/0006-separate-domain-and-delivery-skills.md)
Kernel packaging 紀錄：[ADR 0007](adr/0007-move-kernel-into-repo-plugin.md)
Distribution 紀錄：[ADR 0008](adr/0008-distribute-shared-workflow-as-pinned-submodule.md)

這是每個安裝此版本的 Delivery Hub 共用的方法唯一來源。每個 Hub 擁有自己的
Domain Graph 與 local adapter；任何 Hub 都不能複製本方法後無聲地分叉。

本方法分開兩種以不同速度演進的變更：

```text
Domain lane：       evidence → graph candidate → human confirmation → graph version
Delivery lane：     request → active slice → frozen snapshot → repo loops → evidence
                                      │
                                      └── pin 一個 graph commit 與選定的 node hashes
```

Domain Graph 會持續學習，Feature Snapshot 則不會。這是讓工作流程足夠線性、
可以執行，同時不假裝 domain 靜止不變的核心規則。

## 1. 目標與問題

目標是建立一條可重複的路徑，把 product request 轉成有 evidence 支持的交付。
Agents 可以探索、起草、實作與執行 checks；business meaning、risk acceptance 與
exceptions 的 authority 仍由 humans 掌握。

Brownfield code 是 evidence，不會自動成為 truth；product prose 也是 evidence，
不會自動成為 executable contract。這套工作流程會先讓歧異浮現，避免 agent 把某個
來源中的偶然現象轉成整個系統的規則。

## 2. 雙 Lane 生命週期

Domain lane 持續運作，記錄組織目前對 journeys、capabilities、Bounded Contexts、
language、policies、contracts 與 decision authority 的理解。

Delivery lane 以 feature 為範圍。它只取 active slice 所需的 confirmed domain
nodes，將其 freeze，投影 executable contracts，再執行 repository-specific
implementation loops。

兩條 lane 只在明確的 snapshot 交會。後續 Domain Graph 的修改會回報為 drift，
不會改寫已經進行中的工作。

## 3. Truth、evidence 與 human authority

每一個 domain statement 都有兩個彼此獨立的維度。

`status` 描述 semantic authority：

- `candidate`：合理但尚未由負責的 human 接受；
- `disputed`：可信來源彼此矛盾；
- `confirmed`：已由明確的 authority 接受此 statement；
- `superseded`：為 traceability 保留，但已不是 current。

`readiness` 描述 evidence 的完整程度：

- `L0`：尚未整理的 observation 或 question；
- `L1`：已命名、至少有一個 source 的 candidate；
- `L2`：已調查 boundaries、alternatives 與 open questions；
- `L3`：implementation-ready、confirmed，且沒有 blocking ambiguity。

Code、tickets、analytics、documents 與 interviews 都是 source lanes，不能自行確認
自己。`confirmed` node 必須記錄 `confirmed_by`、`confirmed_at` 與適用的
`authority`。若 owner 不明，node 就維持 `candidate`，即使 technical evidence
很強也一樣。

## 4. 建立廣泛的 Domain Graph v0

從廣泛的 L1／L2 開始，不必等待完美 model。記錄：

- end-to-end Journeys；
- candidate capabilities；
- terms 與 policies；
- 作為 evidence locations 的 systems／repositories；
- candidate authority 與 ownership；
- contradictions 與 unanswered questions。

Graph 採 Markdown-first，因為人必須能 review 真正的 meaning。Generated JSON 是
index 與 validation surface，永遠不是 business source of truth。

不要掃描所有 branches 來推論 domain。只檢查 primary branches 與 current
operational sources。Historical 或 abandoned branches 只有在被刻意選取並加上標記時，
才作為 evidence。

## 5. 從 Journey 到 capability，再到 Bounded Context

例如 `Saved item → Price alert` 這類 Journey 是 observation path，不是 Bounded
Context。將它與其他 journeys 比較，找出 language、rules、ownership、invariants
與 change cadence 能維持 cohesive 的邊界。

只有多項 observations 足以支持 durable semantic boundary 時，才建立或修改
Bounded Context candidate。Service、repository、UI surface 或 team 本身都不足以
單獨證明這個 boundary。

一般演進順序如下：

```text
Journey step
  → candidate capability
    → compare across journeys
      → candidate Bounded Context
        → domain/PM review
          → confirmed Bounded Context
```

## 6. Context ownership、contracts 與 shared concepts

本節的 folder placement 與 lazy creation 規則為 `prose-only, unenforced`；compiler
會驗證 node content 與 references，不會驗證 directory policy。

只有多項 observations 提供足夠 evidence，可以把一個 Bounded Context candidate
當作 durable semantic boundary 調查時，才為它建立專屬 folder。因此 folder 可以在
node 仍是 `candidate L2` 時存在；folder 存在不代表 boundary 已 confirmed。不要預先
建立任意數量的空 BC folders。Human confirmation 透過 node 的 `status`、
`readiness` 與 authority metadata 另外記錄。

Cross-context interaction 以 contract 表達，由 provider boundary 擁有，或由相關
boundaries 共同擁有。真正跨 contexts 共用的 concepts 放在 graph 的 shared-kernel
區域，並明確記錄 owners 與 compatibility policy。「Shared」不能變成 miscellaneous
folder。

`app`、`web` 與 `server` 是 delivery lanes，用來 route tickets 與 repo loops；
它們不是 Bounded Contexts。一個 feature snapshot 可以啟用多條 delivery lanes 與
多個 repositories。

## 7. Markdown source of truth 與 derived index

Canonical hierarchy 如下：

```text
docs/domain/                 Markdown-first canonical graph record
  INDEX.md                   graph entry and current maturity
  SCHEMA.md                  authoring contract
  bounded-contexts/          evidence-backed BC candidates, created as needed
  capabilities/              capability nodes
  journeys/                  journey nodes
  contracts/                 cross-context and wire contracts
  policies/                  rules that decide outcomes
  terms/                     ubiquitous language entries
  questions/                 unresolved semantic questions, with who must answer
  shared-kernel/             deliberately shared concepts
  authorities/               who may confirm which statements

domain-index/index.json      deterministic, generated typed index
```

Kernel 會驗證 IDs、types、statuses、readiness 與 confirmation metadata。它會排序
nodes 並輸出 content digests，讓 downstream snapshots 能 pin 精確 meaning。Index
可以刪除後重新產生；手動編輯是錯誤操作。

Code exploration 仍以單一 repository 為範圍。Hub 可以關聯各 repo 的 findings，
但 symbol impact 與 call paths 不會跨越 repository index boundaries。

## 8. Decision packets 與 Domain Gate

Agents 不應把一堆 raw findings 直接交給 PM 或 domain expert。每個 decision 都要準備
一份精簡 packet：

- exact question；
- candidate answer 與 alternatives；
- 支持與反對的 evidence；
- affected journeys、contracts 與 repositories；
- 延後決策的 consequence；
- 可以確認它的 named authority。

只有選入 delivery 的每個 node 都是 `confirmed L3`、所有 required authority 都已
記錄，且選中的 rules 沒有 blocking contradiction，Domain Gate 才通過。Graph 其餘
部分可以維持 candidate 或 L2。這就是 active-slice principle：delivery 不必等待整個
domain 完整才開始。

## 9. Active slice 與 immutable Feature Snapshot

Domain Gate 通過後，在衍生 BDD 或 code 以前先 freeze Feature Snapshot。Snapshot
包含：

- feature identifier 與 snapshot version；
- Domain Graph commit、source root 與 generated index digest；
- selected node IDs 與 content digests；
- accepted scope、invariants、preconditions、postconditions 與 invalid cases；
- required delivery lanes 與 wire contracts；
- required evidence／check IDs。

Preconditions、postconditions 與 invariants 應寫在 reviewed Markdown domain 或
feature material。Manifest 只 reference 並 hash 它們；JSON 不取代其文字說明。

Snapshots 是 immutable。當 graph 改變時，agent 會回報 drift，但仍依 pinned
snapshot 繼續，除非 human 判定此修正必須 rebaseline。Replacement 以新版本
（`v2`）取代 `v1`；任何 process 都不能原地修改 `v1`。

## 10. Scrum、Definition of Ready 與 change classification

建立 executable Sprint Backlog 前，先把 PO／PM shaping 與 agent execution 分開：

```text
Product Backlog
  → active-slice discovery and decisions
    → Domain Gate
      → frozen Feature Snapshot
        → executable Sprint Backlog
          → repository Agent Loops
```

Snapshot 是 agent work 的 semantic Definition of Ready。Team capacity、dependencies
與 release readiness 仍是一般 Scrum concerns。

發生變更時，必須明確分類：

| 情況 | 處理方式 |
|---|---|
| 實作前發現錯誤細節 | 同一 feature；建立 snapshot v2 |
| 實作中發現錯誤 contract | 停止受影響的 loops；rebaseline 至 v2 |
| 要求額外 capability | 新 feature／change request |
| Released code 違反有效 snapshot | Bug fix |
| Released behaviour 符合 snapshot，但後來發現 snapshot 錯誤 | Corrective change；只有風險需要時才 hotfix |
| Release 後新增 business rule | 新 feature／change request |

這主要是 management distinction：保留工作存在的原因、適用哪一個 acceptance basis，
以及先前 implementation 是否有 defect。

## 11. Snapshot 之後的 contract stack

依下列順序從 frozen snapshot 投影 executable checks：

1. observable behaviour 的 BDD examples；
2. preconditions、postconditions、invariants 與 invalid cases 的
   Design-by-Contract checks；
3. delivery lanes 或 contexts 之間的 wire／schema contracts；
4. dependency direction 與 ownership 的 architecture contracts；
5. repository-native quality checks。

BDD 是 snapshot 的 projection，不是用來決定 snapshot 的 input。Snapshot 可以要求
named check，不需要指定 Java、Flutter、TypeScript 或特定 framework。

## 12. Repository Agent Loops 與 brownfield ratchets

每個受影響的 repository 都依同一份 snapshot 執行自己的 loop：

```text
select next contract → red test → minimal change → green → refactor
  → architecture/static checks → record evidence → fresh review
```

各 repository 自己的 `AGENTS.md`／`CLAUDE.md`／README 定義 commands 與 local
standards。Shared kernel 負責 binding results；它不會為每個 team 產生某一種語言的
test layout。

Brownfield architecture violations 以 fingerprints 記錄成 baseline。Gate 允許 known
debt、拒絕 new violations，並在 debt 移除時讓 baseline 只減不增。Known debt 不會
被無聲地視為「pass」；它是包含 owner 與 scope 的 visible exception。

與 active confirmed snapshot 矛盾的 behaviour 不能當作 brownfield debt 被
grandfather。它必須 fail，或由 human rebaseline。

## 13. Evidence、feedback 與 rollout

Evidence entries 透過 kernel append 並形成 hash chain。每筆會 bind：

- snapshot digest；
- repository-scoped check ID 與 checker file digest；
- repository commit 與 dirty-state digest；
- output／artifact digest；
- exit code 與 timestamp；
- 一份 result performer declaration；
- 另一份獨立的 trusted attestation declaration 與 artifact digest；
- previous entry hash。

Exit code `0` 表示 pass、`1` 表示 fail、`2` 表示 invalid evidence／input、`3` 表示
not applicable。Required checks 只有 `0` 才通過；historical success、missing checks
與 N/A 都不能滿足 gate。Kernel 會 enforce separation 與 integrity；surrounding CI 或
local adapter 負責驗證 declared actor 的身分，單純的 string identity 不能宣稱為
cryptographic proof。Local ledger 只有在 terminal hash 被 external trusted system
保存或簽署時，才能稱為 tamper-evident。

Feedback 透過 Domain lane 更新 Domain Graph，永遠不會改寫 snapshot 或 evidence
ledger。因此每個 completed run 都能回答：「我們實作了哪個 domain version、改了
什麼，以及用什麼證明？」

以 thin slices rollout：

1. 建立 Graph v0 與 authorities；
2. 選擇一個 PM-approved pilot，範圍要小到能從單一 confirmed rule 開始；
3. freeze 一份 snapshot；
4. 執行 native repository loops 與 evidence binding；
5. review false positives、missing contracts 與 decision latency；
6. 改進 method，但不修改 completed artifacts。

## Artifact 權威

| Artifact | Authority | 可修改？ |
|---|---|---|
| 本 repository 的 `docs/workflow.md` | shared method | versioned edits |
| Hub `docs/domain/**` | 該 Hub 的 domain meaning | 可以，需保留 status／history |
| `domain-index/index.json` | generated validation／index | 只能 regenerate |
| `specs/<feature>/snapshot/**` | feature execution basis | 不可；以新版本 supersede |
| product-repo tests／contracts | executable projection | 可以，需依 snapshot |
| `evidence/<feature>/<run>/` | bound run declarations／evidence | kernel append；terminal hash 由外部 anchor |
| tickets／backlogs | work coordination | 可以；不是 domain truth |

## 實作狀態

Version 1.0 定義完整 contract。這裡刻意不追蹤各 Hub 的 maturity；每個 Hub 在自己的
current-state authority 記錄 live state，通常是透過 Hub adapter 到達的
`docs/domain/INDEX.md`。Hub adapter 必須明確 map 到此 lifecycle，才能宣稱
conformance。
