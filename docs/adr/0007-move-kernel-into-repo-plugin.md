# Move the shared kernel into a packaged plugin

Status: Accepted (2026-09-02)

Move the repository-neutral Graph, Snapshot and Evidence kernel out of an
ad-hoc directory inside the first Hub and into a packaged plugin. The plugin
owns one Python module interface, one stable CLI adapter, schemas, tests and
migration history; the `domain-graph` and `feature-delivery` Skills remain
separate lifecycle adapters that depend on it. This supersedes only ADR 0006's
timing decision to wait for a second Hub before extraction: the two lifecycle
adapters already provide two real callers at the seam, and plugin packaging
makes shared ownership explicit without duplicating implementation.

At acceptance the plugin was still consumed directly from the first Hub with no
marketplace entry;
[ADR 0008](0008-distribute-shared-workflow-as-pinned-submodule.md) later moved
it into this shared repository at `kernel/` and made every Hub a consumer. The
kernel remains deterministic integrity machinery, not a Domain Graph, lifecycle
Skill or semantic authority. An old directory may be removed only after every
active CLI/import caller uses the packaged kernel and both kernel and Skill
test suites pass.
