import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from domain_delivery_kernel import kernel


COMMIT = "a" * 40
DIGEST = "sha256:" + "1" * 64


def finish_index(nodes):
    index = {"schema_version": 1, "source_root": "docs/domain", "nodes": nodes}
    index["index_digest"] = kernel.digest_json(index)
    return index


def authority_node():
    return {
        "id": "authority:product",
        "type": "authority",
        "title": "Product governance",
        "status": "confirmed",
        "readiness": "L3",
        "sources": ["decision:governance"],
        "scope": ["capability:*"],
        "blocking_questions": [],
        "confirmed_by": "product-governance",
        "confirmed_at": "2026-09-01",
        "confirmation_source": "ticket:DEC-1",
        "source_path": "authorities/product.md",
        "body": "Product governance confirms capability rules.\n",
        "content_digest": kernel.digest_bytes(b"authority"),
    }


def capability_node(status="confirmed", readiness="L3", authority="authority:product"):
    node = {
        "id": "capability:reminder",
        "type": "capability",
        "title": "Reminder",
        "status": status,
        "readiness": readiness,
        "authority": authority,
        "sources": ["code:reminder-service/main"],
        "scope": ["save customer reminder intent"],
        "out_of_scope": ["notification delivery"],
        "open_questions": [],
        "source_path": "capabilities/reminder.md",
        "body": "Reminder stores customer intent.\n",
        "content_digest": kernel.digest_bytes(b"capability"),
    }
    if readiness == "L3":
        node.update(
            {
                "blocking_questions": [],
                "preconditions": ["customer identity is known"],
                "postconditions": ["reminder intent is retrievable"],
                "invariants": ["one saved intent per customer and item"],
                "invalid_cases": ["unknown item is rejected"],
            }
        )
    if status == "confirmed":
        node.update(
            {
                "confirmed_by": "reminder-product-owner",
                "confirmed_at": "2026-09-01",
                "confirmation_source": "ticket:TCK-1",
            }
        )
    return node


def term_node():
    return {
        "id": "term:catalog-item",
        "type": "term",
        "title": "Catalog item",
        "status": "candidate",
        "readiness": "L1",
        "sources": ["document:glossary"],
        "source_path": "terms/catalog-item.md",
        "body": "A product term.\n",
        "content_digest": kernel.digest_bytes(b"term"),
    }


def required_checks(*repositories):
    return [
        {
            "repository_id": repository,
            "check_id": "unit-tests",
            "trusted_attestors": ["ci:test-runner"],
        }
        for repository in repositories
    ]


def frozen(index=None, repositories=("reminder-service",)):
    index = index or finish_index([authority_node(), capability_node()])
    return kernel.freeze_snapshot(
        "reminder-digest",
        "v1",
        index,
        ["capability:reminder"],
        ["server"],
        repositories,
        required_checks(*repositories),
        COMMIT,
    )


def result_entry(snapshot, exit_code=kernel.PASS, repository="reminder-service", previous=None):
    entry = {
        "schema_version": 1,
        "kind": "result",
        "snapshot_digest": snapshot["snapshot_digest"],
        "repository_id": repository,
        "check_id": "unit-tests",
        "exit_code": exit_code,
        "checker_digest": DIGEST,
        "repo_commit": COMMIT,
        "repo_state_digest": DIGEST,
        "output_digest": DIGEST,
        "performed_by": "agent:implementation",
        "recorded_at": "2026-09-01T00:00:00+00:00",
        "previous_hash": previous,
    }
    entry["entry_hash"] = kernel.digest_json(entry)
    return entry


def attestation_entry(snapshot, result, declared_by="ci:test-runner"):
    entry = {
        "schema_version": 1,
        "kind": "attestation",
        "snapshot_digest": snapshot["snapshot_digest"],
        "result_entry_hash": result["entry_hash"],
        "declared_by": declared_by,
        "declaration_mode": "ci_declaration",
        "artifact_digest": DIGEST,
        "recorded_at": "2026-09-01T00:01:00+00:00",
        "previous_hash": result["entry_hash"],
    }
    entry["entry_hash"] = kernel.digest_json(entry)
    return entry


class PluginPackagingTests(unittest.TestCase):
    def test_stable_cli_adapter_exposes_kernel_commands(self):
        cli = PLUGIN_ROOT / "scripts" / "kernel.py"
        result = subprocess.run(
            [sys.executable, "-B", str(cli), "--help"],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for command in (
            "compile",
            "gate-index",
            "freeze",
            "verify-snapshot",
            "drift",
            "record-result",
            "declare-attestation",
            "verify-evidence",
        ):
            self.assertIn(command, result.stdout)


class DomainGraphTests(unittest.TestCase):
    def test_compile_is_deterministic(self):
        text = """---
id: capability:reminder
type: capability
title: Reminder
status: candidate
readiness: L2
authority: unknown
sources: [\"code:main\"]
scope: [\"save intent\"]
out_of_scope: []
open_questions: [\"who confirms?\"]
---

Meaning.\n"""
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / "node.md").write_text(text, encoding="utf-8")
            self.assertEqual(kernel.compile_graph(source), kernel.compile_graph(source))

    def test_l2_requires_explicit_boundary_fields(self):
        node = capability_node(status="candidate", readiness="L2", authority="unknown")
        del node["open_questions"]
        self.assertTrue(any("open_questions" in error for error in kernel.validate_node_shape(node)))

    def test_present_optional_fields_are_always_typed_and_unique(self):
        node = term_node()
        node["readiness"] = "L0"
        node["sources"] = 123
        self.assertTrue(any("sources" in error for error in kernel.validate_node_shape(node)))
        capability = capability_node(status="candidate", readiness="L2", authority="unknown")
        capability["related_nodes"] = ["term:catalog-item", "term:catalog-item"]
        self.assertTrue(any("duplicates" in error for error in kernel.validate_node_shape(capability)))

    def test_id_namespace_must_match_type(self):
        node = authority_node()
        node["id"] = "term:product"
        self.assertTrue(any("namespace" in error for error in kernel.validate_node_shape(node)))

    def test_unknown_authority_cannot_confirm_node(self):
        node = capability_node(authority="authority:missing")
        errors = kernel.validate_index(finish_index([authority_node(), node]))
        self.assertTrue(any("authority does not resolve" in error for error in errors))

    def test_pinned_commit_reconstructs_the_whole_index(self):
        text = """---
id: term:catalog-item
type: term
title: Catalog item
status: candidate
readiness: L1
sources: [\"document:glossary\"]
---

A product term.\n"""
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            source = repo / "docs" / "domain"
            source.mkdir(parents=True)
            (source / "term.md").write_text(text, encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            subprocess.run(["git", "add", "docs/domain/term.md"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "graph"], cwd=repo, check=True)
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True, capture_output=True,
            ).stdout.strip()
            index = kernel.compile_graph(source)
            kernel.verify_index_at_commit(index, commit, repo)
            tampered = copy.deepcopy(index)
            tampered["nodes"][0]["title"] = "Manipulated title"
            tampered["index_digest"] = kernel.digest_json(
                {key: value for key, value in tampered.items() if key != "index_digest"}
            )
            with self.assertRaisesRegex(kernel.KernelError, "deterministic index"):
                kernel.verify_index_at_commit(tampered, commit, repo)

    def test_crlf_markdown_reconstructs_from_commit(self):
        text = (
            "---\r\nid: term:catalog-item\r\ntype: term\r\ntitle: Catalog item\r\n"
            "status: candidate\r\nreadiness: L1\r\nsources: [\"document:glossary\"]\r\n"
            "---\r\n\r\nA product term.\r\n"
        ).encode()
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            source = repo / "docs" / "domain"
            source.mkdir(parents=True)
            (source / "term.md").write_bytes(text)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            subprocess.run(["git", "add", "docs/domain/term.md"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "crlf graph"], cwd=repo, check=True)
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True, capture_output=True,
            ).stdout.strip()
            kernel.verify_index_at_commit(kernel.compile_graph(source), commit, repo)

    def test_malformed_utf8_and_duplicate_json_exit_invalid_without_traceback(self):
        command = [sys.executable, "-B", str(Path(kernel.__file__).resolve()), "gate-index", "--index"]
        with tempfile.TemporaryDirectory() as directory:
            invalid_utf8 = Path(directory) / "utf8.json"
            invalid_utf8.write_bytes(b"\xff")
            result = subprocess.run(command + [str(invalid_utf8)], text=True, capture_output=True)
            self.assertEqual(result.returncode, kernel.INVALID)
            self.assertNotIn("Traceback", result.stderr)
            duplicate = Path(directory) / "duplicate.json"
            duplicate.write_text('{"schema_version":1,"schema_version":1}\n', encoding="utf-8")
            result = subprocess.run(command + [str(duplicate)], text=True, capture_output=True)
            self.assertEqual(result.returncode, kernel.INVALID)
            self.assertIn("duplicate JSON key", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_candidate_l2_cannot_enter_snapshot(self):
        candidate = capability_node(status="candidate", readiness="L2", authority="unknown")
        index = finish_index([authority_node(), candidate])
        with self.assertRaisesRegex(kernel.KernelError, "confirmed L3"):
            frozen(index)


class SnapshotTests(unittest.TestCase):
    def test_empty_required_checks_are_rejected(self):
        index = finish_index([authority_node(), capability_node()])
        with self.assertRaisesRegex(kernel.KernelError, "requires at least one repository-scoped check"):
            kernel.freeze_snapshot(
                "reminder-digest", "v1", index, ["capability:reminder"],
                ["server"], ["reminder-service"], [], COMMIT,
            )

    def test_same_check_id_in_multiple_repositories_remains_distinct(self):
        snapshot, _, _ = frozen(repositories=("reminder-service", "edge-gateway"))
        keys = {(item["repository_id"], item["check_id"]) for item in snapshot["required_checks"]}
        self.assertEqual(
            keys,
            {("reminder-service", "unit-tests"), ("edge-gateway", "unit-tests")},
        )

    def test_required_check_order_does_not_change_snapshot(self):
        index = finish_index([authority_node(), capability_node()])
        repositories = ["reminder-service", "edge-gateway"]
        checks = required_checks(*repositories)
        first, _, _ = kernel.freeze_snapshot(
            "reminder-digest", "v1", index, ["capability:reminder"],
            ["server"], repositories, checks, COMMIT,
        )
        second, _, _ = kernel.freeze_snapshot(
            "reminder-digest", "v1", index, ["capability:reminder"],
            ["server"], reversed(repositories), reversed(checks), COMMIT,
        )
        self.assertEqual(first, second)

    def test_every_repository_requires_a_check(self):
        index = finish_index([authority_node(), capability_node()])
        with self.assertRaisesRegex(kernel.KernelError, "without required checks"):
            kernel.freeze_snapshot(
                "reminder-digest", "v1", index, ["capability:reminder"],
                ["server"], ["reminder-service", "edge-gateway"],
                required_checks("reminder-service"), COMMIT,
            )

    def test_snapshot_publish_is_immutable(self):
        snapshot, bundle, payload = frozen()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "v1"
            kernel.publish_snapshot(output, snapshot, bundle, payload)
            with self.assertRaisesRegex(kernel.KernelError, "immutable"):
                kernel.publish_snapshot(output, snapshot, bundle, payload)

    def test_domain_bundle_tamper_is_detected(self):
        snapshot, bundle, payload = frozen()
        self.assertIn('"preconditions"', bundle)
        self.assertIn('"invariants"', bundle)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "v1"
            kernel.publish_snapshot(output, snapshot, bundle, payload)
            manifest = output / "snapshot-manifest.json"
            (output / "DOMAIN.md").write_text("tampered\n", encoding="utf-8")
            self.assertIn("domain bundle digest mismatch", kernel.validate_snapshot(snapshot, manifest))

    def test_payload_and_markdown_cannot_diverge(self):
        snapshot, bundle, payload = frozen()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "v1"
            kernel.publish_snapshot(output, snapshot, bundle, payload)
            payload[1]["preconditions"] = ["manipulated condition"]
            (output / "domain-payload.json").write_bytes(kernel.canonical(payload))
            snapshot["domain_bundle"]["payload_digest"] = kernel.digest_json(payload)
            snapshot["snapshot_digest"] = kernel.digest_json(
                {key: value for key, value in snapshot.items() if key != "snapshot_digest"}
            )
            errors = kernel.validate_snapshot(snapshot, output / "snapshot-manifest.json")
            self.assertIn("domain bundle is not the rendering of its payload", errors)

    def test_verify_snapshot_binds_payload_to_exact_committed_closure(self):
        authority = """---
id: authority:product
type: authority
title: Product governance
status: confirmed
readiness: L3
sources: [\"decision:governance\"]
scope: [\"capability:*\"]
blocking_questions: []
confirmed_by: product-governance
confirmed_at: 2026-09-01
confirmation_source: ticket:DEC-1
---

Product governance confirms capability rules.\n"""
        capability = """---
id: capability:reminder
type: capability
title: Reminder
status: confirmed
readiness: L3
authority: authority:product
sources: [\"ticket:TCK-1\"]
scope: [\"save intent\"]
out_of_scope: [\"notification delivery\"]
open_questions: []
blocking_questions: []
preconditions: [\"customer is known\"]
postconditions: [\"intent is retrievable\"]
invariants: [\"one intent per item\"]
invalid_cases: [\"unknown item is rejected\"]
confirmed_by: reminder-product-owner
confirmed_at: 2026-09-01
confirmation_source: ticket:TCK-1
---

Reminder stores customer intent.\n"""
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            source = repo / "docs" / "domain"
            (source / "authorities").mkdir(parents=True)
            (source / "capabilities").mkdir()
            (source / "authorities" / "product.md").write_text(authority, encoding="utf-8")
            (source / "capabilities" / "reminder.md").write_text(capability, encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            subprocess.run(["git", "add", "docs/domain"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "confirmed graph"], cwd=repo, check=True)
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True, capture_output=True,
            ).stdout.strip()
            index = kernel.compile_graph(source)
            snapshot, bundle, payload = kernel.freeze_snapshot(
                "reminder-digest", "v1", index, ["capability:reminder"],
                ["server"], ["reminder-service"], required_checks("reminder-service"), commit,
            )
            output = repo / "specs" / "reminder-digest" / "snapshot" / "v1"
            kernel.publish_snapshot(output, snapshot, bundle, payload)
            manifest = output / "snapshot-manifest.json"
            self.assertEqual(kernel.verify_snapshot_against_graph(snapshot, manifest), [])
            command = [
                sys.executable, "-B", str(Path(kernel.__file__).resolve()),
                "verify-snapshot", "--snapshot", str(manifest),
            ]
            self.assertEqual(subprocess.run(command, cwd=repo, capture_output=True).returncode, kernel.PASS)

            payload[1]["invariants"] = ["manipulated but internally consistent"]
            forged_bundle = kernel.render_domain_bundle(
                snapshot["feature"], snapshot["snapshot_version"], snapshot["graph_commit"], payload,
            )
            (output / "DOMAIN.md").write_text(forged_bundle, encoding="utf-8")
            (output / "domain-payload.json").write_bytes(kernel.canonical(payload))
            snapshot["domain_bundle"]["digest"] = kernel.digest_bytes(forged_bundle.encode())
            snapshot["domain_bundle"]["payload_digest"] = kernel.digest_json(payload)
            snapshot["snapshot_digest"] = kernel.digest_json(
                {key: value for key, value in snapshot.items() if key != "snapshot_digest"}
            )
            manifest.write_bytes(kernel.canonical(snapshot))
            self.assertEqual(kernel.validate_snapshot(snapshot, manifest), [])
            errors = kernel.verify_snapshot_against_graph(snapshot, manifest)
            self.assertIn("snapshot payload is not the exact root dependency closure at the pinned commit", errors)
            result = subprocess.run(command, cwd=repo, text=True, capture_output=True)
            self.assertEqual(result.returncode, kernel.INVALID)
            self.assertNotIn("Traceback", result.stderr)

    def test_drift_distinguishes_global_and_selected_changes(self):
        index = finish_index([authority_node(), capability_node(), term_node()])
        snapshot, _, _ = frozen(index)
        unrelated = copy.deepcopy(index)
        unrelated["nodes"][2]["content_digest"] = kernel.digest_bytes(b"changed term")
        unrelated["index_digest"] = kernel.digest_json({key: value for key, value in unrelated.items() if key != "index_digest"})
        self.assertEqual(kernel.detect_drift(snapshot, unrelated), ["global index changed"])
        selected = copy.deepcopy(unrelated)
        selected["nodes"][1]["content_digest"] = kernel.digest_bytes(b"changed capability")
        selected["index_digest"] = kernel.digest_json({key: value for key, value in selected.items() if key != "index_digest"})
        self.assertEqual(
            kernel.detect_drift(snapshot, selected),
            ["global index changed", "selected node changed: capability:reminder"],
        )

    def test_malformed_snapshot_and_index_return_errors(self):
        self.assertTrue(kernel.validate_snapshot({"nodes": [None]}))
        self.assertTrue(kernel.validate_index({"schema_version": 1, "source_root": ".", "nodes": [None], "index_digest": DIGEST}))


class EvidenceTests(unittest.TestCase):
    def test_missing_result_fields_are_invalid(self):
        snapshot, _, _ = frozen()
        entry = result_entry(snapshot)
        del entry["output_digest"]
        self.assertTrue(kernel.validate_entry_shape(entry, 1))

    def test_pass_requires_a_trusted_independent_attestation_declaration(self):
        snapshot, _, _ = frozen()
        result = result_entry(snapshot)
        self.assertTrue(any("lacks trusted" in error for error in kernel.verify_evidence(snapshot, [result])))
        attestation = attestation_entry(snapshot, result)
        self.assertEqual(kernel.verify_evidence(snapshot, [result, attestation]), [])

    def test_not_applicable_never_passes(self):
        snapshot, _, _ = frozen()
        result = result_entry(snapshot, kernel.NOT_APPLICABLE)
        attestation = attestation_entry(snapshot, result)
        self.assertTrue(any("did not pass" in error for error in kernel.verify_evidence(snapshot, [result, attestation])))

    def test_performer_cannot_be_verifier(self):
        snapshot, _, _ = frozen()
        result = result_entry(snapshot)
        attestation = attestation_entry(snapshot, result, declared_by="agent:implementation")
        self.assertTrue(any("lacks trusted" in error for error in kernel.verify_evidence(snapshot, [result, attestation])))

    def test_corrupt_ledger_refuses_append(self):
        snapshot, _, _ = frozen()
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger.jsonl"
            ledger.write_text("not json\n", encoding="utf-8")
            with self.assertRaisesRegex(kernel.KernelError, "invalid JSON"):
                kernel.append_locked(ledger, snapshot, lambda _entries: {})

    def test_repository_state_digest_tracks_dirty_content(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            tracked = repo / "tracked.txt"
            tracked.write_text("one\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "initial"], cwd=repo, check=True)
            commit, clean = kernel.repo_state(repo)
            tracked.write_text("two\n", encoding="utf-8")
            same_commit, dirty = kernel.repo_state(repo)
            self.assertEqual(commit, same_commit)
            self.assertNotEqual(clean, dirty)


if __name__ == "__main__":
    unittest.main()
