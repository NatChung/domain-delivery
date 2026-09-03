# Domain node authoring contract

This is the shared authoring contract. A Delivery Hub's `docs/domain/SCHEMA.md`
points here instead of keeping a copy that can silently fork.

Each semantic node is Markdown with flat, JSON-compatible front matter. The
body contains the explanation that people review; the generated index adds
`source_path`, `body` and `content_digest`.

```markdown
---
id: capability:reminder
type: capability
title: Reminder
status: candidate
readiness: L2
authority: unknown
sources: ["code:reminder-service/main", "map:service-routing"]
scope: ["save and retrieve customer reminder intent"]
out_of_scope: ["notification delivery"]
open_questions: ["is identity item or variant level?", "who confirms this?"]
related_nodes: ["journey:reminder-digest"]
---

Human-readable meaning, evidence, alternatives and unresolved decisions.
```

## Vocabulary

Allowed `type` values are `authority`, `bounded_context`, `capability`,
`contract`, `journey`, `policy`, `question` and `term`.

Allowed `status` values are:

- `candidate`: plausible but not accepted by the responsible authority;
- `disputed`: credible sources disagree;
- `confirmed`: an identified authority accepted the meaning;
- `superseded`: historical and no longer current.

Readiness is independent of status:

- `L0`: observation or question;
- `L1`: requires at least one `sources` entry;
- `L2`: shaped node types also require non-empty `scope` plus explicit
  `out_of_scope` and `open_questions` lists; either list may be empty;
- `L3`: requires `confirmed`, an explicit empty `blocking_questions` list and,
  for executable node types, non-empty `preconditions`, `postconditions`,
  `invariants` and `invalid_cases`.

`preconditions`, `postconditions`, `invariants` and `invalid_cases` live here,
not only in generated JSON. They become executable projections only after a
snapshot freezes them.

The executable node types are `bounded_context`, `capability`, `contract`,
`journey` and `policy`. At L3, each of these types must carry all four rule
lists above. `authority`, `question` and `term` nodes may reach L3 without those
executable rule lists.

## Confirmation and authority

A confirmed non-authority node must contain:

```yaml
confirmed_by: reminder-product-owner
confirmed_at: 2026-09-01
confirmation_source: ticket:TCK-123
authority: authority:reminder-product
```

The referenced authority must itself be a `confirmed L3` `authority` node and
its `scope` must cover the confirmed node ID. `confirmed_by` must name a human
or accountable role; agents cannot confirm semantic truth. When the owner is
unknown, keep `status: candidate` and `authority: unknown`.

## Relationships

- `requires` is a typed dependency. Snapshot closure includes it and it must be
  `confirmed L3` before freezing.
- `related_nodes` is navigation or comparison evidence. It must resolve, but it
  is not automatically pulled into the snapshot.

Use `requires` only when the selected rule cannot be interpreted or executed
without the referenced node. This prevents an interesting link from silently
expanding the active slice.

The compiler rejects unknown fields and dangling references. The equivalent
machine-readable node contract is
[`../kernel/schema/domain-node.schema.json`](../kernel/schema/domain-node.schema.json).

## File placement

Enforcement: `prose-only, unenforced`. The compiler validates node content and
references but recursively accepts Markdown nodes from any nested directory;
it does not enforce folder/type placement or lazy folder creation.

Journey and capability nodes may be captured broadly before a Bounded Context
boundary is clear. Once several observations provide enough evidence for a real
boundary candidate, create its folder as:

```text
bounded-contexts/<context>/
  INDEX.md                  bounded_context node
  terms/                    context-specific term nodes, when they exist
  policies/                 context-specific policy nodes, when they exist
  questions/                unresolved boundary questions, when they exist
```

Create only files with substantive evidence or questions; do not add empty
folders or `.gitkeep` placeholders. A folder may start at `candidate L2` and
does not imply confirmation. Confirmation still requires the metadata and
authority described above.
