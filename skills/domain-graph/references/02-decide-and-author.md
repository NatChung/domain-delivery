# 02 · Prepare decisions and author canonical nodes

## 何時讀

已有 evidence-backed domain question、需要 identified authority 回答，或已可把 discovery 轉成 canonical `candidate`/`disputed`/human-confirmed node 時讀本檔。

## Enforcement note

Decision-packet adequacy、human authority identity/provenance/scope judgment 與
folder placement/lazy creation 都是 `prose-only, unenforced`，因為 Kernel
無法判斷 business authority 或目錄是否表達正確邊界。Kernel 只驗證
canonical node 的 machine shape、typed references 與 metadata consistency；
machine pass 不能取代人類 semantic review。

## 進入條件

- 01 的 evidence 與 alternatives 足以提出 exact question，或已有一份可追溯的 authority answer；
- 已讀 `docs/domain/SCHEMA.md`、affected canonical nodes與相關 ADR；
- 若要寫檔，active request 明確要求建立/更新 Domain Graph。

## 1. 準備 decision packet

每個 decision 單獨提供：

- exact question；
- proposed answer 與 viable alternatives；若 evidence 不足以安全推薦任何
  semantic answer，明寫 `no defensible recommendation yet`，不要為了填欄位猜 meaning；
- evidence for/against，含 freshness/contradiction；
- affected journeys、nodes、contracts、repositories與 delivery requests；
- 延後決定的 consequence；
- 可以決定此 scope 的 named human authority，或 `unknown`。

Decision packet 預設在對話或原 ticket 交付；未獲 external-write 授權時不代替使用者留言。問題屬於既有 ticket 時留在該 ticket，Slack 只在另獲授權後通知對方去看 ticket。

### Packet 範本(源自 16 段 §13)

```markdown
# Decision: <題目>
## Question(確切的一題)
## Evidence(正反都列,含新鮮度)
## Proposed answer
## Alternatives(可行替代,直接可選)
## Impact(影響哪些 journeys/nodes/contracts/repos;拖延的代價)
## Required authority(具名)
```

Authority 只需三選一:同意 proposed answer、選一個 alternative、補充
未列的規則。

### 三層 review 分級(源自 16 段 §13)

- **BC boundary review**:Purpose / Owns / Does not own /
  Ubiquitous Language / Authority。
- **Rule decision review**:Preconditions / Invariants / Postconditions /
  Failure cases / Unknowns。
- **Cross-context contract review**:兩側 authority 各自確認提供什麼、
  需要什麼。

### 不算 confirmed 的反例

已讀不回、會議中沒反對、code 已經這樣跑、PM 說「應該是」——
都不是 confirmed。

## 2. 處理 authority outcome

- 沒有答案或 authority unknown：保持 `candidate`，把問題放入 `open_questions`/`blocking_questions`，停止 confirmation。
- 可信來源不同意：使用 `disputed` 並保存 alternatives，不自行折衷成 confirmed meaning。
- Human answer 可追溯，但 authority node 未達 `confirmed L3` 或 scope 不涵蓋 target node：記錄 evidence，先補 authority gap；不填 target confirmation metadata。
- 只有 named human/role 已接受 meaning、`confirmation_source` 可追溯、authority node 是 scope-covering `confirmed L3` 時，才可依該接受內容 author `confirmed` metadata。Agent 不是 confirmer。

把有效接受結果整理成 authority confirmation record：target node ID、accepted answer/meaning、authority node ID與 scope、`confirmed_by`、`confirmed_at`、`confirmation_source`，以及明列的 exclusions。Canonical node front matter加上它引用的人類 source是正式 record；不要維護一份可能分叉的平行 confirmation truth。

## 3. Author canonical Markdown

Front matter 必須符合 `docs/domain/SCHEMA.md` 的 flat JSON-compatible contract；human-readable meaning、evidence、alternatives與 unresolved decisions 放在 non-empty body。只使用 exact status：`candidate`（尚未接受）、`disputed`（可信來源衝突）、`confirmed`（authority 已接受）、`superseded`（只保留歷史）。常用 placement：

```text
docs/domain/journeys/                       cross-context journey discovery
docs/domain/capabilities/                   cross-context capability discovery
docs/domain/bounded-contexts/<context>/     evidence-backed BC candidate/confirmed model
docs/domain/contracts/                      cross-context/wire contracts
docs/domain/shared-kernel/                  deliberately shared concepts
docs/domain/authorities/                    confirmation scopes
```

`docs/domain/bounded-contexts/<context>/INDEX.md` 是 `bounded_context` node；context-specific `terms/`、`policies/`、`questions/` 只在有 substantive node 時建立。Candidate folder 可在 L2 建立但不代表 confirmation；禁止空 folder 或 placeholder。若 supported type 尚無已接受 placement，先向 maintainer取得 path decision，不自行創造第二套 hierarchy。

依 node maturity 填寫：

- L0：observation/question，尚未達 source-backed maturity；
- L1：至少一筆 `sources`；
- shaped type 的 L2：non-empty `scope`，並明列 `out_of_scope`、`open_questions`（可為空 list）；
- L3：`confirmed`、空 `blocking_questions`；`docs/domain/SCHEMA.md` 定義的 executable node types另需 non-empty `preconditions`、`postconditions`、`invariants`、`invalid_cases`；
- confirmed non-authority：`confirmed_by`、`confirmed_at`、`confirmation_source` 與 scope-covering `authority`。

非 confirmed node 的 `authority` 只能是 exact `authority:<id>` 或 `unknown`。不要加入 schema 未定義的 front-matter field；需要額外解釋時放 Markdown body。

使用 `requires` 只表示無該 node 就不能正確解讀或執行的 typed dependency；它會進 Snapshot closure。比較、導航與非必要 evidence 使用 `related_nodes`。兩者都必須 resolve。

更新 semantic nodes 後，若 current maturity、node inventory或 navigation 改變，同一 change 更新 `docs/domain/INDEX.md`。不手改 generated `domain-index/index.json`。

## 完成判準

本路徑完成時必須回傳：

- 每個 decision 的 answer/authority/provenance或 blocker；
- created/updated node IDs、status/readiness、source paths與 relationship rationale；
- observed/inferred/disputed/confirmed claims 的明確邊界；
- 尚未 resolve 的 authority、source、placement或 relationship問題；
- 有 canonical writes 時路由到 03；只有 decision packet 時停在 human decision，不假裝完成 graph update。
