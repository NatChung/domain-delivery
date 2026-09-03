# ADR 0004: Share the workflow, keep Domain Graphs separate

## Status

Accepted (2026-09-01)

## Context

Several independent products need the same delivery vocabulary, but their
business language, authorities, evidence and release constraints are different.
Copying the method into every Hub would create silent forks. Combining domain
knowledge would create false cross-client authority and privacy risk.

## Decision

[`../workflow.md`](../workflow.md) in this repository is the versioned shared
method source of truth.

Each Delivery Hub owns its own:

- Markdown Domain Graph and generated index;
- authority records and decision packets;
- Feature Snapshots and evidence;
- local repository-loop adapter and operational constraints.

Sibling Hubs link to a named workflow version; they do not copy the method. No
Hub may treat another Hub's Domain Graph as its business authority.

## Consequences

Method fixes happen once. Domain information remains isolated. Each Hub needs a
thin session-start adapter that states its current maturity, local source of
truth and next approved pilot.
