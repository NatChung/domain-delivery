# Separate Domain Graph and Feature Delivery skills over one shared kernel

Status: Accepted (2026-09-02)

Kernel-location note: the decision to keep the implementation in a directory
inside the first Hub until a second Hub existed is superseded by
[ADR 0007](0007-move-kernel-into-repo-plugin.md) and then by
[ADR 0008](0008-distribute-shared-workflow-as-pinned-submodule.md). The
two-lifecycle ownership and `bounded-contexts/` decisions remain accepted.

The workflow exposes the two lifecycle lanes as separate Skills: `domain-graph`
owns Domain Graph discovery, candidate shaping, authority decision packets,
recording traceable human confirmation and graph publication;
`feature-delivery` owns request-to-evidence delivery but may freeze only a
confirmed L3 graph slice. Both call the same repository-neutral kernel
interface for deterministic graph, Snapshot and Evidence integrity. Later ADRs
moved that interface's package location without changing the
one-implementation rule.

Canonical Domain Graph storage uses the explicit context-first path
`docs/domain/bounded-contexts/<context>/`. A folder is created only when
evidence supports a real candidate boundary; candidate folders are allowed and
remain non-authoritative until a named authority confirms their node.
Cross-context discovery remains in top-level journeys and capabilities, while
cross-context contracts and deliberately shared concepts remain at their
graph-level paths. Folder placement and lazy creation are `prose-only,
unenforced`; the compiler validates node content and references, not directory
policy.

## Considered alternatives

- Putting the kernel inside `feature-delivery` would make a delivery adapter own repository-neutral integrity rules and hide Domain-lane commands behind the wrong Skill.
- Giving each Skill its own kernel copy would create silent contract forks.
- Keeping the ambiguous `contexts/` name would continue colliding with execution context and delivery-lane language; pre-creating empty Bounded Context folders would make guesses look established.

## Consequences

- Domain Graph work and Feature Delivery have distinct invocation pointers and completion criteria.
- The shared kernel module is not a second Graph or an authority over business meaning; later ADRs change only its package location.
- Hub-specific numbered-artifact validators remain under the owning Skill's
  `scripts/`; they are adapter contracts, not a second kernel. The Domain Skill
  adds no local script while shared `compile` and `gate-index` are sufficient.
- Superseded timing consequence: the original plan waited for a second Hub before extraction; ADR 0007 recognises the two lifecycle Skills as real callers and moves earlier.
- The compiler continues to discover nested Markdown nodes recursively; directory layout improves human navigation without changing node IDs or semantic status.
