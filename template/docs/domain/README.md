# Domain Graph folder roles

Markdown here is the canonical record. Each file is one typed semantic node with
front matter plus a human explanation; see [`SCHEMA.md`](SCHEMA.md).

| Folder | Holds |
|---|---|
| `journeys/` | end-to-end observation paths through the business |
| `capabilities/` | what the business can do, independent of any service |
| `bounded-contexts/` | evidence-backed boundary candidates, created lazily |
| `contracts/` | cross-context and wire contracts, owned by a provider |
| `policies/` | rules that decide outcomes |
| `terms/` | ubiquitous language entries |
| `questions/` | unresolved semantic questions, with who must answer |
| `authorities/` | who may confirm which statements |
| `shared-kernel/` | concepts deliberately shared across contexts |

## Reading route

1. [`../../CONTEXT-MAP.md`](../../CONTEXT-MAP.md) — the human map.
2. [`INDEX.md`](INDEX.md) — current maturity and what is confirmed.
3. The node files themselves, following `requires` and `related_nodes`.
4. `domain-index/index.json` — generated; for machines and gates only.

There is no `INDEX.md` inside each typed folder. Typed relations plus the
compiler already carry the structure; per-folder indexes would duplicate it and
drift.

## Creating nodes

Write a node only when there is real evidence or a real question behind it.
Start broad at L1/L2 in `journeys/` and `capabilities/`; open a
`bounded-contexts/<context>/` folder only once several observations support a
durable boundary. Do not pre-create empty folders or `.gitkeep` placeholders,
and do not seed the graph with examples — synthetic nodes belong in the shared
workflow's `examples/`, never in a real Hub.
