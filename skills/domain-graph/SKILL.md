---
name: domain-graph
description: 維護 Delivery Hub 的 Domain lane：從 journey/domain evidence 建立或更新 candidate/disputed Domain Graph nodes、比較 capabilities 與 Bounded Context boundaries、準備 authority decision packets、套用可追溯的人類 confirmation、編譯 typed index，並處理 delivery drift/feedback。當使用者要求建立或補齊 Domain Graph、處理 domain gap/contradiction/unknown authority、把 implementation evidence 回饋 graph，或 Feature Delivery 將 domain gap 路由回來時使用；不處理 request-to-Snapshot delivery、Snapshot freeze 或 product implementation。
---

# Domain Graph

這是 Delivery Hub 的 Domain lane router。它把 evidence 變成可審查的 graph
candidates，再由 identified PM/domain authority 決定哪些 meaning 能成為 confirmed
truth。Hub 的 `docs/domain/**` 是 canonical Markdown record；
`domain-index/index.json` 只由 `.domain-delivery/kernel/scripts/kernel.py` 產生，
Skill 不複製 kernel implementation。

## 先確認安裝版本

先讀 Hub root 的 `workflow.lock`。lock 的 tag/commit 與 `.domain-delivery/`
實際 checkout 不一致時停止，改用 `delivery-hub` 的 `doctor` 與 `upgrade`
([`../delivery-hub/SKILL.md`](../delivery-hub/SKILL.md))，不要在版本不明的情況下
改 canonical graph。

## 每次先讀

1. Hub 的 `CONTEXT-MAP.md` 與 `AGENTS.md`。
2. Hub 的 `docs/domain/INDEX.md` 的 live current maturity；不要把 pilot
   candidates 說成已建立的 Graph v0，也不要在 Skill 內快取 node inventory。
3. [`../../docs/domain-graph-schema.md`](../../docs/domain-graph-schema.md)、
   相關 canonical nodes 與相關 ADR。當工作涉及 lane ownership 或 Bounded Context
   placement 時，讀 [ADR 0006](../../docs/adr/0006-separate-domain-and-delivery-skills.md)。

## 選擇路徑

- 新 evidence、journey discovery、capability coverage 或 boundary comparison：完整讀 [01 · Discover and shape](references/01-discover-and-shape.md)。
- 已有明確 domain question、需要 authority decision，或已可 author canonical nodes：完整讀 [02 · Decide and author](references/02-decide-and-author.md)。
- 已有 canonical changes 要驗證 graph commit readiness，或收到 delivery drift/feedback：完整讀 [03 · Validate and feed back](references/03-validate-and-feed-back.md)。
- 完整 Domain lane 依 01 → 02 → 03；evidence 或 authority 不足時停在當下路徑，不以後續 validation 假裝補足 meaning。

只讀當下需要的 reference。若 feedback 產生新的 discovery 或 decision，從 03 路由回 01 或 02，而不是在 validation 階段暗中改 semantic conclusion。

## Authority 與 permission boundaries

- Tracker、知識庫、analytics、interviews、maps、code 與 tests 都是 evidence，不是 domain confirmation。Code-derived statements 先標 observed/inferred；code 不能成為 truth authority。
- Agent 可建立 `candidate`/`disputed` node 與 decision packet；只有 identified human PM/domain authority 能接受 meaning。沒有 traceable acceptance、confirmed L3 authority node 或 scope coverage 時，不填 `confirmed` metadata。Hub 在 `hub.yaml` 的 `authority.registry` 宣告 authority nodes 存放位置。
- 只有使用者要求建立/更新 Domain Graph 時才修改 `docs/domain/**` 與 generated index。Review/query 不授權寫入；ticket/chat/repository writes、commit/push/PR 各需另外的 active request。
- 不修改任何 product repository 的 code。Implementation investigation 是 read-only evidence collection，且遵守該 repo guides、primary branch 與 code-explorer-first 規則。
- 不建立或修改 Feature Snapshot、不執行 repository delivery loops、不記錄 delivery evidence。這些由 `$feature-delivery` 負責。
- `compile`/`gate-index` 只驗證 machine coherence，不代表 authority acceptance、Domain Gate 或 Snapshot readiness。

## Shared seam

Domain Graph 的 schema、compile、gate-index 與 drift calculation 由
[`../../kernel/`](../../kernel/README.md) 擁有。命令與 completion semantics 只在
[03 reference](references/03-validate-and-feed-back.md) 定義；Skill 直接使用 kernel
seam，不在 Skill 內複製 validator，也不手改 `domain-index/index.json`。

## 完成與 handoff

- 每次回傳：完成的 artifact/change、observed/inferred/confirmed 分類、未決 evidence 或 authority blocker、machine validation 結果與下一個合法路徑。若 read-only 或 decision-packet-only 路徑不需要執行 validation，明寫 `not run / not applicable` 與原因，不用假造 pass。
- Canonical update 只有在 Markdown 與 regenerated index 一致、`compile` 和 `gate-index` 都 exit `0` 時才是 `graph commit ready`；這個 prose outcome 不是 kernel-emitted status。未獲 commit 授權時停在 readiness，不自行 commit。
- 若更新含 `confirmed` node，還必須保留 traceable human confirmation metadata；machine pass 不能取代它。
- 只有實際 commit 後才能向 `$feature-delivery` 提供 full graph commit SHA。Feature Delivery 仍須重新做 active-slice/closure gate，Domain Skill 不 freeze Snapshot。
- Feedback 永不重寫 frozen Snapshot；需要 rebaseline、v2 或 release classification 時交回 human delivery/release owner。
