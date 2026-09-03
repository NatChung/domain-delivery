# 00 · Feature Delivery artifact matrix

狀態：v0.1。這份 matrix 是 Steps 01–08 的跨步 contract：它擁有 artifact 名稱、producer/consumer、semantic authority、enforcement owner 與 failure routing。每個 step reference 擁有該步的完整 procedure、status computation、machine command 與 completion criterion；matrix 只列 consumer 接手前必須成立的 handoff condition，不複製 step-local gate logic。

## Chain

```text
Feature Intent
  → Domain Comparison ──┬─ optional Implementation Investigation ─┐
                        └─ optional Domain Skill decision/commit ──┤
                                      rerun Domain Comparison ─────┘
  → immutable Feature Snapshot
  → Check Projection
  → Repository Task Plan
  → product-repository changes + checker/output artifacts
  → Evidence Ledger + feedback
```

Step 03 只把 implementation evidence 回饋 Step 02；它不是通往 Step 04 的捷徑。Step 04 只接受更新後通過 Domain Gate 的 Domain Comparison 與已確認的 Domain Graph closure。

## Matrix

| Step | Input | Output artifact | Consumer | Handoff condition | Semantic authority | Enforcement owner | Failure / next state |
|---|---|---|---|---|---|---|---|
| 01 | Live/provided request evidence | `01-feature-intent.json` (`feature-intent/v0.1`) | Step 02 | Feature Intent ready | PO/request authority only confirms request intent；不確認 Domain Truth | Skill Feature Intent validator | `incomplete`；補 tracker sources 或 request answers |
| 02 | Ready Feature Intent + current compiled Domain Graph index | `02-domain-comparison.md`；必要時另產生給 `$domain-graph` 的 numbered question/evidence handoff | Step 03、Domain lane or 04 | Comparison routes explicitly to investigation/Domain decision，或 whole-node basis 已由 identified domain authority review 並可 freeze | Identified PM/domain authority confirms domain meaning；Feature Delivery only compares and routes | Kernel owns graph structure；matching、handoff adequacy 與 human review 是 `prose-only, unenforced`；`$domain-graph` owns decision packets and canonical writes | `needs_domain_decision` → 路由 `$domain-graph`，取得 committed full SHA 後重跑 Step 02；`needs_implementation_evidence` → Step 03 |
| 03 | Domain Comparison implementation questions + selected primary product repos | `03-implementation-investigation.md` | Step 02 rerun | `complete` means every requested technical question has traceable findings or explicit unresolved result | Codegraph/code is implementation evidence only；不能確認 Domain Truth | `prose-only, unenforced`：Codegraph provides source/call paths, but this hub has no validator for finding correctness or cross-repo interpretation | `blocked`；記錄 missing index/source，回 Step 02 without inventing an answer |
| 04 | `ready_for_snapshot` Domain Comparison + committed deterministic index + selected root nodes + lanes/repos/required check IDs/attestors | `specs/<feature>/snapshot/<version>/{snapshot-manifest.json,DOMAIN.md,domain-payload.json}` | Step 05–08 | Snapshot verified | Only selected confirmed L3 Domain Graph nodes are semantic authority | Domain kernel owns closure、commit/index/digests、required checks 與 immutability | Domain Gate fail → Step 02；wrong detail/contract → create superseding version, never edit frozen version |
| 05 | Verified Feature Snapshot | `05-check-projection.json` (`check-projection/v0.1`) plus numbered BDD/contract specification files | Step 06 | Projection ready | Snapshot whole-node closure is acceptance authority；projection may not add business rules | Skill Delivery Plan validator owns binding/coverage；semantic adequacy remains review-only | `incomplete`；omit unfinished projection、列 blocker，或 snapshot 缺 rule 時 rebaseline |
| 06 | Verified Snapshot + ready Check Projection + product-repo guides | `06-repository-task-plan.json` (`repository-task-plan/v0.1`) | Step 07 | Repository task plan ready | Snapshot owns meaning；each product repo owns native commands/architecture constraints | Skill Delivery Plan validator owns routing/coverage；ordering feasibility remains review-only | `incomplete`；fix routing/packet coverage；domain contradiction returns to rebaseline, not packet editing |
| 07 | One repository packet + pinned Snapshot/Projection + repo-local guides | Product-repo tests/contracts/code, checker files and `/tmp/07-...` raw outputs | Step 08 | Native red → green loop and all packet criteria complete；exit `1/2/3` may enter Step 08 only to bind a failed run | Snapshot governs behaviour；product repo governs implementation and native quality rules | Product-repo native test/contract/architecture commands；no duplicate hub pass artifact. Later `record-result` recomputes repo/checker/output binding | Check failure stays in repo loop after optional failed-run binding；snapshot contradiction stops affected loops and triggers human rebaseline |
| 08 | Verified Snapshot + checker/output files + product-repo state + independent attestation artifact | `evidence/<feature>/<run>/check-ledger.jsonl`, verified terminal hash, and numbered `08-domain-feedback.md` handoff | Delivery/release decision + `$domain-graph` | Evidence result classified as failed、kernel-verified unanchored，或 externally anchored | Evidence proves declared execution integrity, not new Domain Truth；PM/domain authority handles feedback confirmation；release owner decides rollout | Evidence kernel owns ledger integrity；`$domain-graph` owns feedback classification and canonical graph writes；authentication、anchoring與 rollout remain external/human | Missing/fail/N/A/untrusted attestation means delivery evidence gate fails；feedback routes to Domain Skill and never mutates graph or snapshot inside Step 08 |

## Stable identifiers and digests

- Step 05/06 planning files預設放在 `specs/<feature>/delivery/<snapshot-version>/`；這個目錄可迭代，只有 sibling `snapshot/<version>/` immutable。Numbered specification paths 相對 `05-check-projection.json`，`repository_path` 相對 hub Git root。
- Planning artifacts use a lowercase feature ID matching the snapshot `feature` value.
- The Step 05/06 validator prints the canonical `sha256:<hex>` digest of every valid planning JSON. Downstream artifacts store that digest when the matrix declares a binding.
- `05-check-projection.json.snapshot_digest` binds the frozen Step 04 manifest. `06-repository-task-plan.json.projection_digest` binds the exact Step 05 JSON. Step 02 retains the Feature Intent digest in its numbered Markdown report, but that linkage is `prose-only, unenforced` in v0.1.
- A path in a planning artifact is descriptive until Step 08. Evidence binding trusts only bytes read by the kernel from the declared checker/output paths.

## Gate rule

An Agent stops delivery progress at the first non-ready state and returns that artifact with its blocking reasons. Step 07 may call Step 08 only to append/report a failed run from real output; this preserves evidence without turning the state ready. It may gather Step 03 evidence only when Step 02 explicitly requests it. Human confirmation, external writes and product implementation still require the authorization stated by the active request; advancing the artifact chain does not broaden permission.
