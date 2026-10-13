# Rename the delivery Skill to delivery-workflow

Target: planned 0.6.0. This is a breaking path and invocation rename from 0.5.0,
not a change to Steps 01–08, the kernel or artifact contracts. The source branch
still has VERSION 0.5.0; it is not a tagged 0.6.0 release.

`skills/delivery-workflow/` is the only delivery Skill directory. There is no
`skills/feature-delivery/` compatibility directory, symlink or script redirect.
An adapter using the old path will fail after updating the package pin. Keep
consumers on v0.5.0 until their path changes are ready in the same upgrade.

## Manual consumer upgrade

This guide is documentation only. `hub.py upgrade` does not apply this checklist
or rewrite custom adapters; a healthy doctor alone does not prove their paths
have been migrated. The manual review requirement is `prose-only, unenforced`
because the shared package cannot identify every consumer-owned adapter.

1. Inventory current references in tracked files, hidden host configuration,
   local scripts and CI commands. Classify frozen artifacts and historical
   records separately; preserve their original bytes, paths and provenance.
2. Update current pointers using these mappings (the `.domain-delivery/` prefix
   stays unchanged):

   | Old reference | New reference |
   |---|---|
   | `skills/feature-delivery/SKILL.md` | `skills/delivery-workflow/SKILL.md` |
   | `skills/feature-delivery/references/<file>` | `skills/delivery-workflow/references/<file>` |
   | `skills/feature-delivery/scripts/<file>` | `skills/delivery-workflow/scripts/<file>` |
   | `skills/feature-delivery/tests/<file>` | `skills/delivery-workflow/tests/<file>` |
   | `$feature-delivery` or lifecycle `feature-delivery` | `$delivery-workflow` or lifecycle `delivery-workflow` |

   This includes imports, subprocess commands, schema loading, fixture loaders,
   test-copy paths, workspace preflight lists, path-reference policies and
   `doctor --skill-source` arguments. The old lifecycle is no longer accepted
   by doctor; it returns invalid input (exit 2), rather than a deprecation warning.
3. Reconcile Hub-owned `AGENTS.md`, `CLAUDE.md`, `docs/skill-entry.md`,
   `docs/session-start.md`, workflow guides and live links with the new templates.
   Preserve local scope and authority rules. Existing Hubs that already applied
   `001-pinned-skill-entry` do not receive a refreshed entry from that migration.
4. The plugin remains named `domain-delivery`, and both plugin manifests still
   discover `./skills/`. Marketplace package paths and kernel paths need no
   rename. Update any consumer-specific explicit Skill lists or cached entry
   pointers; refresh host caches to the same pinned release and source bytes.
5. Once a release exists, update the submodule pin and use the normal Hub upgrade
   procedure to record its tag, full commit and package digest in `workflow.lock`.
   Do not merely relabel a 0.5.0 lock as 0.6.0. Release selection and local adapter
   edits belong in one reviewed consumer change.
6. Run consumer adapter tests, workspace/path checks and the pinned doctor:

   ```bash
   python3 -B .domain-delivery/skills/delivery-hub/scripts/hub.py doctor \
     --skill-source .domain-delivery/skills/delivery-workflow/SKILL.md
   ```

   Confirm tests execute the renamed validators and schemas, that current links
   resolve, and that the host selects the pinned Skill rather than a stale cache.
   Preserve only deliberate historical occurrences of the old name.

## Preserved contracts and rollback

`.domain-delivery/kernel/scripts/kernel.py`, schema versions, numbered artifact
names and semantics are unchanged. Never rewrite `specs/**`, `evidence/**`,
frozen Snapshot manifests, historical evidence digests, ADR acceptance text or
past CHANGELOG entries to disguise their original package version or paths.
Historical verification still uses the original package and Graph provenance.

If the consumer upgrade fails, restore the prior submodule pin, workflow.lock
and matching adapter changes together. Do not combine old adapter paths with
the renamed package or edit frozen artifacts to make the upgrade pass.
