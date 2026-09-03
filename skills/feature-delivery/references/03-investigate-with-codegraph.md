# 03 · 必要時用 Codegraph 查證目前實作

狀態：v0.1，可執行。Codegraph 回傳逐行 source、symbol edges 與 repository-local impact；問題選擇、cross-repo correlation 與 finding correctness 是 `prose-only, unenforced`，因為目前沒有跨 repo graph 或 implementation-evidence validator。

## 目的

只回答 Step 02 明列的 implementation questions，例如目前 caller/callee、wire contract、repo routing、affected symbols 或 brownfield constraint。結果是 implementation evidence，必須回到 Step 02 重新比較，不能直接確認 Domain Truth 或通過 Domain Gate。

## 進入條件

只有 `02-domain-comparison.md` 的狀態為 `needs_implementation_evidence`，且每個問題都包含以下資料時執行：

- 編號 question ID；
- exact technical question；
- 為何答案可能改變 node selection、contract、routing 或 impact；
- 預計調查的 repositories；
- 可判定完成的 expected evidence。

問題屬於 request/domain/release decision 時回 Step 02 分流，不查 code 代替人類決定。

## 1. 準備每個 repository

Hub 在 `hub.yaml` 的 `code_explorer.kind` 宣告使用哪個 explorer；本 reference 以 Codegraph 為 reference implementation，其他 explorer 需提供等價的 symbol/call-path 證據。Product clones 的位置由 Hub 的 `lanes` 決定，預設是 `codebases/<repo>/`。

逐一進入 `codebases/<repo>/`，先讀該 repo 的 `AGENTS.md`、`CLAUDE.md` 與 README。記錄 repository ID、absolute path、remote、full commit、branch 與 dirty state。

只調查 `main`、`master`、`dev`、`develop` 或 repo 文件明定的 production branch。若需要 checkout/pull/branch switch：

- 保留使用者的 dirty/untracked work；無法安全切換就將該 question 設為 blocked；
- HEAD 移動後直接執行 `codegraph sync`，不先用 `codegraph status` 判斷；
- repo 沒有 `.codegraph/` 時不自行 `codegraph init`，記錄 missing index 並回報 Hub maintainer。

**完成判準：**每個 target repo 都有 guides-reviewed、branch/commit/dirty state 與 codegraph availability 紀錄；沒有用 stale/WIP branch 當成 current implementation。

## 2. 以 Codegraph 回答 exact questions

每個 repo 的 code location、flow、callers、callees、structure 與 impact 都先呼叫 `codegraph_explore(projectPath=<absolute-repo-path>)`。Query 同時帶入 question ID、入口 symbol/route/contract 名稱與要追的 flow，讓一次結果包含相關 source 與 call path。

只有 Codegraph 查不到 symbol，或要讀非程式碼 config/schema/docs 時，才用 `rg`/直接讀檔補證據；在 report 中標明 fallback 理由。不要掃所有 branches。

每個 finding 分成：

- `observed`：可追到 repo/commit/file/line/symbol 或 config path；
- `inferred`：Agent 對 observed edges 的解讀，附 basis；
- `unknown`：目前 evidence 無法回答；
- `contradicted`：兩個 current sources 不相容。

**完成判準：**每個 question 都有 observed answer、明確 inconclusive reason，或 contradiction；每個 material finding 都能追到 repo + full commit + source location。

## 3. 明列 cross-repo wire edges

Codegraph impact 只在單一 repo 內。跨 repo flow 必須分別查兩端，再人工記錄：

```text
<caller repo>@<commit>:<caller symbol/path>
  → <method/topic/event/schema and evidence path>
  → <provider repo>@<commit>:<handler symbol/path>
```

若只能證明一端，將另一端寫 `unknown`，不能把 repo-local call path 延伸成已證實的跨 repo edge。API path 名稱相同也不自動證明 consumer/provider contract 相容。

## 4. 影響與 boundary 解讀

分別記錄：

- current implementation scope；
- repository-local blast radius；
- cross-repo contract/wire impact；
- known architecture debt or test seams；
- code 與 Ticket/Domain Graph 的 agreement、gap 或 contradiction。

Service/repository/team alignment 只是 boundary evidence。它不自動建立 Bounded Context，也不把 code-derived rule 變成 confirmed node。

## 5. 產出 `03-implementation-investigation.md`

預設回傳於對話；呼叫者要求保存時使用以下固定 sections 與編號檔名：

```markdown
# 03 · <feature> Implementation Investigation

- Status: complete | blocked
- Based on: <02-domain-comparison.md path/artifact ID>
- Comparison SHA-256: sha256:<digest of exact Markdown bytes>
- Investigated at: <ISO timestamp with timezone>

## Requested questions
## Repository states
## Codegraph queries and call paths
## Observed findings
## Inferences
## Cross-repo wire edges
## Unknowns and contradictions
## Impact summary
## Step 02 feedback
## Enforcement notes
```

每個 query/finding 使用 Step 02 question ID。若用 fallback，緊鄰 finding 寫明 `codegraph fallback: <reason>`。Report digest 與內容在 v0.1 是 `prose-only, unenforced`。

## Status rule

- `complete`：每個 requested question 都有可追溯 observed answer，或已證明 evidence 本身不足而能形成精確的 Step 02 question；所有 target repos 使用允許的 primary/production branch 與已同步 index。
- `blocked`：缺 `.codegraph/`、無法安全取得 primary branch/current contract、必要 source unavailable，或結果不足以讓 Step 02 重新分類。

`complete` 不等於「找到肯定答案」，也不等於 Domain Gate passed。

## 回到 Step 02

完成 report 後停止 Step 03，將 findings 加入 Domain Comparison evidence，重新做 node matching、question ownership 與 status calculation：

- implementation fact 能回答 routing/impact → 更新 Step 02；
- code 與 graph 衝突 → 保留兩方 evidence，交 `$domain-graph` 分類並準備 authority decision；code 與 Ticket request 衝突則回 Step 02 路由 request authority；
- 新發現的 business rule → 將 observed evidence 交給 `$domain-graph` 建 candidate/decision packet；Feature Delivery 不改 canonical graph；
- 仍 blocked → Step 02 保持 non-ready，不能跳到 snapshot。

## 邊界

本步 read-only 探索 product code；不修改 product repo、不建立 tests、不執行 implementation、不留言 ticket，也不把 Codegraph 結果寫成 confirmed Domain Truth。需要 graph update 時路由 `$domain-graph`；只有該 Skill 回傳 committed full SHA 且 Step 02 重新 gate 後，Feature Delivery 才能繼續。Repository loop 仍需有效 Snapshot 與 implementation authority。
