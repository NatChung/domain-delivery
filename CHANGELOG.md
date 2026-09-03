# Changelog

Skills, kernel, schemas, template, migrations and docs ship as one atomic
SemVer release. Consumers pin a tag in `workflow.lock` and upgrade explicitly.

## 0.2.3

Four integrity defects found in review of the first consumer Hub's pull request.
Each let `upgrade` or `doctor` report an outcome it had not actually achieved.

- Immutable rollback is now a real boundary. `restore_immutable` was skipping a
  deleted tree because of an `exists()` guard, leaving migration-created files
  in place because `checkout` cannot remove what Git never tracked, ignoring the
  Git result, and running only after a migration returned normally. It now uses
  the pre-migration fingerprint as the restore instruction — deleting additions
  and checking out modifications and deletions — runs on the exception path too,
  re-verifies the trees afterwards, and says `NOT be fully restored` with the
  offending paths when it did not succeed. A migration that raises now fails the
  upgrade with exit `2` instead of a traceback.
- `upgrade` checks release identity before the first migration runs. An untagged
  package previously failed only when the lock was written, by which point the
  migrations had already changed the Hub, contrary to ADR 0008's pinning rule.
- `doctor` verifies the recorded tag against Git. It compared the lock's `tag`
  text with `VERSION` and never asked whether that tag points at the installed
  HEAD, so deleting the release tag still reported healthy.

## 0.2.2

- Print `untagged` rather than `None` where an untagged installation has no
  release tag to name.

## 0.2.1

- The Hub CLI suite no longer depends on whether this repository's own working
  copy sits on a tagged commit. 0.2.0's tag rule made every test that installs
  from the live tree fail during development, for a reason unrelated to what
  those tests assert. They now opt out explicitly; the tag rule itself is
  covered by its own tests.

## 0.2.0

Three integrity defects found in review. The lock's job is to say truthfully
what is installed; each of these let it say something false.

- `workflow.lock` no longer fabricates a tag. `package_tag` returned
  `v{VERSION}` when no tag pointed at the checked-out commit, so any working
  state could be recorded and reported as a published release. `init` and
  `upgrade` now refuse an untagged commit; `--allow-untagged` records one
  deliberately with `tag: null`, which `doctor` keeps reporting.
- `doctor` treats a missing `.domain-delivery` gitlink as a finding. It
  previously only compared a gitlink that existed, so a workflow present in one
  working copy but never committed reported healthy while a fresh clone got no
  workflow at all.
- Migrations can no longer rewrite the delivered record. `upgrade` fingerprints
  `specs/**` and `evidence/**` around every migration; one that changes them is
  restored from Git and fails the upgrade without updating the lock. This was
  prose in `migrations/README.md` and is now enforced.
- `version_key` follows SemVer precedence: a prerelease sorts below its
  release, and numeric identifiers compare numerically. It previously ranked
  `1.0.0-alpha` above `1.0.0`.
- `delivery-hub` SKILL.md corrected: `hub.py` lives inside the submodule, so a
  completely absent checkout cannot run `doctor` at all. That case belongs to
  the Hub README's clone order; the finding covers a partial checkout.

Locks written by earlier versions stay readable. One written from an untagged
commit will now be reported by `doctor` until it is re-pinned to a release.

## 0.1.7

- `doctor` compares `workflow.lock` against the commit the Hub's own history
  records for the submodule, not only against what is checked out. Those three
  can disagree, and until now `doctor` reported healthy while a fresh clone of
  the Hub would have installed a different version.
- `upgrade` no longer calls a downgrade an upgrade, and says when the submodule
  move and the lock still need committing together.

## 0.1.6

- `upgrade` refuses when the installed workflow itself has uncommitted changes
  or untracked files. 0.1.4's submodule exemption was too wide: it ignored every
  status entry under `.domain-delivery`, so a hand-edited installation could be
  recorded into `workflow.lock` and every later `doctor` would call it healthy.
  The gitlink move that starts an upgrade is still allowed.
- `doctor` no longer initialises the submodule. ADR 0008 asked it both to
  auto-initialise and to be read-only; read-only wins, because initialising
  clones over the network and writes to the working tree. A missing
  installation is now a finding naming the command to fix it.
- `doctor` also reports modified files inside the installation.
- ADR 0008 amended to record that resolution.

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
