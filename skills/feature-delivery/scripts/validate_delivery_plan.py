#!/usr/bin/env python3
"""Validate numbered Step 05/06 planning artifacts against a Feature Snapshot."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any


if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from _paths import KERNEL_ROOT  # noqa: E402

if str(KERNEL_ROOT) not in sys.path:
    sys.path.insert(0, str(KERNEL_ROOT))

from domain_delivery_kernel import (  # noqa: E402
    EXECUTABLE_TYPES,
    ID_RE,
    NAME_RE,
    KernelError,
    digest_json,
    git_root,
    load_json as load_kernel_json,
    verify_snapshot_against_graph,
)


PASS, FAIL, INVALID = 0, 1, 2
PROJECTION_VERSION = "check-projection/v0.1"
PROJECTION_STATUSES = {"ready_for_task_planning", "incomplete"}
LAYERS = {
    "bdd",
    "design_by_contract",
    "wire_contract",
    "architecture_contract",
    "native_quality",
}
RULE_FIELDS = {
    "scope",
    "out_of_scope",
    "preconditions",
    "postconditions",
    "invariants",
    "invalid_cases",
}
PROJECTION_FIELDS = {
    "schema_version",
    "projection_status",
    "feature",
    "snapshot_digest",
    "projections",
    "blocking_reasons",
    "extensions",
}
PROJECTION_ITEM_FIELDS = {
    "projection_id",
    "repository_id",
    "check_id",
    "layers",
    "snapshot_rule_refs",
    "repository_rule_refs",
    "specification_paths",
    "planned_checker_path",
    "notes",
}
TASK_PLAN_VERSION = "repository-task-plan/v0.1"
TASK_PLAN_STATUSES = {"ready_for_repository_loops", "incomplete"}
TASK_PLAN_FIELDS = {
    "schema_version",
    "planning_status",
    "feature",
    "snapshot_digest",
    "projection_digest",
    "packets",
    "blocking_reasons",
    "extensions",
}
PACKET_FIELDS = {
    "packet_id",
    "repository_id",
    "repository_path",
    "delivery_lane",
    "base_ref",
    "repo_guides",
    "test_seams",
    "projection_ids",
    "required_checks",
    "depends_on_repositories",
    "cross_repo_contracts",
    "completion_criteria",
    "evidence_inputs",
    "notes",
}
EVIDENCE_INPUT_FIELDS = {"check_id", "checker_file", "output_file"}
SNAPSHOT_RULE_REF_FIELDS = {"node_id", "field", "statement"}
PROJECTION_ID_RE = re.compile(r"^05-[a-z0-9][a-z0-9._-]*$")
PACKET_ID_RE = re.compile(r"^06-[a-z0-9][a-z0-9._-]*$")
SAFE_RELATIVE_PATH_RE = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$)).+$")
OUTPUT_PATH_RE = re.compile(r"^/tmp/07-[^/]+$")


class ValidationError(ValueError):
    pass


def load_json(path: Path) -> Any:
    try:
        return load_kernel_json(path)
    except KernelError as exc:
        raise ValidationError(str(exc)) from exc


def exact_object(
    value: Any, path: str, fields: set[str], errors: list[str]
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return None
    if set(value) != fields:
        errors.append(
            f"{path} has missing or unknown fields "
            f"(missing={sorted(fields - set(value))}, "
            f"unknown={sorted(set(value) - fields)})"
        )
    return value


def nonempty_string(value: Any, path: str, errors: list[str]) -> bool:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} must be a non-empty string")
        return False
    return True


def string_list(
    value: Any,
    path: str,
    errors: list[str],
    *,
    allow_empty: bool = True,
    allowed: set[str] | None = None,
) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        errors.append(f"{path} must be an array of non-empty strings")
        return []
    if not allow_empty and not value:
        errors.append(f"{path} must not be empty")
    if len(value) != len(set(value)):
        errors.append(f"{path} must not contain duplicates")
    if allowed is not None:
        for item in value:
            if item not in allowed:
                errors.append(f"{path} contains invalid value {item!r}")
    return value


def safe_relative_path(value: Any, path: str, errors: list[str]) -> bool:
    if not nonempty_string(value, path, errors):
        return False
    if not SAFE_RELATIVE_PATH_RE.fullmatch(value):
        errors.append(f"{path} must be a safe relative path")
        return False
    return True


def load_verified_snapshot(path: Path) -> dict[str, Any]:
    try:
        snapshot = load_kernel_json(path)
        errors = verify_snapshot_against_graph(snapshot, path)
    except KernelError as exc:
        raise ValidationError(str(exc)) from exc
    if errors:
        raise ValidationError("\n".join(dict.fromkeys(errors)))
    return snapshot


def validate_projection(
    projection: Any,
    projection_path: Path,
    snapshot: dict[str, Any],
    snapshot_path: Path,
) -> list[str]:
    errors: list[str] = []
    projection = exact_object(projection, "projection", PROJECTION_FIELDS, errors)
    if projection is None:
        return errors
    if projection.get("schema_version") != PROJECTION_VERSION:
        errors.append(f"schema_version must be {PROJECTION_VERSION}")
    if projection.get("projection_status") not in PROJECTION_STATUSES:
        errors.append("projection_status is invalid")
    if projection.get("feature") != snapshot.get("feature"):
        errors.append("projection.feature does not match snapshot")
    if projection.get("snapshot_digest") != snapshot.get("snapshot_digest"):
        errors.append("projection.snapshot_digest does not match snapshot_digest")
    blocking = string_list(
        projection.get("blocking_reasons"), "blocking_reasons", errors
    )
    if not isinstance(projection.get("extensions"), dict):
        errors.append("extensions must be an object")

    payload_path = snapshot_path.parent / snapshot["domain_bundle"]["payload_path"]
    try:
        payload = load_kernel_json(payload_path)
    except KernelError as exc:
        errors.append(str(exc))
        payload = []
    payload_by_id = {
        node.get("id"): node
        for node in payload
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    } if isinstance(payload, list) else {}

    declared_pairs = {
        (item["repository_id"], item["check_id"])
        for item in snapshot.get("required_checks", [])
    }
    expected_rule_refs = {
        (node["id"], field, statement)
        for node in payload_by_id.values()
        if node.get("type") in EXECUTABLE_TYPES
        for field in RULE_FIELDS
        for statement in node.get(field, [])
    }
    projected_rule_refs: set[tuple[str, str, str]] = set()
    items = projection.get("projections")
    if not isinstance(items, list):
        errors.append("projections must be an array")
        items = []
    seen_ids: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()
    for index, item in enumerate(items):
        item_path = f"projections[{index}]"
        item = exact_object(item, item_path, PROJECTION_ITEM_FIELDS, errors)
        if item is None:
            continue
        projection_id = item.get("projection_id")
        if nonempty_string(projection_id, f"{item_path}.projection_id", errors):
            if not PROJECTION_ID_RE.fullmatch(projection_id):
                errors.append(f"{item_path}.projection_id is invalid")
            if projection_id in seen_ids:
                errors.append(f"duplicate projection_id: {projection_id}")
            seen_ids.add(projection_id)
        repository_id = item.get("repository_id")
        check_id = item.get("check_id")
        repository_valid = nonempty_string(
            repository_id, f"{item_path}.repository_id", errors
        )
        check_valid = nonempty_string(check_id, f"{item_path}.check_id", errors)
        if repository_valid and not NAME_RE.fullmatch(repository_id):
            errors.append(f"{item_path}.repository_id is invalid")
            repository_valid = False
        if check_valid and not NAME_RE.fullmatch(check_id):
            errors.append(f"{item_path}.check_id is invalid")
            check_valid = False
        if repository_valid and check_valid:
            pair = (repository_id, check_id)
            if pair in seen_pairs:
                errors.append(f"duplicate projection for {repository_id}/{check_id}")
            seen_pairs.add(pair)
            if pair not in declared_pairs:
                errors.append(
                    f"{repository_id}/{check_id} is not declared by snapshot"
                )
        string_list(
            item.get("layers"),
            f"{item_path}.layers",
            errors,
            allow_empty=False,
            allowed=LAYERS,
        )
        repository_refs = string_list(
            item.get("repository_rule_refs"),
            f"{item_path}.repository_rule_refs",
            errors,
        )
        rule_refs = item.get("snapshot_rule_refs")
        if not isinstance(rule_refs, list):
            errors.append(f"{item_path}.snapshot_rule_refs must be an array")
            rule_refs = []
        seen_rule_refs: set[tuple[str, str, str]] = set()
        for rule_index, rule in enumerate(rule_refs):
            rule_path = f"{item_path}.snapshot_rule_refs[{rule_index}]"
            rule = exact_object(
                rule, rule_path, SNAPSHOT_RULE_REF_FIELDS, errors
            )
            if rule is None:
                continue
            node_id = rule.get("node_id")
            field = rule.get("field")
            statement = rule.get("statement")
            nonempty_string(node_id, f"{rule_path}.node_id", errors)
            nonempty_string(statement, f"{rule_path}.statement", errors)
            if field not in RULE_FIELDS:
                errors.append(f"{rule_path}.field is invalid")
            key = (str(node_id), str(field), str(statement))
            if key in seen_rule_refs:
                errors.append(f"{rule_path} duplicates a source rule")
            seen_rule_refs.add(key)
            node = payload_by_id.get(node_id) if isinstance(node_id, str) else None
            frozen_values = node.get(field, []) if node and field in RULE_FIELDS else []
            if not node or statement not in frozen_values:
                errors.append(
                    f"{rule_path} does not resolve to an exact frozen domain rule"
                )
            elif isinstance(statement, str):
                projected_rule_refs.add((node_id, field, statement))
        if not rule_refs and not repository_refs:
            errors.append(f"{item_path} must declare at least one rule reference")
        specification_paths = string_list(
            item.get("specification_paths"),
            f"{item_path}.specification_paths",
            errors,
            allow_empty=False,
        )
        for spec_index, relative in enumerate(specification_paths):
            spec_path = f"{item_path}.specification_paths[{spec_index}]"
            if safe_relative_path(relative, spec_path, errors):
                if not (projection_path.parent / relative).is_file():
                    errors.append(f"{spec_path} does not exist")
        safe_relative_path(
            item.get("planned_checker_path"),
            f"{item_path}.planned_checker_path",
            errors,
        )
        string_list(item.get("notes"), f"{item_path}.notes", errors)

    missing_pairs = declared_pairs - seen_pairs
    missing_rule_refs = expected_rule_refs - projected_rule_refs
    if (
        projection.get("projection_status") == "ready_for_task_planning"
        and missing_rule_refs
    ):
        for node_id, field, statement in sorted(missing_rule_refs):
            errors.append(
                "frozen acceptance rule is not projected: "
                f"{node_id}.{field}: {statement}"
            )
    computed_status = (
        "ready_for_task_planning"
        if not missing_pairs and not missing_rule_refs and not blocking
        else "incomplete"
    )
    if projection.get("projection_status") == "incomplete" and not blocking:
        errors.append("incomplete projection must list blocking_reasons")
    if projection.get("projection_status") != computed_status:
        errors.append(
            f"recomputed projection_status is {computed_status}, "
            f"not {projection.get('projection_status')}"
        )
    return errors


def has_dependency_cycle(graph: dict[str, list[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for dependency in graph.get(node, []):
            if dependency in graph and visit(dependency):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


def validate_output_path(value: Any, path: str, errors: list[str]) -> None:
    if not nonempty_string(value, path, errors):
        return
    if not OUTPUT_PATH_RE.fullmatch(value):
        errors.append(f"{path} must be an absolute path under /tmp")


def validate_task_plan(
    task_plan: Any,
    snapshot: dict[str, Any],
    snapshot_path: Path,
    projection: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    task_plan = exact_object(task_plan, "task_plan", TASK_PLAN_FIELDS, errors)
    if task_plan is None:
        return errors
    if projection.get("projection_status") != "ready_for_task_planning":
        errors.append("task plan requires a ready Check Projection")
    if task_plan.get("schema_version") != TASK_PLAN_VERSION:
        errors.append(f"schema_version must be {TASK_PLAN_VERSION}")
    if task_plan.get("planning_status") not in TASK_PLAN_STATUSES:
        errors.append("planning_status is invalid")
    if task_plan.get("feature") != snapshot.get("feature"):
        errors.append("task_plan.feature does not match snapshot")
    if task_plan.get("snapshot_digest") != snapshot.get("snapshot_digest"):
        errors.append("task_plan.snapshot_digest does not match snapshot_digest")
    if task_plan.get("projection_digest") != digest_json(projection):
        errors.append("task_plan.projection_digest does not match projection_digest")
    blocking = string_list(
        task_plan.get("blocking_reasons"), "blocking_reasons", errors
    )
    if not isinstance(task_plan.get("extensions"), dict):
        errors.append("extensions must be an object")

    declared_repositories = set(snapshot.get("repositories", []))
    declared_lanes = set(snapshot.get("delivery_lanes", []))
    checks_by_repo: dict[str, set[str]] = {
        repository: {
            item["check_id"]
            for item in snapshot.get("required_checks", [])
            if item["repository_id"] == repository
        }
        for repository in declared_repositories
    }
    projections_by_id = {
        item["projection_id"]: item for item in projection.get("projections", [])
    }
    projection_ids = set(projections_by_id)
    hub_root = git_root(snapshot_path.parent)
    if hub_root is None:
        errors.append("snapshot must be inside the hub Git repository")

    packets = task_plan.get("packets")
    if not isinstance(packets, list):
        errors.append("packets must be an array")
        packets = []
    seen_packet_ids: set[str] = set()
    seen_repositories: set[str] = set()
    assigned_projection_ids: set[str] = set()
    dependency_graph: dict[str, list[str]] = {}
    incomplete = False

    for index, packet in enumerate(packets):
        packet_path = f"packets[{index}]"
        packet = exact_object(packet, packet_path, PACKET_FIELDS, errors)
        if packet is None:
            continue
        packet_id = packet.get("packet_id")
        if nonempty_string(packet_id, f"{packet_path}.packet_id", errors):
            if not PACKET_ID_RE.fullmatch(packet_id):
                errors.append(f"{packet_path}.packet_id is invalid")
            if packet_id in seen_packet_ids:
                errors.append(f"duplicate packet_id: {packet_id}")
            seen_packet_ids.add(packet_id)

        repository_id = packet.get("repository_id")
        if nonempty_string(repository_id, f"{packet_path}.repository_id", errors):
            if repository_id not in declared_repositories:
                errors.append(f"{repository_id} is not declared by snapshot")
            if repository_id in seen_repositories:
                errors.append(f"duplicate packet for repository: {repository_id}")
            seen_repositories.add(repository_id)
        delivery_lane = packet.get("delivery_lane")
        if not isinstance(delivery_lane, str) or delivery_lane not in declared_lanes:
            errors.append(f"{packet_path}.delivery_lane is not declared by snapshot")
        nonempty_string(packet.get("base_ref"), f"{packet_path}.base_ref", errors)

        repository_path_value = packet.get("repository_path")
        repository_root: Path | None = None
        if safe_relative_path(
            repository_path_value, f"{packet_path}.repository_path", errors
        ):
            repository_root = (
                hub_root / repository_path_value if hub_root is not None else None
            )
            if repository_root is None or not repository_root.is_dir():
                errors.append(f"{packet_path}.repository_path does not exist")
        guides = string_list(
            packet.get("repo_guides"),
            f"{packet_path}.repo_guides",
            errors,
            allow_empty=False,
        )
        if repository_root is not None:
            for guide_index, relative in enumerate(guides):
                guide_path = f"{packet_path}.repo_guides[{guide_index}]"
                if safe_relative_path(relative, guide_path, errors):
                    if not (repository_root / relative).is_file():
                        errors.append(f"{guide_path} does not exist")
        string_list(
            packet.get("test_seams"),
            f"{packet_path}.test_seams",
            errors,
            allow_empty=False,
        )

        packet_projection_ids = string_list(
            packet.get("projection_ids"),
            f"{packet_path}.projection_ids",
            errors,
        )
        for projection_id in packet_projection_ids:
            item = projections_by_id.get(projection_id)
            if item is None:
                errors.append(f"{projection_id} is not declared by projection")
                continue
            if item["repository_id"] != repository_id:
                errors.append(
                    f"{projection_id} belongs to {item['repository_id']}, "
                    f"not {repository_id}"
                )
            if projection_id in assigned_projection_ids:
                errors.append(f"projection {projection_id} is assigned more than once")
            assigned_projection_ids.add(projection_id)

        packet_checks = set(
            string_list(
                packet.get("required_checks"),
                f"{packet_path}.required_checks",
                errors,
            )
        )
        expected_checks = checks_by_repo.get(str(repository_id), set())
        for check_id in sorted(packet_checks - expected_checks):
            errors.append(
                f"{repository_id}/{check_id} is not declared for repository"
            )
        if expected_checks - packet_checks:
            incomplete = True

        dependencies = string_list(
            packet.get("depends_on_repositories"),
            f"{packet_path}.depends_on_repositories",
            errors,
        )
        for dependency in dependencies:
            if dependency not in declared_repositories:
                errors.append(f"dependency {dependency} is not a snapshot repository")
            if dependency == repository_id:
                errors.append(f"{repository_id} cannot depend on itself")
        if isinstance(repository_id, str):
            dependency_graph[repository_id] = dependencies

        string_list(
            packet.get("cross_repo_contracts"),
            f"{packet_path}.cross_repo_contracts",
            errors,
        )
        string_list(
            packet.get("completion_criteria"),
            f"{packet_path}.completion_criteria",
            errors,
            allow_empty=False,
        )
        string_list(packet.get("notes"), f"{packet_path}.notes", errors)

        evidence_inputs = packet.get("evidence_inputs")
        if not isinstance(evidence_inputs, list):
            errors.append(f"{packet_path}.evidence_inputs must be an array")
            evidence_inputs = []
        evidence_checks: set[str] = set()
        for evidence_index, evidence in enumerate(evidence_inputs):
            evidence_path = f"{packet_path}.evidence_inputs[{evidence_index}]"
            evidence = exact_object(
                evidence, evidence_path, EVIDENCE_INPUT_FIELDS, errors
            )
            if evidence is None:
                continue
            check_id = evidence.get("check_id")
            if not nonempty_string(check_id, f"{evidence_path}.check_id", errors):
                continue
            if check_id in evidence_checks:
                errors.append(f"duplicate evidence input for {repository_id}/{check_id}")
            evidence_checks.add(check_id)
            if check_id not in expected_checks:
                errors.append(
                    f"evidence input {repository_id}/{check_id} is not declared for repository"
                )
            matching = next(
                (
                    item
                    for item in projections_by_id.values()
                    if item["repository_id"] == repository_id
                    and item["check_id"] == check_id
                ),
                None,
            )
            checker_file = evidence.get("checker_file")
            safe_relative_path(
                checker_file, f"{evidence_path}.checker_file", errors
            )
            if matching and checker_file != matching["planned_checker_path"]:
                errors.append(
                    f"{evidence_path}.checker_file does not match planned checker path"
                )
            validate_output_path(
                evidence.get("output_file"), f"{evidence_path}.output_file", errors
            )
        if expected_checks - evidence_checks:
            incomplete = True

    if has_dependency_cycle(dependency_graph):
        errors.append("repository dependency cycle is invalid")
    if declared_repositories - seen_repositories:
        incomplete = True
    if projection_ids - assigned_projection_ids:
        incomplete = True
    computed_status = (
        "ready_for_repository_loops"
        if not incomplete and not blocking
        else "incomplete"
    )
    if task_plan.get("planning_status") != computed_status:
        errors.append(
            f"recomputed planning_status is {computed_status}, "
            f"not {task_plan.get('planning_status')}"
        )
    if task_plan.get("planning_status") == "incomplete" and not blocking:
        errors.append("incomplete task plan must list blocking_reasons")
    return errors


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--snapshot", required=True)
    root.add_argument("--projection", required=True)
    root.add_argument("--task-plan")
    root.add_argument("--require-ready", action="store_true")
    return root


def main() -> int:
    args = parser().parse_args()
    snapshot_path = Path(args.snapshot).resolve()
    projection_path = Path(args.projection).resolve()
    try:
        snapshot = load_verified_snapshot(snapshot_path)
        projection = load_json(projection_path)
        errors = validate_projection(
            projection, projection_path, snapshot, snapshot_path
        )
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return INVALID
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return INVALID
    output = projection
    ready = projection["projection_status"] == "ready_for_task_planning"
    if args.task_plan:
        task_plan_path = Path(args.task_plan).resolve()
        try:
            task_plan = load_json(task_plan_path)
        except ValidationError as exc:
            print(str(exc), file=sys.stderr)
            return INVALID
        task_errors = validate_task_plan(
            task_plan, snapshot, snapshot_path, projection
        )
        if task_errors:
            print("\n".join(task_errors), file=sys.stderr)
            return INVALID
        output = task_plan
        ready = task_plan["planning_status"] == "ready_for_repository_loops"
    if args.require_ready and not ready:
        print("Delivery planning artifact is valid but incomplete", file=sys.stderr)
        return FAIL
    print(digest_json(output))
    return PASS


if __name__ == "__main__":
    raise SystemExit(main())
