---
name: delivery-hub
description: 安裝、檢查與升級 Delivery Hub 所使用的 shared workflow 版本。當使用者要建立新的 Delivery Hub、把既有 repository 變成 Hub、確認目前 pinned 版本是否正確、修復缺少的 Hub 檔案，或把 Hub 升到新的 workflow release 時使用；不做 Domain Graph discovery、不 freeze Snapshot、不執行 repository delivery loops。
---

# Delivery Hub

管理 Hub 與 shared workflow package 之間的安裝關係。Package 以 Git submodule
固定安裝在 Hub 的 `.domain-delivery/`，由 Hub root 的 `workflow.lock` pin 住 tag、
full commit 與 package digest（[ADR 0008](../../docs/adr/0008-distribute-shared-workflow-as-pinned-submodule.md)）。

Domain 與 Delivery lane 分別由 [`domain-graph`](../domain-graph/SKILL.md) 與
[`feature-delivery`](../feature-delivery/SKILL.md) 負責；本 Skill 不碰 domain
meaning、Snapshot 或 evidence。

## 三個命令

全部從 Hub root 執行，exit code 一致：`0` pass、`1` findings、`2` invalid input
或被拒絕的動作。

```bash
python3 -B .domain-delivery/skills/delivery-hub/scripts/hub.py doctor
```

| 命令 | 用途 |
|---|---|
| `init --project <name>` | 首次安裝：建立 Hub skeleton 與 `workflow.lock` |
| `doctor` | read-only 檢查：lock 與實際 checkout 是否一致、Hub 檔案是否齊全、有無 pending migration |
| `upgrade` | 移到目前 checkout 的版本：依序跑 pending migrations，更新 lock |

## init

```bash
python3 -B .domain-delivery/skills/delivery-hub/scripts/hub.py init \
  --project <name>
```

- `workflow.lock` 已存在時直接停止並要求改用 `upgrade`，`--force` 也不繞過。
- checkout 的 commit 上沒有對應 VERSION 的 release tag 時拒絕執行。lock 記錄的是
  release，不會用 VERSION 湊一個 `v<VERSION>` 出來。確實要用未 tag 的狀態時加
  `--allow-untagged`，lock 的 `tag` 會是 `null`，`doctor` 會一直回報它。
- 只補缺少的檔案，不覆蓋既有檔案。
- `--force` 只覆蓋 template 產生的檔案；`docs/domain/**`、`specs/**` 與
  `evidence/**` 永遠不覆蓋。
- 永不刪除任何檔案，包含不相關的 untracked files。
- 不放入任何 synthetic domain node。範例只存在於 package 的 `examples/`。

安裝後要做的事：填 `hub.yaml` 的 `request_source.kind`、`hub_tracker.kind`、
`code_explorer.kind` 與 `lanes`，把 `CONTEXT-MAP.md` 與 `docs/domain/INDEX.md`
換成真實內容，然後 commit。`hub.yaml` 只放 kind 與 path，不放帳號、cloud ID 或
secret。

第一次在既有 repository 安裝時，先加 submodule：

```bash
git submodule add https://github.com/NatChung/domain-delivery.git .domain-delivery
git -C .domain-delivery checkout <tag>
```

`.gitmodules` 一律使用 public https URL；本機身分用 `url.<alias>.insteadOf`
處理，不要把 SSH alias 寫進 `.gitmodules`。

## doctor

read-only：不 clone、不寫檔、不碰 Git 設定。

注意 `hub.py` 本身就住在 submodule 裡，所以 `.domain-delivery/` 完全沒 checkout
時根本執行不到 `doctor`——那個情況要照 Hub README 的 clone 順序處理。`doctor` 的
missing-installation finding 針對的是目錄存在但空的、或只 checkout 一半的情形。

回報 lock 與安裝不一致（version、tag、commit、package digest）、安裝目錄內被修改
或多出來的檔案、缺少的 Hub 檔案、未替換的 `{{PROJECT}}` placeholder，以及 pending
migrations。

也比對 Hub 歷史記錄的 submodule gitlink——那是別人重新 clone 會拿到的版本。
gitlink 跟 lock 不一致，或 Hub 歷史根本沒有 gitlink（工作區有、但沒 commit 進去），
都是 finding：別人 clone 會拿到不同版本，或完全沒有 workflow。

lock 的 `tag` 是 `null` 時也回報：那份安裝釘在沒有 release tag 的 commit 上。lock
有 tag 時則向 Git 查證：那個 tag 必須真的指在安裝的 HEAD 上。tag 被刪掉或移到別的
commit，即使追蹤的 bytes 一個都沒變，也是 finding——lock 的 tag 欄位是對 Git 的
宣稱，不是自己說了算的文字。digest 涵蓋 release 內每個 Git 追蹤的檔案，包含
`docs/`；不符代表 `.domain-delivery/` 被就地修改過——修正方式是把改動送回
upstream，不是留在 Hub 裡。

任何 lane 工作開始前先跑 `doctor`；`1` 以上都先處理完再繼續。

## upgrade

```bash
git -C .domain-delivery fetch --tags
git -C .domain-delivery checkout <new-tag>
python3 -B .domain-delivery/skills/delivery-hub/scripts/hub.py upgrade
```

- Hub working tree 不乾淨時拒絕執行；先 commit 或另外收起改動。`.domain-delivery`
  這個 gitlink 的移動本身不算，因為那就是升級的第一步。
- 安裝目錄內若有未 commit 的改動或多餘檔案也拒絕執行；否則 lock 會把手改過的
  bytes 記成正式版本，之後每次 `doctor` 都會說 healthy。
- release 身分在第一個 migration 跑之前就先驗：package 沒有對應的 release tag
  時直接拒絕，Hub 還沒被動過。不是等寫 lock 才發現。
- 沒有 upgrade window：所有 pending migrations 依名稱順序全部執行。
- 已完成的 Snapshot 與 evidence 永不重寫，而且這條是機械執行的：每個 migration
  前後比對 `specs/**` 與 `evidence/**` 的 digest，一有變動就從 Git 還原、中止
  upgrade、不更新 lock。migration 自己丟例外時走同一條還原路徑。還原用的是
  migration 前的 fingerprint：新增的檔案刪掉，改動或刪除的檔案從 Git checkout
  回來。還原後再比對一次，只有真的回到原狀才會說已還原；沒還原乾淨時會明講
  「NOT be fully restored」並列出要手動處理的路徑。
- 目標版本比目前低時會說 `downgraded`，不會謊稱 upgrade。
- 完成後把 submodule 移動與新的 `workflow.lock` 放在同一個 reviewed commit。

Migration 由 package 的 [`migrations/`](../../migrations/README.md) 擁有。`init`
會把當時已存在的 migrations 記成 already applied，因為新 Hub 沒有舊資料要轉。

## 邊界

- 不建立、修改或確認任何 domain node。
- 不 freeze Snapshot、不記錄 evidence、不執行 repository loops。
- 不修改 `.domain-delivery/` 內容。
- commit、push、PR 各需另外的 active request；本 Skill 只改 Hub 檔案與 lock。
