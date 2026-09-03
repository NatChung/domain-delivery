# ADR 0005: Use a versioned Domain Graph and immutable Feature Snapshots

## Status

Accepted (2026-09-01)

## Context

The original harness encoded five fixed acts, interview rounds and
language-specific acceptance/architecture generation. It mixed method,
business discovery and execution mechanics. A changing Domain Graph also made a
strictly linear feature flow appear impossible: later domain edits could change
the meaning of work already under implementation.

App, web and server were also labelled Bounded Contexts even though they are
delivery surfaces. Code-derived candidates could appear authoritative before a
PM or domain expert confirmed them.

## Decision

Use two connected lifecycles:

1. a continuously versioned, Markdown-first Domain Graph;
2. a feature-scoped Delivery lane based on an immutable Feature Snapshot.

The snapshot pins a graph commit/index digest and selected confirmed L3 node
digests. Later graph changes produce drift, not snapshot mutation. Corrections
create a superseding snapshot version.

Markdown contains the reviewed meaning, including preconditions,
postconditions, invariants and invalid cases. A deterministic JSON index and
manifest exist for validation and machine traversal only.

`app`, `web` and `server` are delivery lanes, not Bounded Contexts. Repository
loops use native TDD, contract and architecture checks. The central harness is
a repository-neutral kernel for graph compilation, snapshot verification and
evidence binding.

The vendored five-act harness is removed from the active tree and retained in
Git history with a migration record.

## Consequences

- Domain discovery can continue without destabilising in-flight delivery.
- Only an active confirmed slice must reach L3 before implementation.
- Agents cannot promote code-derived evidence into confirmed business truth.
- BDD and technical contracts are projected after the snapshot.
- Existing architecture debt may use a not-worse ratchet; behaviour that
  contradicts the snapshot cannot be exempted.
- Completed work remains reproducible from pinned meaning and bound evidence.
