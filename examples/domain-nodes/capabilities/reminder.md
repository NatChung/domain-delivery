---
id: capability:reminder
type: capability
title: Reminder
status: confirmed
readiness: L3
authority: authority:reminder-product
sources: ["ticket:TCK-1"]
scope: ["save a customer's reminder intent", "retrieve it later"]
out_of_scope: ["notification delivery"]
open_questions: []
blocking_questions: []
confirmed_by: reminder-product-owner
confirmed_at: 2026-09-01
confirmation_source: ticket:TCK-1
preconditions: ["the customer is identified"]
postconditions: ["the reminder intent is retrievable by that customer"]
invariants: ["one reminder intent per customer and item"]
invalid_cases: ["an anonymous customer saves a reminder intent"]
related_nodes: ["journey:reminder-digest"]
---

Synthetic example. The business can record that a customer wants to be reminded
about an item, and can read that intent back. Delivering the reminder itself is
a different capability.
