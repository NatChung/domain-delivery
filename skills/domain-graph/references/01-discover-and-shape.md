# 01 · Discover journeys, compare capabilities, shape boundaries

## 何時讀

使用者帶來新的 domain evidence、要求建立 journey/capability coverage、比較多個 journeys，或尚未有足夠 basis 提出 Bounded Context candidate 時讀本檔。

## Enforcement note

Evidence freshness、claim classification、capability comparison、boundary
judgment 與本路徑 completion 都是 `prose-only, unenforced`，因為它們需要
source interpretation 與 domain review。Shared Kernel 只在 canonical nodes
寫入後驗證 schema、references 與 deterministic index；它不證明 discovery
結論正確。

## 進入條件

- 已從 `docs/domain/INDEX.md` 確認 live graph maturity，並讀相關 canonical nodes；
- 已寫明 discovery scope：journeys、customer/operations outcome、系統或 business area；
- 已分清 source access 與 write permissions。拿不到的 source 明列 unavailable，不自行補故事。

## 1. 建立 evidence register

對每個 source 記錄 identifier/URL/path、source kind、owner/author、observed/published/fetched date、repo commit/branch（若適用）、freshness limitation 與它實際支持的 claim。把 claims 分成：

- `observed`：來源直接顯示；
- `inferred`：由多筆 observation 推導，附推導理由；
- `disputed`：可信來源互相衝突；
- `unknown`：目前沒有足夠 evidence。

Tracker/知識庫/interview statements 仍須標明 speaker/authority scope。Archive、ticket、code 或網路資料不因可引用就變成 canonical truth。

若需看 implementation，先進 affected `codebases/<repo>/` 讀該 repo 的 `AGENTS.md`、`CLAUDE.md`、README，只查 primary/production branch，對 code location/flow/impact 先用 `codegraph_explore`。Codegraph impact 不跨 repo；每條 cross-repo wire edge要在兩側分別留下 evidence。全程 read-only。

## 2. 由 journey 找 capability

逐條描述 journey 的 actor、trigger、business outcome、important language、rules/state、handoffs、failure/exception 與未知點。不要先用 App/Web/Server、team、repository、API 或 process stage 當 Bounded Context。

把 observations 聚成 candidate capabilities，並在多個 journeys 之間比較：

- language 與 business meaning 是否一致；
- rules、state、lifecycle 與 invariants 是否一起改變；
- decision authority、owner 與 change cadence 是否一致；
- contracts/handoffs 是否顯示 translation 或 autonomy boundary；
- 同名詞是否其實有不同模型，或不同名稱是否其實同一 capability。

每個 proposed capability 必須可追回 evidence；保留 alternatives 與反證，不用漂亮圖取代 claim-level traceability。

### 2a. Capability 判斷五測試(機場比喻)

Capability 是「check-in 這件事」,不是做這件事的櫃台(service)。判斷:

1. **動詞+受詞**:能說成一件業務能力(「保存顧客的購買興趣」);只能說成畫面或步驟的不是。
2. **跨 journey 重複**:多條 journey 用到它。
3. **業務決策**:這裡有決策發生(通不通知、給不給退);純轉資料的管道不是。
4. **關掉測試**:關掉後顧客失去一種「事」,不只是一個畫面。
5. **排除**:不是 UI、不是 journey 段、不是 repo/service、不是一次性 feature。

粒度訊號:它有自己的規則集與資料,寫得出 scope/out_of_scope 而不拖下半個系統。同一能力可有多個實作點(check-in 在櫃台/kiosk/App 都能做);一個 service 也可能兼做多件事 —— service 邊界不當能力邊界。

### 2b. 每個 journey step 問六題(源自 16 段 §12)

1. 這一步做了什麼業務決策?
2. 它使用哪些 domain terms?
3. 它保護什麼 invariant?
4. 哪個系統保存 state truth?
5. 誰有權改變這條規則?
6. 上下游交換了什麼 contract?

## 3. 提出 boundary candidate

只有數筆 observations 共同支持真實 boundary 時，才提出 Bounded Context candidate。候選必須說明：

- 它包含與排除哪些 capabilities/journeys；
- boundary signals 與 counter-evidence；
- language/model ownership、提供或共同擁有的 contracts；
- unknown authority、blocking questions 與相鄰 candidate alternatives。

有足夠 evidence 時可進入 `candidate L2`，不必先 confirmed。沒有足夠 evidence 時保留 top-level journey/capability discovery，不建立空 `docs/domain/bounded-contexts/<context>/`、`.gitkeep` 或預想中的 context tree。

### 3a. Boundary 數量紀律(源自 16 段 §11C)

不預設「要切幾個 BC」。跑完主要 journeys、完成 capability 比較後,數量
自然浮現;在那之前直接指定數量只是猜測。Folder 依 lazy 原則建立
(見 `docs/domain/SCHEMA.md`)。

## 4. 分類 graph work

將每個 gap 對應到 `docs/domain/SCHEMA.md` 的 exact type：`authority`、`bounded_context`、`capability`、`contract`、`journey`、`policy`、`question` 或 `term`。不要發明新 type；不要把所有有趣關聯放入 `requires`。

Discovery 結果預設在對話中交付。只有使用者指定或 maintainer 已接受 working location 時才持久化非-canonical working paper；`docs/domain/**` 只能放 schema-valid semantic nodes與必要 index/contract docs，不能成為 raw research dump。

## 完成判準

本路徑完成時必須有：

- scoped journey/evidence register，含 freshness 與 unavailable sources；
- claim-level observed/inferred/disputed/unknown 分類；
- cross-journey capability comparison與 boundary alternatives；
- proposed node types/relationships、authority gaps與 exact decision questions；
- 清楚路由：需要更多 evidence 留在本路徑；需要 human decision 進 02；已有可 author canonical candidate 才進 02。

本路徑不宣稱 Graph v0、boundary confirmation、Domain Gate 或 delivery readiness。
