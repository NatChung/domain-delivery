# Domain docs

This repository uses a single context: the shared workflow package. It is not a
Delivery Hub and holds no consumer Domain Graph, Snapshots or evidence.

## Before exploring terminology or decisions

- Read the root `GLOSSARY.md` if present. If absent, continue with the existing
  documentation; create vocabulary only when terms are actually resolved.
- Read relevant decisions in `docs/adr/`.
- Read `docs/workflow.md` for the method's authoritative behavior and
  `docs/domain-graph-schema.md` for the shared graph format.

Use the glossary's vocabulary when available. Surface conflicts with accepted
ADRs explicitly rather than silently overriding them. Unresolved proposals
remain issue candidates until a decision is made.

Keep shared-method terminology and decisions here. Consumer-specific business
rules, terminology and authority stay in their own Hubs. Examples follow the
repository's product-neutrality rules.

These navigation and vocabulary conventions are **prose-only, unenforced**:
semantic reading and ADR conflict detection require agent or human judgment.
