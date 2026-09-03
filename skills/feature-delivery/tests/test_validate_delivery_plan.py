import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[3]
KERNEL_ROOT = PACKAGE_ROOT / "kernel"
if str(KERNEL_ROOT) not in sys.path:
    sys.path.insert(0, str(KERNEL_ROOT))

from domain_delivery_kernel import kernel


SKILL_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL_ROOT / "scripts" / "validate_delivery_plan.py"
if str(VALIDATOR.parent) not in sys.path:
    sys.path.insert(0, str(VALIDATOR.parent))

import validate_delivery_plan as contract


AUTHORITY = """---
id: authority:product
type: authority
title: Product governance
status: confirmed
readiness: L3
sources: ["decision:governance"]
scope: ["capability:*"]
blocking_questions: []
confirmed_by: product-governance
confirmed_at: 2026-09-01
confirmation_source: ticket:DEC-1
---

Product governance confirms capability rules.
"""

CAPABILITY = """---
id: capability:reminder
type: capability
title: Reminder
status: confirmed
readiness: L3
authority: authority:product
sources: ["ticket:TCK-1"]
scope: ["save customer reminder intent"]
out_of_scope: ["notification delivery"]
open_questions: []
blocking_questions: []
preconditions: ["customer identity is known"]
postconditions: ["reminder intent is retrievable"]
invariants: ["one saved intent per customer and item"]
invalid_cases: ["unknown item is rejected"]
confirmed_by: reminder-product-owner
confirmed_at: 2026-09-01
confirmation_source: ticket:TCK-1
---

Reminder stores customer intent.
"""


def create_snapshot(root, repositories=("reminder-service",)):
    source = root / "docs" / "domain"
    (source / "authorities").mkdir(parents=True)
    (source / "capabilities").mkdir()
    (source / "authorities" / "product.md").write_text(AUTHORITY, encoding="utf-8")
    (source / "capabilities" / "reminder.md").write_text(CAPABILITY, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "docs/domain"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "confirmed graph"], cwd=root, check=True)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    index = kernel.compile_graph(source)
    checks = [
        {
            "repository_id": repository,
            "check_id": "unit-tests",
            "trusted_attestors": ["ci:test-runner"],
        }
        for repository in repositories
    ]
    snapshot, bundle, payload = kernel.freeze_snapshot(
        "reminder-notification",
        "v1",
        index,
        ["capability:reminder"],
        ["server"],
        repositories,
        checks,
        commit,
    )
    output = root / "specs" / "reminder-notification" / "snapshot" / "v1"
    kernel.publish_snapshot(output, snapshot, bundle, payload)
    return output / "snapshot-manifest.json", snapshot


def ready_projection(snapshot):
    return {
        "schema_version": "check-projection/v0.1",
        "projection_status": "ready_for_task_planning",
        "feature": snapshot["feature"],
        "snapshot_digest": snapshot["snapshot_digest"],
        "projections": [
            {
                "projection_id": f"05-{item['repository_id']}-{item['check_id']}",
                "repository_id": item["repository_id"],
                "check_id": item["check_id"],
                "layers": ["bdd", "design_by_contract", "native_quality"],
                "snapshot_rule_refs": [
                    {
                        "node_id": "capability:reminder",
                        "field": "scope",
                        "statement": "save customer reminder intent",
                    },
                    {
                        "node_id": "capability:reminder",
                        "field": "out_of_scope",
                        "statement": "notification delivery",
                    },
                    {
                        "node_id": "capability:reminder",
                        "field": "preconditions",
                        "statement": "customer identity is known",
                    },
                    {
                        "node_id": "capability:reminder",
                        "field": "postconditions",
                        "statement": "reminder intent is retrievable",
                    },
                    {
                        "node_id": "capability:reminder",
                        "field": "invariants",
                        "statement": "one saved intent per customer and item",
                    },
                    {
                        "node_id": "capability:reminder",
                        "field": "invalid_cases",
                        "statement": "unknown item is rejected",
                    }
                ],
                "repository_rule_refs": ["AGENTS.md#testing"],
                "specification_paths": [
                    f"05-01-{item['repository_id']}-{item['check_id']}.md"
                ],
                "planned_checker_path": "scripts/test.sh",
                "notes": [],
            }
            for item in snapshot["required_checks"]
        ],
        "blocking_reasons": [],
        "extensions": {},
    }


def ready_task_plan(root, snapshot, projection):
    for repository in snapshot["repositories"]:
        repo = root / "codebases" / repository
        repo.mkdir(parents=True)
        (repo / "AGENTS.md").write_text("# Agent guide\n", encoding="utf-8")
        (repo / "README.md").write_text("# Repository\n", encoding="utf-8")
    projections_by_repo = {
        repository: [
            item
            for item in projection["projections"]
            if item["repository_id"] == repository
        ]
        for repository in snapshot["repositories"]
    }
    return {
        "schema_version": "repository-task-plan/v0.1",
        "planning_status": "ready_for_repository_loops",
        "feature": snapshot["feature"],
        "snapshot_digest": snapshot["snapshot_digest"],
        "projection_digest": kernel.digest_json(projection),
        "packets": [
            {
                "packet_id": f"06-{repository}",
                "repository_id": repository,
                "repository_path": f"codebases/{repository}",
                "delivery_lane": snapshot["delivery_lanes"][0],
                "base_ref": "main",
                "repo_guides": ["AGENTS.md", "README.md"],
                "test_seams": ["public reminder command and query interfaces"],
                "projection_ids": [
                    item["projection_id"] for item in projections_by_repo[repository]
                ],
                "required_checks": [
                    item["check_id"] for item in projections_by_repo[repository]
                ],
                "depends_on_repositories": [],
                "cross_repo_contracts": [],
                "completion_criteria": [
                    "assigned checks produce fresh exit codes and output"
                ],
                "evidence_inputs": [
                    {
                        "check_id": item["check_id"],
                        "checker_file": item["planned_checker_path"],
                        "output_file": (
                            f"/tmp/07-{repository}-{item['check_id']}.txt"
                        ),
                    }
                    for item in projections_by_repo[repository]
                ],
                "notes": [],
            }
            for repository in snapshot["repositories"]
        ],
        "blocking_reasons": [],
        "extensions": {},
    }


class DeliveryPlanProjectionCliTests(unittest.TestCase):
    def run_validator(self, root, snapshot_path, projection, *extra_args, raw=None):
        projection_path = root / "05-check-projection.json"
        projection_path.write_text(
            raw if raw is not None else json.dumps(projection, ensure_ascii=False),
            encoding="utf-8",
        )
        if raw is None:
            for item in projection.get("projections", []):
                for relative in item.get("specification_paths", []):
                    (root / relative).write_text("# Specification\n", encoding="utf-8")
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(VALIDATOR),
                "--snapshot",
                str(snapshot_path),
                "--projection",
                str(projection_path),
                *extra_args,
            ],
            cwd=root,
            text=True,
            capture_output=True,
        )

    def run_task_validator(
        self,
        root,
        snapshot_path,
        projection,
        task_plan,
        *extra_args,
        artifact_root=None,
    ):
        artifact_root = artifact_root or root
        artifact_root.mkdir(parents=True, exist_ok=True)
        projection_path = artifact_root / "05-check-projection.json"
        projection_path.write_text(
            json.dumps(projection, ensure_ascii=False), encoding="utf-8"
        )
        for item in projection["projections"]:
            for relative in item["specification_paths"]:
                (artifact_root / relative).write_text(
                    "# Specification\n", encoding="utf-8"
                )
        task_plan_path = artifact_root / "06-repository-task-plan.json"
        task_plan_path.write_text(
            json.dumps(task_plan, ensure_ascii=False), encoding="utf-8"
        )
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(VALIDATOR),
                "--snapshot",
                str(snapshot_path),
                "--projection",
                str(projection_path),
                "--task-plan",
                str(task_plan_path),
                *extra_args,
            ],
            cwd=root,
            text=True,
            capture_output=True,
        )

    def test_exact_multi_repository_projection_coverage_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(
                root, ("reminder-service", "edge-gateway")
            )
            projection = ready_projection(snapshot)
            result = self.run_validator(
                root, manifest, projection, "--require-ready"
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), kernel.digest_json(projection))

    def test_missing_projection_is_valid_incomplete_but_not_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(
                root, ("reminder-service", "edge-gateway")
            )
            projection = ready_projection(snapshot)
            projection["projections"].pop()
            projection["projection_status"] = "incomplete"
            projection["blocking_reasons"] = ["edge-gateway/unit-tests is missing"]
            valid = self.run_validator(root, manifest, projection)
            gated = self.run_validator(root, manifest, projection, "--require-ready")

        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual(gated.returncode, 1, gated.stderr)

    def test_missing_frozen_rule_is_valid_incomplete_but_not_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(root)
            projection = ready_projection(snapshot)
            projection["projections"][0]["snapshot_rule_refs"].pop()
            falsely_ready = self.run_validator(root, manifest, projection)
            projection["projection_status"] = "incomplete"
            projection["blocking_reasons"] = ["one frozen invalid case is missing"]
            valid = self.run_validator(root, manifest, projection)
            gated = self.run_validator(root, manifest, projection, "--require-ready")

        self.assertEqual(falsely_ready.returncode, 2)
        self.assertIn("frozen acceptance rule is not projected", falsely_ready.stderr)
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual(gated.returncode, 1, gated.stderr)

    def test_unexpected_repository_check_pair_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(root)
            projection = ready_projection(snapshot)
            extra = copy.deepcopy(projection["projections"][0])
            extra["projection_id"] = "05-reminder-service-lint"
            extra["check_id"] = "lint"
            projection["projections"].append(extra)
            result = self.run_validator(root, manifest, projection)

        self.assertEqual(result.returncode, 2)
        self.assertIn("not declared by snapshot", result.stderr)

    def test_projection_id_must_match_numbered_schema_pattern(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(root)
            projection = ready_projection(snapshot)
            projection["projections"][0]["projection_id"] = "05-valid but invalid"
            result = self.run_validator(root, manifest, projection)

        self.assertEqual(result.returncode, 2)
        self.assertIn("projection_id is invalid", result.stderr)

    def test_wrong_snapshot_digest_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(root)
            projection = ready_projection(snapshot)
            projection["snapshot_digest"] = "sha256:" + "0" * 64
            result = self.run_validator(root, manifest, projection)

        self.assertEqual(result.returncode, 2)
        self.assertIn("snapshot_digest", result.stderr)

    def test_duplicate_json_key_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(root)
            text = json.dumps(ready_projection(snapshot), ensure_ascii=False)
            text = text.replace(
                '"feature": "reminder-notification",',
                '"feature": "wrong", "feature": "reminder-notification",',
                1,
            )
            result = self.run_validator(root, manifest, {}, raw=text)

        self.assertEqual(result.returncode, 2)
        self.assertIn("duplicate JSON key", result.stderr)

    def test_tampered_snapshot_is_invalid_even_when_manifest_shape_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(root)
            (manifest.parent / "DOMAIN.md").write_text("tampered\n", encoding="utf-8")
            result = self.run_validator(root, manifest, ready_projection(snapshot))

        self.assertEqual(result.returncode, 2)
        self.assertIn("domain bundle digest mismatch", result.stderr)

    def test_malformed_nested_projection_returns_invalid_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(root)
            projection = ready_projection(snapshot)
            projection["projections"][0]["repository_id"] = []
            projection["projections"][0]["snapshot_rule_refs"][0]["node_id"] = []
            result = self.run_validator(root, manifest, projection)

        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)


class DeliveryPlanTaskPlanCliTests(unittest.TestCase):
    def run_validator(
        self,
        root,
        snapshot_path,
        projection,
        task_plan,
        *extra_args,
        artifact_root=None,
    ):
        helper = DeliveryPlanProjectionCliTests()
        return helper.run_task_validator(
            root,
            snapshot_path,
            projection,
            task_plan,
            *extra_args,
            artifact_root=artifact_root,
        )

    def test_exact_multi_repository_task_plan_coverage_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(
                root, ("reminder-service", "edge-gateway")
            )
            projection = ready_projection(snapshot)
            task_plan = ready_task_plan(root, snapshot, projection)
            result = self.run_validator(
                root, manifest, projection, task_plan, "--require-ready"
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), kernel.digest_json(task_plan))

    def test_nested_planning_directory_resolves_repository_from_hub_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(root)
            projection = ready_projection(snapshot)
            task_plan = ready_task_plan(root, snapshot, projection)
            artifact_root = (
                root / "specs" / snapshot["feature"] / "delivery" / "v1"
            )
            result = self.run_validator(
                root,
                manifest,
                projection,
                task_plan,
                "--require-ready",
                artifact_root=artifact_root,
            )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_packet_is_valid_incomplete_but_not_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(
                root, ("reminder-service", "edge-gateway")
            )
            projection = ready_projection(snapshot)
            task_plan = ready_task_plan(root, snapshot, projection)
            task_plan["packets"].pop()
            task_plan["planning_status"] = "incomplete"
            task_plan["blocking_reasons"] = ["edge-gateway packet is missing"]
            valid = self.run_validator(root, manifest, projection, task_plan)
            gated = self.run_validator(
                root, manifest, projection, task_plan, "--require-ready"
            )

        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual(gated.returncode, 1, gated.stderr)

    def test_wrong_projection_digest_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(root)
            projection = ready_projection(snapshot)
            task_plan = ready_task_plan(root, snapshot, projection)
            task_plan["projection_digest"] = "sha256:" + "0" * 64
            result = self.run_validator(root, manifest, projection, task_plan)

        self.assertEqual(result.returncode, 2)
        self.assertIn("projection_digest", result.stderr)

    def test_packet_cannot_claim_an_unexpected_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(root)
            projection = ready_projection(snapshot)
            task_plan = ready_task_plan(root, snapshot, projection)
            task_plan["packets"][0]["required_checks"].append("lint")
            result = self.run_validator(root, manifest, projection, task_plan)

        self.assertEqual(result.returncode, 2)
        self.assertIn("not declared for repository", result.stderr)

    def test_evidence_output_must_use_numbered_absolute_tmp_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(root)
            projection = ready_projection(snapshot)
            task_plan = ready_task_plan(root, snapshot, projection)
            task_plan["packets"][0]["evidence_inputs"][0]["output_file"] = (
                "07-unit-tests.txt"
            )
            result = self.run_validator(root, manifest, projection, task_plan)

        self.assertEqual(result.returncode, 2)
        self.assertIn("absolute path under /tmp", result.stderr)

    def test_evidence_output_cannot_use_nested_tmp_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(root)
            projection = ready_projection(snapshot)
            task_plan = ready_task_plan(root, snapshot, projection)
            task_plan["packets"][0]["evidence_inputs"][0]["output_file"] = (
                "/tmp/nested/07-unit-tests.txt"
            )
            result = self.run_validator(root, manifest, projection, task_plan)

        self.assertEqual(result.returncode, 2)
        self.assertIn("absolute path under /tmp", result.stderr)

    def test_packet_id_must_match_numbered_schema_pattern(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(root)
            projection = ready_projection(snapshot)
            task_plan = ready_task_plan(root, snapshot, projection)
            task_plan["packets"][0]["packet_id"] = "06-valid but invalid"
            result = self.run_validator(root, manifest, projection, task_plan)

        self.assertEqual(result.returncode, 2)
        self.assertIn("packet_id is invalid", result.stderr)

    def test_projection_cannot_be_assigned_to_two_packets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(
                root, ("reminder-service", "edge-gateway")
            )
            projection = ready_projection(snapshot)
            task_plan = ready_task_plan(root, snapshot, projection)
            duplicate = task_plan["packets"][0]["projection_ids"][0]
            task_plan["packets"][1]["projection_ids"].append(duplicate)
            result = self.run_validator(root, manifest, projection, task_plan)

        self.assertEqual(result.returncode, 2)
        self.assertIn("assigned more than once", result.stderr)

    def test_repository_dependency_cycle_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(
                root, ("reminder-service", "edge-gateway")
            )
            projection = ready_projection(snapshot)
            task_plan = ready_task_plan(root, snapshot, projection)
            task_plan["packets"][0]["depends_on_repositories"] = ["edge-gateway"]
            task_plan["packets"][1]["depends_on_repositories"] = [
                "reminder-service"
            ]
            result = self.run_validator(root, manifest, projection, task_plan)

        self.assertEqual(result.returncode, 2)
        self.assertIn("dependency cycle", result.stderr)

    def test_malformed_nested_packet_returns_invalid_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, snapshot = create_snapshot(root)
            projection = ready_projection(snapshot)
            task_plan = ready_task_plan(root, snapshot, projection)
            task_plan["packets"][0]["delivery_lane"] = []
            result = self.run_validator(root, manifest, projection, task_plan)

        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)


class DeliveryPlanSchemaParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema_path = SKILL_ROOT / "references" / "05-06-delivery-plan.schema.json"
        cls.schema = json.loads(schema_path.read_text(encoding="utf-8"))

    def assert_object_fields(self, definition_name, runtime_fields):
        definition = self.schema["$defs"][definition_name]
        self.assertFalse(definition["additionalProperties"])
        self.assertEqual(set(definition["required"]), runtime_fields)
        self.assertEqual(set(definition["properties"]), runtime_fields)

    def test_runtime_and_schema_shapes_match(self):
        self.assert_object_fields("checkProjection", contract.PROJECTION_FIELDS)
        self.assert_object_fields("projection", contract.PROJECTION_ITEM_FIELDS)
        self.assert_object_fields(
            "snapshotRuleRef", contract.SNAPSHOT_RULE_REF_FIELDS
        )
        self.assert_object_fields("repositoryTaskPlan", contract.TASK_PLAN_FIELDS)
        self.assert_object_fields("packet", contract.PACKET_FIELDS)
        self.assert_object_fields("evidenceInput", contract.EVIDENCE_INPUT_FIELDS)

    def test_runtime_and_schema_versions_enums_and_patterns_match(self):
        definitions = self.schema["$defs"]
        projection = definitions["checkProjection"]["properties"]
        task_plan = definitions["repositoryTaskPlan"]["properties"]
        projection_item = definitions["projection"]["properties"]
        packet = definitions["packet"]["properties"]
        self.assertEqual(projection["schema_version"]["const"], contract.PROJECTION_VERSION)
        self.assertEqual(
            set(projection["projection_status"]["enum"]),
            contract.PROJECTION_STATUSES,
        )
        self.assertEqual(task_plan["schema_version"]["const"], contract.TASK_PLAN_VERSION)
        self.assertEqual(
            set(task_plan["planning_status"]["enum"]), contract.TASK_PLAN_STATUSES
        )
        self.assertEqual(
            set(projection_item["layers"]["items"]["enum"]), contract.LAYERS
        )
        self.assertEqual(
            set(definitions["snapshotRuleRef"]["properties"]["field"]["enum"]),
            contract.RULE_FIELDS,
        )
        self.assertEqual(
            definitions["snapshotRuleRef"]["properties"]["node_id"]["pattern"],
            contract.ID_RE.pattern,
        )
        self.assertEqual(
            projection_item["projection_id"]["pattern"],
            contract.PROJECTION_ID_RE.pattern,
        )
        self.assertEqual(packet["packet_id"]["pattern"], contract.PACKET_ID_RE.pattern)
        self.assertEqual(definitions["name"]["pattern"], contract.NAME_RE.pattern)
        self.assertEqual(
            definitions["safeRelativePath"]["pattern"],
            contract.SAFE_RELATIVE_PATH_RE.pattern,
        )
        self.assertEqual(
            definitions["evidenceInput"]["properties"]["output_file"]["pattern"],
            contract.OUTPUT_PATH_RE.pattern,
        )


if __name__ == "__main__":
    unittest.main()
