# Domain Context Map

The canonical {{PROJECT}} Domain Graph begins at
[`docs/domain/INDEX.md`](docs/domain/INDEX.md).

This is the human map: which Bounded Contexts this Hub believes exist, and how
they relate. It is not the generated index and not a node list.

A Delivery Hub is multi-context. Delivery lanes declared in `hub.yaml` — such as
`app`, `web` or `server` — are routing labels, not Bounded Contexts. Create a
`docs/domain/bounded-contexts/<context>/` folder only after several observations
support a real boundary candidate. The folder may exist at `candidate L2` so
domain/PM authority can review it; folder existence does not mean acceptance.

No Bounded Context is confirmed yet in this Hub. Replace this paragraph with the
real map as candidates appear.
