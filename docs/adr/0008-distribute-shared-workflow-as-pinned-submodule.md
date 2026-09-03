# Distribute the shared workflow as a pinned Git submodule

Status: Accepted (2026-09-03)

The shared workflow — three lifecycle Skills, the kernel, artifact schemas,
migrations and method docs — lives in this independent repository,
`NatChung/domain-delivery`, released as one atomic SemVer unit. Every Delivery
Hub consumes it as a Git submodule at the fixed path `.domain-delivery/`,
pinned to a release tag, and records tag, full commit and package digest in
`workflow.lock`. Both host marketplaces (`.claude-plugin/marketplace.json` for
Claude Code, `.agents/plugins/marketplace.json` for Codex) point at
`./.domain-delivery`, so both hosts read the same bytes by construction rather
than by comparing two plugin caches after the fact. This supersedes ADR 0007's
statement that the kernel is consumed directly from a Hub with no marketplace
entry.

Considered and rejected: installing through each host's own marketplace from
GitHub. That gives two independently cached copies that can drift, and an
upgrade would need to be repeated per host. A submodule makes an upgrade one
reviewed commit — move the submodule, update the lock — which is what ADR 0004
and the "pin and upgrade explicitly" rule require.

Consequences:

- The submodule directory name is part of the contract. The shared `SKILL.md`
  files use only the frontmatter subset both hosts accept, so they cannot use
  host-specific root variables and must address the kernel by a Hub-relative
  path (`.domain-delivery/kernel/scripts/kernel.py`). Renaming the directory
  breaks every consumer.
- `.gitmodules` must use the public URL
  `https://github.com/NatChung/domain-delivery.git`, not a machine-local SSH
  alias; local identity is handled with `url.<alias>.insteadOf`.
- `init` and `upgrade` may run `git submodule update --init` on behalf of the
  user; `doctor` may not. As first written this ADR asked `doctor` to do both,
  which is a contradiction: initialising a submodule clones over the network and
  writes to the working tree. Read-only wins. `doctor` reports a missing
  installation as a finding and names the command to fix it.
- `upgrade` refuses to run on a dirty working tree, and separately refuses when
  the installed workflow itself has uncommitted changes. Moving the submodule to
  a new tag is how an upgrade starts, so the gitlink move alone must not block
  one — but hand-edited bytes inside the installation must, or the lock would
  record a digest of a modification nobody reviewed and every later `doctor`
  would call it healthy.
- No cross-host behaviour test is required: gates are enforced by the kernel,
  which is host-neutral Python, so host differences cannot pass a bad artifact.
