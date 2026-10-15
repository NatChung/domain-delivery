# Triage labels

| Canonical role | Tracker label | Meaning |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | Awaiting maintainer evaluation and scope confirmation |
| `needs-info` | `needs-info` | Missing evidence or a decision needed to proceed |
| `ready-for-agent` | `ready-for-agent` | Scope, allowed actions and acceptance criteria are confirmed for agent execution |
| `ready-for-human` | `ready-for-human` | Requires human execution or a human decision |
| `wontfix` | `wontfix` | Will not be actioned; record the reason |

When a skill names a canonical role, use the corresponding tracker label.
Apply `needs-triage` to new requests and update labels as the request changes.
A label does not authorize an external action or automatically dispatch work.

This workflow is **prose-only, unenforced**: labels are maintained through the
tracker, with no automatic transition or dispatch enforcement in this package.
