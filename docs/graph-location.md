# Graph repository adapter

A Hub may keep its canonical Graph in the Hub or in one explicit external Git
repository. The Graph repository is not another Delivery Hub: it needs no Hub
initialisation, product clones, Snapshots or evidence directories. Validate its
Markdown with the pinned shared kernel `compile` and `gate-index` commands.

## Resolve paths before lifecycle work

Read the optional routing declaration in the Hub's `hub.yaml`:

```yaml
graph:
  repository: ../domain-graph
  source: docs/domain
  index: domain-index/index.json
authority:
  registry: ../domain-graph/docs/domain/authorities
```

`graph.repository` is an explicit local checkout path, relative to the Hub root
(or absolute for a local adapter). `graph.source` and `graph.index` are paths
relative to that checkout. `authority.registry` retains its existing Hub-relative
meaning; update it explicitly when moving authority nodes. No remote identity,
access permission or automatic clone is inferred from these paths.

When `graph` is absent, use the Hub root, `docs/domain` and
`domain-index/index.json`. An explicit `graph` declaration must supply all three
fields; stop on a missing checkout, field or source instead of falling back to
Hub content. Resolve Graph paths before reading its INDEX/SCHEMA/nodes,
compiling an index, choosing a commit, freezing or routing feedback.

Config interpretation and argument forwarding are `prose-only, unenforced`:
`hub.yaml` has no runtime schema/parser; the host or Hub adapter performs this
mapping. The CLI validates the supplied paths/content, not their agreement with
YAML. Existing command examples in lifecycle references use the default layout;
substitute these resolved paths when the optional declaration is present.

## Forward the resolved paths

- Domain discovery, confirmation, compilation and feedback operate on the Graph
  checkout. Its Markdown remains the single canonical record. Commit Graph
  changes and regenerated index together in that repository.
- `freeze` reads the resolved index and receives `--graph-repo <checkout>` and
  the full Graph commit SHA. Snapshot output remains in the Hub.
- Kernel `verify-snapshot`, `drift`, `record-result`, `declare-attestation` and
  `verify-evidence` receive the same `--graph-repo <checkout>`.
- Feature `validate_delivery_plan.py` receives `--graph-repo <checkout>` for both
  projection and task-plan gates. Product repository paths remain Hub-relative.
- Hub `doctor` receives `--graph-repo <checkout> --graph-source <source>`.
  It checks installation plus the selected Graph entry; it does not compile or
  semantically confirm the Graph. Run it from the Hub, not the Graph repository.

Kernel and planning CLI relative paths are relative to the process working
directory; resolve the config to absolute paths or run from the Hub root.
`doctor` resolves its `--graph-repo` relative to `--hub`.

## Historical Snapshots and migration

A frozen Snapshot retains its original commit, source root and index digest.
When verifying a Snapshot made before extraction, explicitly select the original
Hub checkout containing that commit. For post-extraction Snapshots, select the
external Graph checkout. Keep the selection in the run's adapter invocation;
never rewrite old Snapshot/evidence bytes or silently retry another repository.
The kernel rejects a checkout without the pinned commit or matching content;
[the kernel contract](../kernel/README.md#separate-graph-repository) explains the
binding and its limits.

This capability changes no required Hub file shape and has no automatic
migration. Existing Hubs retain their current layout. An opt-in extraction must
update local routing, authority paths and consumers in its own reviewed change,
and preserve historical commit availability. It requires neither a submodule
nor a second publication copy of the canonical Graph.
