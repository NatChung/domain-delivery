# {{PROJECT}} — session start

This is the Hub adapter to the pinned shared workflow. It is an entry point, not
the method and not the Domain Graph. It carries the reading guide: which
documents are canonical, which are reference-only, and which must not be read
wholesale.

One-line rule: **method lives in
[`../.domain-delivery/docs/workflow.md`](../.domain-delivery/docs/workflow.md),
current state lives in [`domain/INDEX.md`](domain/INDEX.md), operations live in
the Skills; generated JSON is regenerate-only, and product clones are not
browsed unless product evidence is explicitly required.**

Enforcement note: the reading and operating rules here are
`prose-only, unenforced` — they need task-scope judgement no checker can make.

## Tier 1 — always read, in order

1. [`../AGENTS.md`](../AGENTS.md) — execution constraints.
2. This file — Hub adapter and reading guide.
3. [`../workflow.lock`](../workflow.lock) — which shared version is installed.
4. [`../.domain-delivery/docs/workflow.md`](../.domain-delivery/docs/workflow.md)
   — the method source of truth.
5. [`../CONTEXT-MAP.md`](../CONTEXT-MAP.md) and
   [`domain/INDEX.md`](domain/INDEX.md) — the only current-state record.

## Tier 2 — read per task

- Domain lane work → the `domain-graph` Skill plus the one reference the task
  needs.
- Delivery lane work → the `feature-delivery` Skill. The lane split comes from
  the frozen snapshot, not from a guess.
- Authoring nodes → [`domain/SCHEMA.md`](domain/SCHEMA.md).
- Method decisions →
  [`../.domain-delivery/docs/adr/README.md`](../.domain-delivery/docs/adr/README.md).
  Hub decisions → [`adr/README.md`](adr/README.md).
- Before touching a product repo → that repository's own agent guides.

## Tier 3 — reference only

Evidence and management material this Hub accumulates: maps, research, archives,
plans. Pull the section you need; never load wholesale.

## Tier 4 — do not read or edit

- `domain-index/index.json` — generated; regenerate only.
- `.domain-delivery/**` — pinned upstream; changes go upstream and arrive
  through `upgrade`.

## Current maturity

Live maturity, node counts and confirmation state are recorded once, in
[`domain/INDEX.md`](domain/INDEX.md). Do not restate them here or elsewhere.

## Safe next work

An agent may gather primary-branch evidence, compare journeys, draft candidate
nodes, prepare decision packets, compile the graph and report drift. It may not
self-confirm domain nodes, freeze a candidate into a snapshot, create product
tickets without the documented routing decision, or change product code before a
valid snapshot exists.
