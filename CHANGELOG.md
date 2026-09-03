# Changelog

Skills, kernel, schemas, template, migrations and docs ship as one atomic
SemVer release. Consumers pin a tag in `workflow.lock` and upgrade explicitly.

## 0.1.5

- `workflow.lock`'s package digest now covers every file the release ships,
  taken from what Git tracks. Earlier versions hashed a hand-written list of
  directories, so `docs/` and `examples/` fell outside it: someone could edit
  `.domain-delivery/docs/workflow.md` — the method every Hub pins — in place and
  `doctor` would still report healthy. Existing locks will report a digest
  mismatch once; re-run `upgrade` to record the new one.
- `doctor` also reports untracked files inside the installation, which the
  digest cannot see by construction.

## 0.1.4

- Parse `git status --porcelain` from unstripped output. Stripping it removed
  the leading space of an unstaged entry, shifting every path by one character,
  so 0.1.3's submodule exemption never matched a real unstaged submodule move
  and `upgrade` still refused.

## 0.1.3

- `upgrade` no longer refuses because of the submodule move that starts an
  upgrade. Moving `.domain-delivery/` to the new tag is step one of the
  documented flow, so the superproject is always dirty at that path by the time
  `upgrade` runs; 0.1.2 and earlier made the command unusable as written. Every
  other uncommitted change still blocks, and the refusal now names the paths.

## 0.1.2

- Remove two consumer-flavoured strings the first sanitisation pass missed: a
  reference sentence naming the first consumer Hub by initials, and an
  industry-hinting term node in a kernel test fixture. Both were prose and
  fixture text; no behaviour changed.

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
