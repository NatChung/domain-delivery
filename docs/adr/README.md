# Method decision records

These are the shared-method decisions carried by this repository. They are
versioned with the release; a Delivery Hub links to them instead of copying
them, and records its own Hub-specific decisions in its own `docs/adr/`.

| ADR | Decision |
|---|---|
| [0004](0004-shared-workflow-separate-domain-graphs.md) | Share the workflow, keep Domain Graphs separate |
| [0005](0005-versioned-domain-graph-and-feature-snapshot.md) | Versioned Domain Graph, immutable Feature Snapshots |
| [0006](0006-separate-domain-and-delivery-skills.md) | Separate Domain and Delivery Skills over one kernel |
| [0007](0007-move-kernel-into-repo-plugin.md) | Move the kernel into a packaged plugin |
| [0008](0008-distribute-shared-workflow-as-pinned-submodule.md) | Distribute as a pinned Git submodule |
| [0009](0009-public-shared-workflow-repo-with-fresh-history.md) | Publish from a personal account with fresh history |

Numbering starts at 0004 because 0001–0003 are Hub-specific decisions that
stayed behind in the first consumer Hub.
