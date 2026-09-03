# Five-act v0 retirement and plugin-kernel continuity

The vendored five-act harness was removed from the active tree on 2026-09-01.
It encoded a fixed act sequence, interview rounds and Java-specific ArchUnit /
PIT mechanics that conflict with the repository-neutral workflow.

The old files remain recoverable from Git history. Their source was:

- repository: `https://github.com/NatChung/ddd-harness.git`
- source commit: `9a08233fefa2482ab54cf73274bcbda7e2f04304`
- vendored on: 2026-08-26
- test result recorded at vendoring: 354 passed, 2 skipped
- final local baseline before retirement: 387 passed, 1 skipped

Semantics carried forward into the new kernel are deterministic output,
provenance, typed references, kernel-appended hash-chain evidence, separation
of producer and attestor declarations, and the rule that “not applicable” is
not “pass”. Language-specific
architecture and test commands now belong to each product repository's loop.
