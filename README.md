# domain-delivery

A repository-neutral, two-lane delivery workflow for AI coding agents, shipped
as one plugin that runs on Codex or Claude Code.

- The **Domain lane** keeps a Markdown-first Domain Graph that never stops
  learning. Only an identified human authority can confirm meaning.
- The **Delivery lane** takes only the confirmed slice a feature needs, freezes
  it into an immutable Snapshot, projects executable checks, runs per-repository
  loops, and binds hash-chained evidence back to that Snapshot.

The lanes meet at exactly one place: the frozen Snapshot. Later graph edits show
up as drift, not as silent changes to work already in flight.

Method source of truth: [`docs/workflow.md`](docs/workflow.md).

## Install into a Delivery Hub

A Hub is any repository that coordinates delivery for one product. Install this
package as a submodule at the fixed path `.domain-delivery/` and pin a tag:

```bash
git submodule add https://github.com/NatChung/domain-delivery.git .domain-delivery
git -C .domain-delivery checkout v0.2.2
python3 -B .domain-delivery/skills/delivery-hub/scripts/hub.py init --project my-product
```

`init` writes the Hub skeleton — `hub.yaml`, both host marketplaces,
`CONTEXT-MAP.md`, an empty typed `docs/domain/` tree, thin `AGENTS.md` /
`CLAUDE.md` adapters — and a `workflow.lock` pinning tag, full commit and package
digest. It installs no domain nodes: a Hub's graph must contain only what its own
evidence supports.

Then `doctor` before work, and `upgrade` to move to a new release:

```bash
python3 -B .domain-delivery/skills/delivery-hub/scripts/hub.py doctor
```

See [`skills/delivery-hub/SKILL.md`](skills/delivery-hub/SKILL.md).

## What is in here

```text
skills/
  delivery-hub/       install, check and upgrade a Hub's pinned workflow
  domain-graph/       the continuous Domain lane
  feature-delivery/   request -> Snapshot -> repository loops -> evidence
kernel/               deterministic graph, Snapshot and Evidence integrity
template/             the Hub skeleton `init` writes
migrations/           Hub migrations run by `upgrade`
docs/                 method, authoring contract, decision records
examples/             synthetic artifacts; never installed into a Hub
tests/                behaviour tests for the Hub commands
```

Both hosts read the same bytes: `.claude-plugin/marketplace.json` and
`.agents/plugins/marketplace.json` in the Hub both point at `./.domain-delivery`.

## Design boundaries

- The kernel is integrity machinery. It never decides business meaning.
- Exit codes are a contract: `0` pass, `1` fail, `2` invalid, `3` not
  applicable. `3` is never a pass.
- A Snapshot and its evidence are immutable. Corrections create a new version;
  `upgrade` never rewrites either.
- Rules are either mechanically enforced or explicitly labelled
  `prose-only, unenforced` with a reason.

## Tests

```bash
python3 -B -m unittest discover -s kernel/tests -v
python3 -B -m unittest discover -s skills/feature-delivery/tests -v
python3 -B -m unittest discover -s tests -v
```

Confirmed authorities, L3 nodes and Snapshots in these suites are synthetic
fixtures. A passing suite says nothing about any real Hub's graph maturity.

## Releases

Skills, kernel, schemas, template and docs ship as one atomic SemVer release
([ADR 0004](docs/adr/0004-shared-workflow-separate-domain-graphs.md),
[0008](docs/adr/0008-distribute-shared-workflow-as-pinned-submodule.md)).
Consumers cannot mix component versions. See [`CHANGELOG.md`](CHANGELOG.md).

## Licence

MIT. See [`LICENSE`](LICENSE).
