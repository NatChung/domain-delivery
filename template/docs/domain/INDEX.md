# {{PROJECT}} Domain Graph

This file is the single current-state record for this Hub's Domain Graph: what
exists, how mature it is, and what has been confirmed. Other documents link
here; none of them restate it.

Read [`../../CONTEXT-MAP.md`](../../CONTEXT-MAP.md) first for the human map,
then this file, then the individual node files.

## Authoring

Node front matter and the confirmation contract live upstream in
[`SCHEMA.md`](SCHEMA.md), which points at the pinned shared contract. Folder
roles are described in [`README.md`](README.md).

## Maturity

Nothing has been discovered yet. This Hub has no nodes, no authorities and no
confirmed meaning.

Record here, and only here:

| Node type | Count | Highest readiness | Confirmed |
|---|---|---|---|
| journey | 0 | — | 0 |
| capability | 0 | — | 0 |
| bounded_context | 0 | — | 0 |
| contract | 0 | — | 0 |
| policy | 0 | — | 0 |
| term | 0 | — | 0 |
| question | 0 | — | 0 |
| authority | 0 | — | 0 |

## Generated index

`domain-index/index.json` is compiled from this folder by the pinned kernel. It
is a validation and traversal surface, never the business source of truth.
Regenerate it; never hand-edit it.

```bash
python3 -B .domain-delivery/kernel/scripts/kernel.py compile \
  --source docs/domain --output domain-index/index.json

python3 -B .domain-delivery/kernel/scripts/kernel.py gate-index \
  --index domain-index/index.json
```
