# Domain Delivery Kernel

The deterministic machinery shared by the Domain and Delivery lifecycles. The
canonical graph record stays in Markdown inside each Delivery Hub; only
`confirmed` nodes are accepted semantic meaning.

- method: [`../docs/workflow.md`](../docs/workflow.md)
- front matter contract: [`../docs/domain-graph-schema.md`](../docs/domain-graph-schema.md)
- repository commands: each product repository's own agent guide

The kernel compiles the Domain Graph, freezes an immutable Feature Snapshot,
and binds repository evidence to that snapshot. It does not encode a fixed
number of acts, interview rounds, languages or test frameworks. It carries no
product, organisation or tracker assumptions.

Request intake, check projection and repository-packet validation belong to the
calling lifecycle Skill, not here. Skills and other adapters may add the kernel
root to `sys.path` and import the supported seam exported by
`domain_delivery_kernel/__init__.py`: `load_json`,
`verify_snapshot_against_graph`, `digest_json`, `git_root`, `EXECUTABLE_TYPES`,
`ID_RE`, `NAME_RE` and `KernelError`. The kernel never imports an adapter;
dependency direction is adapter → kernel.

The stable CLI interface is `scripts/kernel.py`; callers must not execute the
implementation module directly.

## Calling it from a Hub

A Hub installs this repository as a submodule at the fixed path
`.domain-delivery/`, so every command below is written Hub-relative and run from
the Hub root. Paths such as `docs/domain`, `domain-index/`, `specs/` and
`evidence/` are Hub paths.

## Domain Graph

```bash
python3 -B .domain-delivery/kernel/scripts/kernel.py compile \
  --source docs/domain \
  --output domain-index/index.json

python3 -B .domain-delivery/kernel/scripts/kernel.py gate-index \
  --index domain-index/index.json
```

The files under [`schema/`](schema/) mirror the runtime validators as
machine-readable contracts; the stdlib-only kernel does not require a JSON
Schema package.

## Immutable Feature Snapshot

Only a committed, reproducible `confirmed L3` dependency closure can freeze.
Every declared repository must have at least one repository-scoped required
check and a declared trusted attestor.

```bash
python3 -B .domain-delivery/kernel/scripts/kernel.py freeze \
  --feature reminder-digest \
  --version v1 \
  --index domain-index/index.json \
  --node capability:reminder \
  --graph-commit <domain-graph-commit> \
  --delivery-lane server \
  --repository reminder-service \
  --required-check reminder-service/unit-tests \
  --trusted-attestor ci:test-runner \
  --output specs/reminder-digest/snapshot/v1

python3 -B .domain-delivery/kernel/scripts/kernel.py verify-snapshot \
  --snapshot specs/reminder-digest/snapshot/v1/snapshot-manifest.json

python3 -B .domain-delivery/kernel/scripts/kernel.py drift \
  --snapshot specs/reminder-digest/snapshot/v1/snapshot-manifest.json \
  --index domain-index/index.json
```

`reminder-digest` and `reminder-service` are synthetic example names, not a real
delivery.

The snapshot bundles every selected node's semantic fields and body in
`DOMAIN.md`. A derived `domain-payload.json` lets `verify-snapshot` reconstruct
that Markdown and verify the closure; it is a checking surface, not the meaning
people edit. The manifest records both digests and refuses to overwrite an
existing version. A correction creates a new directory such as `v2` and passes
the prior snapshot digest through `--supersedes`.

## Evidence

A result and its independent attestation declaration are separate hash-chain
entries. The CLI only appends; the file is tamper-evident, not tamper-proof,
unless an external system retains or signs the terminal entry hash.
The kernel computes checker, output, Git commit and dirty-state digests; callers
do not supply those values.

```bash
python3 -B .domain-delivery/kernel/scripts/kernel.py record-result \
  --ledger evidence/reminder-digest/run-001/check-ledger.jsonl \
  --snapshot specs/reminder-digest/snapshot/v1/snapshot-manifest.json \
  --repository-id reminder-service \
  --check-id unit-tests \
  --exit-code 0 \
  --repo-path codebases/reminder-service \
  --checker-file codebases/reminder-service/scripts/test.sh \
  --output-file /tmp/reminder-unit-tests.txt \
  --performed-by agent:implementation

python3 -B .domain-delivery/kernel/scripts/kernel.py declare-attestation \
  --ledger evidence/reminder-digest/run-001/check-ledger.jsonl \
  --snapshot specs/reminder-digest/snapshot/v1/snapshot-manifest.json \
  --result-hash <result-entry-hash> \
  --declared-by ci:test-runner \
  --declaration-mode ci_declaration \
  --attestation-file /tmp/reminder-unit-tests-attestation.json

python3 -B .domain-delivery/kernel/scripts/kernel.py verify-evidence \
  --ledger evidence/reminder-digest/run-001/check-ledger.jsonl \
  --snapshot specs/reminder-digest/snapshot/v1/snapshot-manifest.json
```

The exit code and identity values such as `ci:test-runner` are declarations,
not cryptographic authentication or proof that the checker ran. The CI or local
adapter that calls these commands must run the check, authenticate the actor,
produce the attestation artifact, and retain or sign the terminal hash. The
kernel binds those declarations and bytes; it never upgrades an unauthenticated
string or arbitrary file into independent proof.

Exit codes are part of the contract: `0` pass, `1` fail, `2` invalid input or
evidence, and `3` not applicable. Required checks pass only with result `0`
plus a trusted, independently declared attestation. This is an integrity gate;
its authenticity is only as strong as the adapter and external anchor. N/A is
never a pass.

## Tests

Run from this repository's root:

```bash
python3 -B -m unittest discover -s kernel/tests -v
```

Confirmed authorities, L3 nodes and snapshots created by these tests are
synthetic fixtures in temporary Git repositories. Passing kernel tests says
nothing about the maturity or confirmation status of any Hub's actual Domain
Graph.
