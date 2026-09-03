# Publish the shared workflow from a personal account with fresh history

Status: Accepted (2026-09-03)

This repository lives under the maintainer's personal GitHub account,
`NatChung`, not under any client organisation, and is intended to become
public. It starts private; it is switched to public only after the first tagged
release passes a three-surface identifier audit — working tree, every commit
message, every revision's content — that finds zero consumer content. The
repository is created with a fresh Git history by copying files out of the
first consumer Hub, not by filtering that Hub's history, so the audit has one
small history to check and nothing to rewrite.

Consequences:

- Each Hub keeps its own Domain Graph, specs, maps, evidence and Hub-specific
  ADRs. Method docs and method ADRs (0004–0009) live here after sanitisation;
  a Hub links to them instead of keeping copies.
- The plugin manifests' author and contact fields name the maintainer, never a
  client organisation.
- While the repository is private, only the owner can fetch the submodule.
  Switching to public must happen before any teammate works in a Hub.
- The audit term list is owned by the consumer Hub that donated the content,
  not by this repository: shipping the list would put the very identifiers it
  protects into the public tree.
