# 05 · Dual-driver acceptance (optional advisory)

## Activation and authority

Set `extensions.dual_driver.enabled: true` in the Step 05 projection to opt in;
missing or false means the existing flow. This is a planning flag, **not a new
CLI option**. Copy the configuration to Step 06 `extensions` and reference this
procedure in packet completion criteria. Initially it is advisory: report its
status separately from existing readiness and evidence gates. An incomplete
experiment earns no dual-driver claim, but adds no frozen required check.

All rules in this reference are **prose-only, unenforced**: existing validators
accept the extensions object but do not validate its contents, run drivers,
classify surfaces or compute coverage. A product adapter may automate these
checks; describe its enforcement separately. No framework or runtime is shipped
here. Existing required checks still have to pass regardless of this flag.

This procedure applies to domain-kind Graph-derived BDD after Steps 02/04. It
neither confirms meaning nor bypasses comparison, whole-node acceptance or freeze.
UI-kind accepted AC can reuse the driver technique, but cannot claim Graph rule
coverage. If a new obligation is to become required, return to Step 04 for an
explicitly accepted superseding Snapshot; never edit a frozen bundle.

## 1. Plan once, bind per surface (Steps 05–06)

Inputs: verified Snapshot/digest, frozen executable rule refs and Graph commit,
Step 05 feature files projected from that basis, ready projection, repository
packets, public test seams and the selected UI surfaces. Use `web` initially;
add `app` through its native automation adapter when available. App bindings
need their own evidence; web success never proves app coverage.

Compile scenario outlines with the feature language's standard compiler. Keep
one unchanged Given/When/Then text and example set, a stable BDD scenario ID and
1-based example row. Generate the catalog from these files instead of writing a
second UI specification. A driver binds actions, fixtures and oracles, not new
business meaning. Source-rule disagreement routes back to Step 02/04.

Use this optional planning fragment in both existing `extensions` objects:

```json
{
  "dual_driver": {
    "enabled": true,
    "mode": "advisory",
    "surfaces": ["web"],
    "catalog_path": "reports/dual-driver/catalog.json",
    "report_path": "reports/dual-driver/summary.json"
  }
}
```

Paths are product-repository-relative retained artifacts, not new fields in the
planning schema or replacements for Step 06's existing evidence input contract.
In cross-repository plans, document each path's owning repository and pass the
same feature digest/BDD IDs to each adapter. Packet notes identify driver
commands, API provider dependency, fixture lifecycle, UI route/control and oracle
for each surface, unsupported rows with reasons, and binding-fault scope.

Catalog row contract (advisory; adapters choose serialization):

| Field | Meaning |
|---|---|
| `id`, `bdd` | Unique catalog row ID; `bdd` contains feature path, stable scenario ID and example row (1 for a plain scenario) |
| `featureDigest`, `snapshotDigest`, `graphCommit` | Exact source feature bytes and frozen semantic basis |
| `graphNodes`, `ruleRefs` | Node IDs plus exact frozen node/field/statement references; broad historical tags alone prove nothing |
| `driver`, `uiSurface`, `surface`, `reason` | API or UI driver, web/app target (null for API), actual ui/mixed/api-only classification and explanation |
| `steps`, `ruleEvidence` | Exact expanded steps, completed runtime surface/reason per step, and reviewed rule-to-action/oracle links |
| `run`, `bindingFault` | Repository commit/dirty digest, checker/build/environment, attempt/status/exit, retained artifacts and binding-fault evidence refs |

Keep planned classification distinct from actual runtime classification. An
unsupported UI row is explicitly api-only/skipped with a reason, never a UI pass.

## 2. API first, then the same scenarios through UI (Step 07)

1. Execute the selected rows through the API driver at the repository's public
   API seam. Record whether this is in-process or actual HTTP; an in-memory pass
   does not prove a deployed wire. Retain existing authorization, replay and raw
   invalid-request probes even when UI controls prevent those requests.
2. Require API pass for the selected batch before running its UI bindings.
   On API failure, retain output and repair the API loop; do not label a later
   UI-only diagnostic as completed dual-driver acceptance.
3. Run the identical expanded rows using each selected surface's UI driver.
   Reset per-row fixtures and deterministic clock/identity state between drivers;
   carry scenario meaning, not state leaked from the API run.
4. Use ordinary visible controls and assert screen outcomes plus named read-only
   backend oracles where needed. For UI-disabled negatives, assert the guard and
   unchanged relevant state, without inventing an HTTP response.
5. Attach completed step surfaces/reasons and rule-specific action/oracle evidence
   to the actual attempt. Preserve logs, traces, screenshots, source/build digests
   and exit codes under `reports/dual-driver/<run>/<driver>/<surface>/`.

### Honest surface and UI credit

- `ui`: the rule's decisive action and observable assertion traverse real user
  controls and UI outcomes on the selected surface.
- `mixed`: real UI action/guard and screen assertions combine with non-UI setup
  or a read-only backend oracle. Credit only the exact rule actually exercised
  through that UI action/guard, not every rule used to prepare the fixture.
- `api-only`: no ordinary UI path exercises the rule (for example a raw replay,
  foreign-resource probe or setup-only effect). Preserve API evidence and reason.

Fixtures, seeded data, local/session storage, direct HTTP, browser `fetch` or
request clients, DOM mutation, forced clicks and injected application actions
**never earn UI credit**. Such setup can support a mixed row, but cannot replace
its decisive UI action. A passing row with those bypasses as the tested action
is api-only. A read-only database oracle alone proves no UI binding.

Count a rule only with reviewed exact rule mapping and fresh passed evidence for
all steps needed for its claim. Failed, missing, skipped, stale or flaky attempts
(including a retry after failure), and api-only rows earn zero UI credit. A fresh
clean rerun may establish new evidence; retain the prior attempts. Match feature
bytes, expanded steps, Snapshot, repository/build state and chosen surface before
joining results to catalog declarations. Record deferred/unsupported surfaces as
gaps rather than quietly removing them from the declared scope.

## 3. Prove each new UI binding can fail (Step 07)

For each new UI action binding on each surface, select a representative BDD row
that depends on it. In an isolated test build, temporarily break only the actual
application control-to-action binding (for example make its handler a no-op).
Keep the feature, test assertions, API implementation and fixtures unchanged.

Record the patch, source/build identifiers, commands, exits and artifacts for:

1. baseline API and UI pass;
2. broken binding: same API row passes, same UI row fails because the action no
   longer reaches its expected outcome (environment/syntax failure is invalid);
3. restored original bytes and rebuilt app: same UI row passes again.

Force rebuild/cache invalidation for both broken and restored builds. Compare
before/after file digests, revert the fault and verify no mutation remains in the
final diff. Grouping rows sharing one binding is allowed only with an explicit
binding-to-row map and rationale; another control or app surface needs its own
experiment. An unproven binding earns no UI credit and the advisory report stays
incomplete. The fault build is diagnostic evidence, never the final delivery build.

## 4. Report coverage and hand off (Step 08)

Report **Graph rules verified via UI** per surface as `N / D` (and percentage
only when D is known and nonzero):

- `D`: distinct `(node ID, field, exact statement)` executable rules in the
  frozen active slice, covering the Step 05 frozen-rule field set; pin the
  Snapshot digest and show the enumerated denominator. Api-only and unsupported
  rules stay in D. Never substitute the whole live Graph or just selected tests.
- `N`: distinct rules in D with qualifying runtime UI evidence under this
  reference, including a successful binding-fault proof for each new binding
  used by that claim. Deduplicate rules across scenarios/example rows. Mixed
  rows qualify only for their reviewed UI-exercised rule refs.

Show API counts, UI counts, explicit api-only skips, failures/flakes/missing/stale
rows, unproven bindings and deferred surfaces separately. If only a pilot subset
has mappings, label counts as partial; if D is unavailable, report distinct
verified rule refs and **denominator unknown**, without a percentage. A union
across surfaces may be shown only as an explicitly labelled union, never as proof
that every surface passed. UI-kind AC counts are separate and D is not applicable.

Step 08 retains the catalog, mapping, driver results and binding experiment with
the existing run artifacts, reports advisory `complete | incomplete | disabled`
separately from kernel evidence status, and preserves actual failed exits. Existing
checker/output/attestation binding and external retention/anchoring requirements
remain in force; a matrix or metric is not a kernel attestation.

### Completion checklist

- [ ] Opt-in flag, frozen basis, exact feature/row IDs and target surfaces recorded.
- [ ] API selected batch passed before identical rows ran through each UI driver.
- [ ] Actual surfaces/reasons and exact rule/action/oracle links reviewed.
- [ ] Every new credited UI binding has broken → restored proof and clean final bytes.
- [ ] Catalog joins only fresh qualifying attempts; unsupported rows/surfaces are visible.
- [ ] Metric has enumerated scope/denominator or an explicit unknown/partial label.
- [ ] Retained artifacts and separate advisory status handed to Step 08; frozen gates unchanged.

## Reference implementation

The method was piloted in [chasr PR #319](https://github.com/KicksCrew/chasr/pull/319):
[dual-driver guide](https://github.com/KicksCrew/chasr/blob/3e75d6b59011e98b91513c7bce1321c0a226b780/docs/e2e/dual-driver.md)
and [execution report](https://github.com/KicksCrew/chasr/blob/3e75d6b59011e98b91513c7bce1321c0a226b780/reports/dual-driver-pilot.md).
These consumer-specific links are historical reference material, not a dependency
or normative business rule; access may require repository permission.
