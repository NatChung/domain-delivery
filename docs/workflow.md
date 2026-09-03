# AI Coding Agent Delivery Workflow

Status: Accepted, version 1.0

Reviewed: Nat Chung, 2026-09-03 — section-by-section walkthrough against the
16-part teaching reader; no semantic drift found. This file is the method
source of truth; the reader remains teaching material.

Owner: delivery-method maintainers
Decision record: [ADR 0005](adr/0005-versioned-domain-graph-and-feature-snapshot.md)
Structure record: [ADR 0006](adr/0006-separate-domain-and-delivery-skills.md)
Kernel packaging record: [ADR 0007](adr/0007-move-kernel-into-repo-plugin.md)
Distribution record: [ADR 0008](adr/0008-distribute-shared-workflow-as-pinned-submodule.md)

This is the method source of truth shared by every Delivery Hub that installs
this release. Each Hub owns its own Domain Graph and local adapter; none may
copy and silently fork this method.

The method separates two kinds of change that move at different speeds:

```text
Domain lane:       evidence → graph candidate → human confirmation → graph version
Delivery lane:     request → active slice → frozen snapshot → repo loops → evidence
                                      │
                                      └── pins one graph commit and selected node hashes
```

The Domain Graph keeps learning. A Feature Snapshot does not. That is the
central rule that makes the workflow linear enough to execute without
pretending the domain is static.

## 1. Outcome and problem

The outcome is a repeatable path from a product request to evidence-backed
delivery. Agents may explore, draft, implement and run checks. Humans retain
authority over business meaning, risk acceptance and exceptions.

Brownfield code is evidence, not automatically truth. Product prose is also
evidence, not automatically executable. The workflow makes disagreements
visible before an agent turns one source's accident into a system-wide rule.

## 2. The two-lane lifecycle

The Domain lane is continuous. It records what the organisation currently
believes about journeys, capabilities, Bounded Contexts, language, policies,
contracts and decision authority.

The Delivery lane is feature-scoped. It takes only the confirmed domain nodes
needed for an active slice, freezes them, projects executable contracts, and
runs repository-specific implementation loops.

The lanes meet only at an explicit snapshot. Later Domain Graph edits are
reported as drift; they do not mutate work already in progress.

## 3. Truth, evidence and human authority

Every domain statement has two independent dimensions.

`status` describes semantic authority:

- `candidate`: plausible, not yet accepted by the responsible human;
- `disputed`: credible sources disagree;
- `confirmed`: an identified authority accepted the statement;
- `superseded`: retained for traceability, no longer current.

`readiness` describes how complete the evidence is:

- `L0`: an unshaped observation or question;
- `L1`: named candidate with at least one source;
- `L2`: boundaries, alternatives and open questions have been investigated;
- `L3`: implementation-ready, confirmed and free of blocking ambiguity.

Code, tickets, analytics, documents and interviews are source lanes. They
cannot confirm themselves. A `confirmed` node records `confirmed_by`,
`confirmed_at` and the applicable `authority`. If the owner is unknown, the
node remains `candidate`, even when technical evidence is strong.

## 4. Build a broad Domain Graph v0

Start broad at L1/L2; do not wait for a perfect model. Capture:

- end-to-end Journeys;
- candidate capabilities;
- terms and policies;
- systems/repositories as evidence locations;
- candidate authority and ownership;
- contradictions and unanswered questions.

The graph is Markdown-first because people must be able to review the real
meaning. Generated JSON is an index and validation surface, never the business
source of truth.

Do not infer the domain by scanning every branch. Inspect primary branches and
current operational sources. Historical or abandoned branches are evidence
only when deliberately selected and labelled.

## 5. Journey to capability to Bounded Context

A Journey such as `Saved item → Price alert` is an observation path, not a
Bounded Context. Compare it with other journeys and ask where language, rules,
ownership, invariants and change cadence remain cohesive.

Open or change a Bounded Context candidate only when several observations
support a durable semantic boundary. A service, repository, UI surface or team
is not sufficient evidence by itself.

The usual progression is:

```text
Journey step
  → candidate capability
    → compare across journeys
      → candidate Bounded Context
        → domain/PM review
          → confirmed Bounded Context
```

## 6. Context ownership, contracts and shared concepts

The folder-placement and lazy-creation rules in this section are `prose-only,
unenforced`; the compiler validates node content and references, not directory
policy.

A Bounded Context candidate gets its own folder only after several observations
provide enough evidence to investigate it as a durable semantic boundary. The
folder may therefore exist while the node is still `candidate L2`; folder
existence does not mean that the boundary is confirmed. Do not pre-create an
arbitrary number of empty BC folders. Human confirmation is recorded separately
through the node's `status`, `readiness` and authority metadata.

Cross-context interaction is expressed as a contract owned by the providing or
co-owned boundary. Concepts genuinely shared across contexts live under the
graph's shared-kernel area, with explicit owners and compatibility policy.
“Shared” must not become a miscellaneous folder.

`app`, `web` and `server` are delivery lanes. They help route tickets and repo
loops; they are not Bounded Contexts. One feature snapshot may activate several
delivery lanes and several repositories.

## 7. Markdown source of truth and derived index

The canonical hierarchy is:

```text
docs/domain/                 Markdown-first canonical graph record
  INDEX.md                   graph entry and current maturity
  SCHEMA.md                  authoring contract
  bounded-contexts/          evidence-backed BC candidates, created as needed
  capabilities/              capability nodes
  journeys/                  journey nodes
  contracts/                 cross-context and wire contracts
  shared-kernel/             deliberately shared concepts
  authorities/               who may confirm which statements

domain-index/index.json      deterministic, generated typed index
```

The kernel validates IDs, types, statuses, readiness and confirmation metadata.
It sorts nodes and emits content digests so downstream snapshots can pin exact
meaning. The index may be deleted and regenerated; editing it by hand is an
error.

Code exploration remains per repository. A hub may correlate its findings, but
symbol impact and call paths do not cross repository index boundaries.

## 8. Decision packets and the Domain Gate

Agents should not give a PM or domain expert a pile of raw findings. For each
decision, prepare a compact packet:

- the exact question;
- candidate answer and alternatives;
- evidence for and against;
- affected journeys, contracts and repositories;
- consequence of delaying the decision;
- the named authority who can confirm it.

The Domain Gate passes only when every node selected for delivery is
`confirmed L3`, every required authority is recorded, and no selected rule has
a blocking contradiction. The rest of the graph may remain candidate or L2.
This is the active-slice principle: delivery does not wait for the whole domain
to be complete.

## 9. Active slice and immutable Feature Snapshot

After the Domain Gate, freeze a Feature Snapshot before deriving BDD or code.
The snapshot contains:

- feature identifier and snapshot version;
- Domain Graph commit, source root and generated index digest;
- selected node IDs and content digests;
- accepted scope, invariants, preconditions, postconditions and invalid cases;
- required delivery lanes and wire contracts;
- required evidence/check IDs.

Preconditions, postconditions and invariants belong in the reviewed Markdown
domain or feature material. The manifest references and hashes them; JSON does
not replace their explanation.

Snapshots are immutable. When the graph changes, the agent reports drift but
continues against the pinned snapshot unless a human classifies the correction
as requiring a rebaseline. A replacement is a new version (`v2`) that
supersedes `v1`; no process edits `v1` in place.

## 10. Scrum, Definition of Ready and change classification

Separate PO/PM shaping from agent execution before creating an executable
Sprint Backlog:

```text
Product Backlog
  → active-slice discovery and decisions
    → Domain Gate
      → frozen Feature Snapshot
        → executable Sprint Backlog
          → repository Agent Loops
```

The snapshot is the semantic Definition of Ready for agent work. Team capacity,
dependencies and release readiness remain normal Scrum concerns.

When something changes, classify it explicitly:

| Situation | Treatment |
|---|---|
| Wrong detail found before implementation | Same feature; create snapshot v2 |
| Wrong contract found during implementation | Stop affected loops; rebaseline to v2 |
| Additional capability requested | New feature/change request |
| Released code violates a valid snapshot | Bug fix |
| Released behaviour follows a snapshot later found wrong | Corrective change; hotfix only if risk demands |
| New business rule after release | New feature/change request |

This is primarily a management distinction: it preserves why work exists,
which acceptance basis applies, and whether prior implementation was defective.

## 11. Contract stack after the snapshot

Project executable checks from the frozen snapshot, in this order:

1. BDD examples for observable behaviour;
2. Design-by-Contract checks for preconditions, postconditions, invariants and
   invalid cases;
3. wire/schema contracts between delivery lanes or contexts;
4. architecture contracts for dependency direction and ownership;
5. repository-native quality checks.

BDD is a projection of the snapshot, not an input used to decide the snapshot.
The snapshot may require a named check without prescribing Java, Flutter,
TypeScript or a particular framework.

## 12. Repository Agent Loops and brownfield ratchets

Each affected repository runs its own loop against the same snapshot:

```text
select next contract → red test → minimal change → green → refactor
  → architecture/static checks → record evidence → fresh review
```

The repository's own `AGENTS.md`/`CLAUDE.md`/README defines commands and local
standards. The shared kernel binds results; it does not generate one language's
test layout for every team.

Brownfield architecture violations are fingerprinted as a baseline. The gate
allows known debt, rejects new violations, and ratchets the baseline downward
when debt is removed. Known debt is not silently “passed”; it is a visible
exception with owner and scope.

Behaviour that contradicts the active confirmed snapshot cannot be
grandfathered as brownfield debt. It fails or forces a human rebaseline.

## 13. Evidence, feedback and rollout

Evidence entries are appended through the kernel and hash-chained. They bind:

- snapshot digest;
- repository-scoped check ID and checker file digest;
- repository commit and dirty-state digest;
- output/artifact digest;
- exit code and timestamp;
- one result performer declaration;
- a separate trusted attestation declaration and artifact digest;
- previous entry hash.

Exit code `0` means pass, `1` fail, `2` invalid evidence/input and `3` not
applicable. Required checks pass only with `0`; historical success, missing
checks and N/A do not satisfy the gate. The kernel enforces separation and
integrity, while the surrounding CI or local adapter is responsible for
authenticating the declared actor; a string identity alone is not presented as
cryptographic proof. A local ledger is tamper-evident only when its terminal
hash is retained or signed by an external trusted system.

Feedback updates the Domain Graph through the Domain lane. It never rewrites a
snapshot or evidence ledger. A completed run can therefore always answer:
“Which domain version did we implement, what changed, and what proved it?”

Roll out in thin slices:

1. establish Graph v0 and authorities;
2. choose one PM-approved pilot, thin enough to start from a single
   confirmed rule;
3. freeze one snapshot;
4. run native repository loops and evidence binding;
5. review false positives, missing contracts and decision latency;
6. refine the method without changing completed artifacts.

## Artifact authority

| Artifact | Authority | Mutable? |
|---|---|---|
| this repository's `docs/workflow.md` | shared method | versioned edits |
| Hub `docs/domain/**` | that Hub's domain meaning | yes, with status/history |
| `domain-index/index.json` | generated validation/index | regenerate only |
| `specs/<feature>/snapshot/**` | feature execution basis | no; supersede |
| product-repo tests/contracts | executable projection | yes, against snapshot |
| `evidence/<feature>/<run>/` | bound run declarations/evidence | kernel-appended; externally anchor terminal hash |
| tickets/backlogs | work coordination | yes; not domain truth |

## Implementation status

Version 1.0 defines the complete contract. Per-Hub maturity is deliberately not
tracked here: each Hub records its live state in its own current-state
authority, normally `docs/domain/INDEX.md`, reached through the Hub adapter. A
Hub's adapter must explicitly map to this lifecycle before claiming
conformance.
