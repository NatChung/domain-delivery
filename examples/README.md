# Examples

Everything here is synthetic. It exists to show the shape of an artifact, and to
give the test suite something to compile. It is never copied into a real
Delivery Hub — `init` deliberately installs no domain nodes, because a Hub's
graph must contain only what its own evidence supports.

- [`domain-nodes/`](domain-nodes/) — a minimal graph that compiles and passes
  `gate-index`: one authority, one capability it covers, and one journey.
