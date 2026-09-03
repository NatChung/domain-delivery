# 99 · 維護 Feature Delivery Skill

只有修改本 Skill、numbered references、schemas、scripts、tests 或 eval cases 時讀本文件；正常 Feature Delivery 不讀。

## Contract authority

Python validators 是 executable shape 與 gate authority：

- `validate_feature_intent.py`：`feature-intent/v0.1`；
- `validate_delivery_plan.py`：`check-projection/v0.1` 與 `repository-task-plan/v0.1`。

`feature-intent.schema.json` 與 `05-06-delivery-plan.schema.json` 是 machine-readable mirrors。修改任何 field set、enum、ID pattern 或 schema version 時，同一次 change 必須更新 validator、schema 與 parity tests。Numbered references 中的 YAML/JSON 是 authoring examples，不是第四份 contract authority。

## Deterministic validation

執行 Skill tests、plugin-kernel tests 與 packaging validation：

```bash
python3 -B scripts/check_doc_path_references.py
python3 -B -m unittest discover -s scripts/tests -v
python3 -B -m unittest discover -s .domain-delivery/skills/feature-delivery/tests -v
python3 -B -m unittest discover \
  -s .domain-delivery/kernel/tests -v
python3 -B /Users/natchung/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  .agents/skills/feature-delivery
```

前兩個命令守住 hub folder 與 active Markdown／HTML 的 reference integrity；
若搬動 Skill、Plugin 或 canonical docs，finding 會用 `file:line` 指出要一起
更新的文件。Active docs 的歷史或故意未建立 reference 只能在
`scripts/path-reference-policy.json` 用「檔案＋該行內容」精確保留；不能
allow 整份 active 文件。`docs/archive/` 不屬於 active-document scan scope。

Contract parity tests 必須同時證明 schema/runtime 的 top-level 與 nested required fields、enums、schema versions 及 ID patterns 一致。Runtime-only tests 不足以宣稱 mirror 沒有 drift。

## Fresh intake forward test

`run_intake_evals.py` 是 comparator，不會呼叫 Agent。每次 forward test 都必須先由 fresh、independent Skill invocation 讀 `ticket.json`，把每個 case 的新 `01-feature-intent.json` 寫到 repo 外的 output directory，命名為 `<case-id>.json`。使用 committed 或先前 run 的 output 不算 behavior regression。

```bash
eval_outputs="$(mktemp -d)"
# Independent invocation writes ${eval_outputs}/<case-id>.json here.
python3 -B .domain-delivery/skills/feature-delivery/scripts/run_intake_evals.py \
  --cases .domain-delivery/skills/feature-delivery/tests/fixtures/intake \
  --outputs "$eval_outputs"
```

Runner 機械式要求 explicit `--outputs`、拒絕 hub 內目錄、要求每個 case 都有 validator-valid output，再與 `expected.json` semantic invariants 比對。輸出的 fresh/independent provenance 是 `prose-only, unenforced`：runner 無法區分 stale external bytes，也不能證明是哪個 Agent 生成；orchestration 必須每次建立新的 `mktemp` directory，dispatch fresh invocation，並在同一 run 內生成後立即比較。Comparator 不取代 request/domain authority。

## Independent review

對 router、reference hierarchy 或 gate semantics 的實質修改完成後，以 fresh reviewer 檢查：

- router 是否只負責 routing；
- matrix 是否只擁有 cross-step contract；
- current step reference 是否獨自擁有 procedure 與 completion criterion；
- script dependency 是否維持 skill adapter → repository-neutral plugin kernel；
- 每個 prose-only boundary 是否仍準確。
