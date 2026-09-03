# AGENTS.md

Execution constraints for agents working in this repository. This is the shared
workflow package, not a Delivery Hub: it has no Domain Graph, no Snapshots and
no evidence of its own.

## Product neutrality

This repository must contain zero consumer content: no client or organisation
names, product names, service repository names, people, tracker keys or private
URLs — in files, in paths, or in commit messages
([ADR 0009](docs/adr/0009-public-shared-workflow-repo-with-fresh-history.md)).
Every example is synthetic and lives in `examples/`, `template/` or a test
fixture. When a real Hub's detail is needed to explain something, describe the
shape instead of naming it.

## Layout authority

- `docs/workflow.md` — the method source of truth. Change it deliberately; every
  Hub is pinned to a version of it.
- `docs/adr/**` — shared-method decisions. A Hub's own decisions do not go here.
- `kernel/` — deterministic integrity machinery. Repository-neutral, stdlib only,
  never imports a lifecycle Skill.
- `skills/**/SKILL.md` — router files using only `name`, `description`, Markdown
  and relative links, so both hosts accept them unchanged.
- `template/` — what `init` writes into a Hub. `{{PROJECT}}` is the only
  placeholder.
- `migrations/` — see [`migrations/README.md`](migrations/README.md).

## Change rules

- Skills, kernel, schemas, template and docs release together. Do not version
  a component independently.
- Renaming `.domain-delivery`, a Skill directory or `kernel/scripts/kernel.py`
  breaks every consumer. Treat those names as contract.
- A change that alters what a Hub's files must look like needs a migration.
- Never rewrite the semantics of frozen Snapshots or evidence; add a new
  version instead.
- New rules must be mechanically enforced or explicitly labelled
  `prose-only, unenforced` with a reason.

## Before committing

```bash
python3 -B -m unittest discover -s kernel/tests
python3 -B -m unittest discover -s skills/feature-delivery/tests
python3 -B -m unittest discover -s tests
```

Commit messages are a published surface. Keep them free of consumer
identifiers, exactly like the files.
