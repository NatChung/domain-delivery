# AGENTS.md

Execution constraints for coding agents in the {{PROJECT}} Delivery Hub. Method
and domain meaning live in linked documents; do not duplicate them here.

## Start here

1. Read [`docs/session-start.md`](docs/session-start.md).
2. Read the pinned shared method,
   [`.domain-delivery/docs/workflow.md`](.domain-delivery/docs/workflow.md).
3. Read [`CONTEXT-MAP.md`](CONTEXT-MAP.md) and
   [`docs/domain/INDEX.md`](docs/domain/INDEX.md).
4. For a concrete product change, enter every affected product clone and read
   that repository's own `AGENTS.md`, `CLAUDE.md` and README before acting.

## Pinned workflow

`workflow.lock` pins the tag, commit and package digest of the shared workflow
installed at `.domain-delivery/`. Check it before Domain or Delivery work. On a
mismatch, stop and run `doctor`, then `upgrade`:

```bash
python3 -B .domain-delivery/skills/delivery-hub/scripts/hub.py doctor
```

Do not edit anything inside `.domain-delivery/`. It is a pinned submodule; fixes
belong upstream and arrive through `upgrade`.

## Repository role and artifact authority

This is a delivery Hub, not a product repository.

- `docs/domain/**`: canonical Domain Graph record, including candidates and
  disputes; only `confirmed` nodes are accepted semantic truth.
- `domain-index/index.json`: generated index; regenerate, never hand-edit.
- `specs/<feature>/snapshot/**`: immutable execution basis; supersede with a new
  version instead of editing.
- `evidence/<feature>/<run>/`: kernel-appended ledgers; append only.
- product clones: independent repositories, ignored by this Hub.

Delivery lanes declared in `hub.yaml` are routing labels, not Bounded Contexts.

## Domain authority

Code, tickets, documents, analytics and interviews create evidence and
candidates. They do not confirm domain meaning. Only an identified PM/domain
authority may promote a node to `confirmed`; selected snapshot nodes must be
`confirmed L3`. Unknown authority means the node stays `candidate`.

Do not create empty Bounded Context folders in advance. Compare capabilities
across journeys before proposing a durable boundary.

## Delivery execution

- Use the `domain-graph` Skill for Domain-lane discovery, candidate shaping,
  decision packets and graph publication.
- Use the `feature-delivery` Skill for a concrete request moving through Feature
  Intent, active slice, Snapshot, repository loops and bound evidence. Domain
  gaps return to the Domain lane; they are not patched into a Snapshot.
- Freeze a snapshot before deriving BDD or writing product code.
- Run native TDD, contract and architecture checks inside each product repo.
- Evidence must bind the snapshot digest, repository-scoped check, checker file,
  repo commit/dirty state and output digests, then receive a separate trusted
  attestation declaration. Exit `3` is not pass.
- Do not change files inside a product repo as a side effect of Hub work.

## Git and writing

- Preserve user changes and unrelated untracked files.
- New rules must be mechanically enforced or explicitly labelled
  `prose-only, unenforced` with a reason.

Add {{PROJECT}}-specific constraints below this line.
