# Migrations

One directory per migration, named `<sequence>-<slug>` so that name order is
execution order. Each directory contains `migrate.py` exporting:

```python
def migrate(hub_root):
    """Change Hub-owned files in place. Return a list of human-readable notes."""
    return []
```

Rules:

- A migration may change template-generated Hub files, Hub configuration and
  Hub-owned documentation.
- A migration must never rewrite `specs/**` or `evidence/**`. Frozen Snapshots
  and bound evidence stay exactly as recorded; that is what makes a completed
  run reproducible.
- A migration must be idempotent in effect: `upgrade` records applied names in
  `workflow.lock` and never runs one twice, but a re-run after a manual revert
  must still be safe.
- `init` records every migration that exists at install time as already
  applied. A new Hub has nothing to migrate.

There are no migrations in the 0.1.0 release. The mechanism ships so that the
first real one needs no new machinery.
