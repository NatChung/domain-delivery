# Changelog

Skills, kernel, schemas, template, migrations and docs ship as one atomic
SemVer release. Consumers pin a tag in `workflow.lock` and upgrade explicitly.

## 0.1.1

- Fix the Codex marketplace template: `policy.authentication` must be
  `ON_INSTALL`; the 0.1.0 template emitted an unsupported `NONE`.

Known gap, tracked for a later release: `doctor` compares `workflow.lock`
against the checked-out submodule, but not against the superproject's recorded
gitlink (`git ls-tree HEAD .domain-delivery`).

## 0.1.0

First release.

- Two-lane method: a versioned Markdown Domain Graph and a feature-scoped
  Delivery lane meeting at an immutable Snapshot (`docs/workflow.md`).
- `kernel/`: deterministic graph compilation, index gating, Snapshot freeze and
  verification, drift reporting, and hash-chained evidence with separate result
  and attestation declarations.
- `skills/delivery-hub`: `init`, `doctor` and `upgrade`, with `workflow.lock`
  pinning tag, full commit and package digest.
- `skills/domain-graph`: discovery, candidate shaping, authority decision
  packets, traceable confirmation, index publication and drift feedback.
- `skills/feature-delivery`: Steps 01–08 from request intake to bound evidence,
  with intake, projection and task-plan validators.
- `template/`: the Hub skeleton, including both host marketplaces pointing at
  `./.domain-delivery`.
- `migrations/`: the upgrade mechanism. No migrations in this release.
- `examples/`: a synthetic three-node graph that compiles and gates.
- Method decision records 0004–0009.
