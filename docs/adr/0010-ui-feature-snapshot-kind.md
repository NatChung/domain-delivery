# UI Feature Snapshot kind

Status: Proposed

A pure presentation request needs an immutable execution basis without inventing
Domain Graph nodes. Add `kind: ui` with manifest `schema_version: 2`. Missing
`kind` in schema v1 continues to mean `domain`; explicit `kind: domain` is also
accepted in v1. Default domain freeze produces the same bytes and keeps the
capability/journey root, committed Graph reconstruction and confirmed L3 closure.

## Accepted request and scope

UI freezes the verbatim request and each verbatim AC, with SHA-256 over the exact
UTF-8 text (no trimming or newline normalization). ACs have stable unique `ac:`
IDs. `accepted_by` must be a named `human:` identity, `accepted_at` a timezone-aware
ISO datetime, and `source` a non-empty provenance locator. The acceptance covers
both text and classification, not domain confirmation. The canonical payload
contains all these fields and is bound by payload, bundle and manifest digests.

Scope contains a category (`ui`, `copy`, `style`, `explicit_bug`), rationale,
and explicit false flags for `business_rules`, `cross_system`, `data_changes`,
and `permission_changes`. Any true/missing/non-boolean exclusion, unknown field,
non-empty domain nodes/roots or Graph input is rejected. A bug is eligible only
when its already accepted behaviour is explicit and it introduces none of those
excluded changes. A business-rule bug or uncertain intent uses domain kind.
Delivery lanes, repository coverage, required checks, trusted attestors,
atomic immutable publication and evidence requirements are identical to domain.

## Graph pin and anti-bypass defence

UI has no Graph pin: it selects no Graph meaning, and requiring a Graph commit
would imply authority that it neither checks nor uses. Graph inputs are rejected,
not silently ignored. `UI.md` and `ui-payload.json` replace the domain bundle;
`verify-snapshot` checks exact payload and deterministic rendering without a Git
Graph repository. Graph drift is explicitly inapplicable. Request corrections
create a superseding version; none of the frozen artifacts may be edited.

Machine checks establish structural exclusions, named human declarations and
content integrity. They cannot authenticate a human or infer the truth of scope
classification from arbitrary prose. Human review of the entire request, every
AC, rationale and exclusion before acceptance is **prose-only, unenforced**:
no local parser can reliably decide business meaning or authenticate the cited
source. The reviewer must send ambiguity, pricing/eligibility logic, new data,
permission changes or cross-system behaviour to domain, even if labelled UI.
Step 05/07 discovery of such scope stops affected delivery and requires a new
domain Snapshot; adding domain rules to UI checks is not an escape hatch.

Hashes detect corruption relative to a trusted snapshot digest, not malicious
replacement of every artifact and digest. Provenance authentication and external
anchoring remain external/human, as for domain evidence. A human-looking identity
alone does not prove a human accepted the request.

## AC projection and compatibility

UI Step 05 uses `check-projection/v0.2`, with `snapshot_rule_refs` entries
`{node_id: "ac:<id>", field: "acceptance_criteria", statement: <exact AC text>}`.
These references are AC identifiers, not Graph nodes. Every AC and every declared
repository/check pair must be covered for readiness. Native repository quality
references cannot replace AC coverage. Domain continues to use v0.1 and the same
whole-node rule coverage. Step 06 routing and Step 08 attestation are unchanged.

Recommend one atomic package release 0.5.0 after review; no tag is created by this
proposal. See `migrations/ui-snapshot-kind.md`: upgrade the package/lock together,
teach adapters kind-specific inputs/bundles and projection v0.2, and leave all
existing snapshots, projections and evidence byte-for-byte unchanged. No Hub
file rewrite is required, so this additive contract needs a manual adapter
migration guide rather than a script that rewrites frozen artifacts. Older
packages reject v2 UI snapshots; do not hand them to a v0.4.0 consumer.

Open upstream acceptance: maintainers must accept this Proposed ADR, scope policy,
wire format and the eventual atomic release. This implementation does not record
that approval or publish a release.
