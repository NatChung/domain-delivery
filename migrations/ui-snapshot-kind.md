# UI snapshot kind: proposed 0.4.0 → 0.5.0 adapter migration

This is an additive, manual adapter migration, not an executable Hub migration.
No existing Hub-owned file is required to change. Do not rewrite any frozen
snapshot, projection or evidence, including adding an explicit domain kind.

1. After upstream release approval, upgrade the complete package, submodule pin
   and workflow lock together. No component-only install is supported.
2. Adapters must dispatch on `kind` (missing means domain). Reject unsupported
   kinds/versions. Domain continues using schema v1 and the Graph inputs.
3. UI intake must collect exact request/AC UTF-8 text and text digests, unique
   `ac:` IDs, `human:` acceptance identity/time/source and accepted scope flags.
   Record the human review of classification. UI is not domain confirmation.
4. Freeze UI with `--kind ui --accepted-request <JSON>`, no Graph flags. Pass
   lanes, repositories, checks and attestors as before. Verify with the upgraded
   kernel; retain its digest as the immutable downstream binding.
5. Bundle readers/transport adapters must select UI.md/ui-payload.json for UI,
   DOMAIN.md/domain-payload.json for domain. Do not assume nodes are non-empty.
6. UI projection uses check-projection/v0.2 and exact AC references/coverage;
   domain v0.1 artifacts retain their original rule semantics. Step 06 packets
   and Step 08 results/attestations still bind the manifest digest unchanged.
7. Request drift uses a new accepted request and superseding snapshot, not Graph
   drift. If excluded scope is discovered, stop and rebaseline to domain kind.

Migration execution and adapter policy review are **prose-only, unenforced**:
consumer adapters are outside this package. This guide does not change them.
