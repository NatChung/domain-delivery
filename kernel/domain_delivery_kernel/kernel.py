#!/usr/bin/env python3
"""Strict, deterministic Domain Graph, Snapshot and Evidence plugin kernel."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterable


PASS, FAIL, INVALID, NOT_APPLICABLE = 0, 1, 2, 3
ALLOWED_TYPES = {"authority", "bounded_context", "capability", "contract", "journey", "policy", "question", "term"}
ALLOWED_STATUS = {"candidate", "disputed", "confirmed", "superseded"}
ALLOWED_READINESS = {"L0", "L1", "L2", "L3"}
SHAPED_TYPES = {"bounded_context", "capability", "contract", "journey", "policy"}
EXECUTABLE_TYPES = {"bounded_context", "capability", "contract", "journey", "policy"}
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ID_RE = re.compile(r"^[a-z_]+:[a-z0-9][a-z0-9._-]*$")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
COMMIT_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
IDENTITY_RE = re.compile(r"^[a-z][a-z0-9_-]*:[A-Za-z0-9][A-Za-z0-9._-]*$")
NODE_FIELDS = {
    "id", "type", "title", "status", "readiness", "authority", "sources",
    "scope", "out_of_scope", "open_questions", "blocking_questions",
    "preconditions", "postconditions", "invariants", "invalid_cases",
    "requires", "related_nodes", "confirmed_by", "confirmed_at",
    "confirmation_source", "source_path", "body", "content_digest",
}


class KernelError(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def digest_json(value: Any) -> str:
    return digest_bytes(canonical(value))


def strict_json_loads(text: str, source: str) -> Any:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise KernelError(f"{source}: duplicate JSON key {key!r}")
            value[key] = item
        return value

    try:
        return json.loads(text, object_pairs_hook=reject_duplicates)
    except json.JSONDecodeError as exc:
        raise KernelError(f"{source}: invalid JSON: {exc}") from exc


def parse_scalar(raw: str) -> Any:
    raw = raw.strip()
    if not raw:
        return ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        lowered = raw.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered in {"null", "~"}:
            return None
        return raw.strip("'\"")


def parse_markdown_text(text: str, source_path: str) -> dict[str, Any] | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise KernelError(f"{source_path}: front matter is not closed") from exc
    metadata: dict[str, Any] = {}
    for number, line in enumerate(lines[1:end], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise KernelError(f"{source_path}:{number}: expected key: value")
        key, raw = line.split(":", 1)
        key = key.strip()
        if key in metadata:
            raise KernelError(f"{source_path}:{number}: duplicate key {key}")
        metadata[key] = parse_scalar(raw)
    metadata["source_path"] = source_path
    metadata["body"] = "\n".join(lines[end + 1 :]).strip() + "\n"
    metadata["content_digest"] = digest_bytes(text.encode())
    return metadata


def parse_markdown(path: Path, root: Path) -> dict[str, Any] | None:
    source_path = path.relative_to(root).as_posix()
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise KernelError(f"{source_path}: Markdown is not UTF-8") from exc
    return parse_markdown_text(text, source_path)


def iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        dt.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def iso_datetime(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None
    except ValueError:
        return False


def string_list(
    node: dict[str, Any],
    field: str,
    source: str,
    errors: list[str],
    *,
    required: bool = False,
    nonempty: bool = False,
) -> list[str]:
    def report(message: str) -> None:
        if message not in errors:
            errors.append(message)

    value = node.get(field)
    if field not in node and not required:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        report(f"{source}: {field} must be a list of non-empty strings")
        return []
    if len(value) != len(set(value)):
        report(f"{source}: {field} must not contain duplicates")
    if nonempty and not value:
        report(f"{source}: {field} must not be empty")
    return value


def valid_unique_strings(value: Any, pattern: re.Pattern[str]) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and bool(pattern.fullmatch(item)) for item in value)
        and len(value) == len(set(value))
    )


def validate_node_shape(node: Any) -> list[str]:
    if not isinstance(node, dict):
        return ["node must be an object"]
    source = str(node.get("source_path", "<unknown>"))
    errors: list[str] = []
    unknown = set(node) - NODE_FIELDS
    if unknown:
        errors.append(f"{source}: unknown fields: {', '.join(sorted(unknown))}")
    for field in ("id", "type", "status", "readiness", "title", "source_path", "body", "content_digest"):
        if not isinstance(node.get(field), str) or not node.get(field):
            errors.append(f"{source}: missing or invalid {field}")
    if isinstance(node.get("id"), str) and not ID_RE.fullmatch(node["id"]):
        errors.append(f"{source}: invalid id {node['id']!r}")
    if node.get("type") not in ALLOWED_TYPES:
        errors.append(f"{source}: invalid type {node.get('type')!r}")
    elif isinstance(node.get("id"), str) and node["id"].split(":", 1)[0] != node["type"]:
        errors.append(f"{source}: id namespace must match type")
    if node.get("status") not in ALLOWED_STATUS:
        errors.append(f"{source}: invalid status {node.get('status')!r}")
    if node.get("readiness") not in ALLOWED_READINESS:
        errors.append(f"{source}: invalid readiness {node.get('readiness')!r}")
    if isinstance(node.get("content_digest"), str) and not DIGEST_RE.fullmatch(node["content_digest"]):
        errors.append(f"{source}: invalid content_digest")
    list_fields = {
        "sources", "scope", "out_of_scope", "open_questions",
        "blocking_questions", "preconditions", "postconditions",
        "invariants", "invalid_cases", "requires", "related_nodes",
    }
    for field in sorted(list_fields):
        if field in node:
            string_list(node, field, source, errors)
    if "authority" in node:
        authority = node["authority"]
        if not isinstance(authority, str) or (authority != "unknown" and not re.fullmatch(r"authority:[a-z0-9][a-z0-9._-]*", authority)):
            errors.append(f"{source}: authority must be unknown or an authority node ID")
    if "confirmed_by" in node and (not isinstance(node["confirmed_by"], str) or not node["confirmed_by"] or node["confirmed_by"].startswith("agent:")):
        errors.append(f"{source}: confirmed_by must name a non-agent human/role")
    if "confirmed_at" in node and not iso_date(node["confirmed_at"]):
        errors.append(f"{source}: confirmed_at must be an ISO date")
    if "confirmation_source" in node and (not isinstance(node["confirmation_source"], str) or not node["confirmation_source"]):
        errors.append(f"{source}: confirmation_source must be a non-empty string")
    readiness = node.get("readiness")
    if readiness in {"L1", "L2", "L3"}:
        string_list(node, "sources", source, errors, required=True, nonempty=True)
    if readiness in {"L2", "L3"} and node.get("type") in SHAPED_TYPES:
        string_list(node, "scope", source, errors, required=True, nonempty=True)
        string_list(node, "out_of_scope", source, errors, required=True)
        string_list(node, "open_questions", source, errors, required=True)
    if readiness == "L3":
        if node.get("status") != "confirmed":
            errors.append(f"{source}: L3 requires confirmed status")
        if string_list(node, "blocking_questions", source, errors, required=True):
            errors.append(f"{source}: L3 cannot have blocking_questions")
        if node.get("type") in EXECUTABLE_TYPES:
            for field in ("preconditions", "postconditions", "invariants", "invalid_cases"):
                string_list(node, field, source, errors, required=True, nonempty=True)
    for field in ("requires", "related_nodes"):
        for reference in string_list(node, field, source, errors):
            if not ID_RE.fullmatch(reference):
                errors.append(f"{source}: invalid {field} reference {reference!r}")
    if node.get("status") == "confirmed":
        if "confirmed_by" not in node:
            errors.append(f"{source}: confirmed_by must name a non-agent human/role")
        if "confirmed_at" not in node:
            errors.append(f"{source}: confirmed_at must be an ISO date")
        if "confirmation_source" not in node:
            errors.append(f"{source}: confirmed node missing confirmation_source")
        if node.get("type") == "authority":
            string_list(node, "scope", source, errors, required=True, nonempty=True)
        elif not isinstance(node.get("authority"), str) or node.get("authority") in {"", "unknown"}:
            errors.append(f"{source}: confirmed node requires a typed authority reference")
    return errors


def authority_covers(authority: dict[str, Any], node_id: str) -> bool:
    for scope in authority.get("scope", []):
        if scope == "*" or scope == node_id:
            return True
        if scope.endswith(":*") and node_id.startswith(scope[:-1]):
            return True
    return False


def validate_index(index: Any) -> list[str]:
    if not isinstance(index, dict):
        return ["index must be an object"]
    errors: list[str] = []
    if set(index) != {"schema_version", "source_root", "nodes", "index_digest"}:
        errors.append("index has missing or unknown top-level fields")
    if index.get("schema_version") != 1:
        errors.append("index schema_version must be 1")
    source_root = index.get("source_root")
    if (
        not isinstance(source_root, str)
        or not source_root
        or Path(source_root).is_absolute()
        or ".." in Path(source_root).parts
    ):
        errors.append("index source_root must be a non-empty string")
    nodes = index.get("nodes")
    if not isinstance(nodes, list):
        return errors + ["index nodes must be an array"]
    expected = index.get("index_digest")
    unsigned = {key: value for key, value in index.items() if key != "index_digest"}
    if expected != digest_json(unsigned):
        errors.append("index digest does not match content")
    by_id: dict[str, dict[str, Any]] = {}
    for node in nodes:
        errors.extend(validate_node_shape(node))
        if isinstance(node, dict) and isinstance(node.get("id"), str):
            if node["id"] in by_id:
                errors.append(f"duplicate node id: {node['id']}")
            by_id[node["id"]] = node
    for node_id, node in by_id.items():
        source = node.get("source_path", node_id)
        for field in ("requires", "related_nodes"):
            for reference in node.get(field, []) if isinstance(node.get(field, []), list) else []:
                if reference not in by_id:
                    errors.append(f"{source}: unknown {field} reference {reference}")
        if node.get("status") == "confirmed" and node.get("type") != "authority":
            authority_id = node.get("authority")
            authority = by_id.get(authority_id)
            if not authority or authority.get("type") != "authority":
                errors.append(f"{source}: authority does not resolve to an authority node")
            elif authority.get("status") != "confirmed" or authority.get("readiness") != "L3":
                errors.append(f"{source}: authority must be confirmed L3")
            elif not authority_covers(authority, node_id):
                errors.append(f"{source}: authority scope does not cover {node_id}")
    return errors


def git_root(path: Path) -> Path | None:
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=path, text=True, capture_output=True)
    return Path(result.stdout.strip()) if result.returncode == 0 else None


def compile_graph(source: Path) -> dict[str, Any]:
    source = source.resolve()
    root = git_root(source)
    source_root = source.relative_to(root).as_posix() if root and source.is_relative_to(root) else "."
    nodes: list[dict[str, Any]] = []
    for path in sorted(source.rglob("*.md")):
        node = parse_markdown(path, source)
        if node is not None:
            nodes.append(node)
    nodes.sort(key=lambda item: str(item.get("id", "")))
    index: dict[str, Any] = {"schema_version": 1, "source_root": source_root, "nodes": nodes}
    index["index_digest"] = digest_json(index)
    errors = validate_index(index)
    if errors:
        raise KernelError("\n".join(errors))
    return index


def load_json(path: Path) -> Any:
    try:
        text = path.read_bytes().decode("utf-8")
        return strict_json_loads(text, str(path))
    except (OSError, UnicodeDecodeError) as exc:
        raise KernelError(f"cannot read {path}: {exc}") from exc


def closure(index: dict[str, Any], roots: Iterable[str]) -> list[dict[str, Any]]:
    by_id = {node["id"]: node for node in index["nodes"]}
    root_ids = sorted(set(roots))
    if not root_ids:
        raise KernelError("snapshot requires at least one root node")
    if not any(by_id.get(node_id, {}).get("type") in {"capability", "journey"} for node_id in root_ids):
        raise KernelError("snapshot requires a capability or journey root")
    pending = list(root_ids)
    selected: dict[str, dict[str, Any]] = {}
    while pending:
        node_id = pending.pop()
        node = by_id.get(node_id)
        if node is None:
            raise KernelError(f"unknown node: {node_id}")
        if node_id in selected:
            continue
        if node.get("status") != "confirmed" or node.get("readiness") != "L3":
            raise KernelError(f"{node_id}: snapshot requires confirmed L3, got {node.get('status')} {node.get('readiness')}")
        selected[node_id] = node
        dependencies = list(node.get("requires", []))
        if node.get("type") != "authority":
            dependencies.append(node["authority"])
        pending.extend(dependencies)
    return [selected[node_id] for node_id in sorted(selected)]


def parse_required_checks(values: Iterable[str], trusted_attestors: Iterable[str]) -> list[dict[str, Any]]:
    attestor_values = list(trusted_attestors)
    if not attestor_values or any(not isinstance(item, str) or not IDENTITY_RE.fullmatch(item) for item in attestor_values):
        raise KernelError("snapshot requires at least one valid trusted attestor identity")
    attestors = sorted(set(attestor_values))
    checks: list[dict[str, Any]] = []
    for value in values:
        if "/" not in value:
            raise KernelError(f"required check must be repository/check: {value}")
        repository_id, check_id = value.split("/", 1)
        if not NAME_RE.fullmatch(repository_id) or not NAME_RE.fullmatch(check_id):
            raise KernelError(f"invalid required check: {value}")
        checks.append({"repository_id": repository_id, "check_id": check_id, "trusted_attestors": attestors})
    if not checks:
        raise KernelError("snapshot requires at least one repository-scoped check")
    checks.sort(key=lambda item: (item["repository_id"], item["check_id"]))
    if len({(item["repository_id"], item["check_id"]) for item in checks}) != len(checks):
        raise KernelError("duplicate required check")
    return checks


def render_domain_bundle(feature: str, version: str, graph_commit: str, nodes: list[dict[str, Any]]) -> str:
    parts = [f"# {feature} Feature Snapshot {version}", "", f"Graph commit: `{graph_commit}`", ""]
    for node in nodes:
        semantic_fields = {
            key: value
            for key, value in node.items()
            if key not in {"body", "source_path", "content_digest"}
        }
        parts.extend([
            f"## {node['title']}", "", f"- ID: `{node['id']}`", f"- Type: `{node['type']}`",
            f"- Source: `{node['source_path']}`", f"- Content digest: `{node['content_digest']}`", "",
            "### Frozen semantic fields", "", "```json",
            json.dumps(semantic_fields, ensure_ascii=False, indent=2, sort_keys=True),
            "```", "", "### Meaning", "", node["body"].rstrip(), "",
        ])
    return "\n".join(parts).rstrip() + "\n"


def freeze_snapshot(
    feature: str,
    version: str,
    index: dict[str, Any],
    root_ids: Iterable[str],
    delivery_lanes: Iterable[str],
    repositories: Iterable[str],
    required_checks: list[dict[str, Any]],
    graph_commit: str,
    supersedes: str | None = None,
) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    errors = validate_index(index)
    if errors:
        raise KernelError("\n".join(errors))
    if not isinstance(feature, str) or not NAME_RE.fullmatch(feature):
        raise KernelError("feature must be a lowercase identifier")
    if not isinstance(version, str) or not NAME_RE.fullmatch(version):
        raise KernelError("snapshot version must be a lowercase identifier")
    if not isinstance(graph_commit, str) or not COMMIT_RE.fullmatch(graph_commit):
        raise KernelError("graph_commit must be a 7-64 character lowercase hex commit")
    lane_values = list(delivery_lanes)
    repo_values = list(repositories)
    if not lane_values or any(not isinstance(item, str) or not NAME_RE.fullmatch(item) for item in lane_values):
        raise KernelError("snapshot requires valid delivery lanes")
    if not repo_values or any(not isinstance(item, str) or not NAME_RE.fullmatch(item) for item in repo_values):
        raise KernelError("snapshot requires valid repository IDs")
    lanes = sorted(set(lane_values))
    repos = sorted(set(repo_values))
    check_values = list(required_checks)
    if not check_values:
        raise KernelError("snapshot requires at least one repository-scoped check")
    normalized_checks: list[dict[str, Any]] = []
    check_repos: set[str] = set()
    for check in check_values:
        if not isinstance(check, dict) or set(check) != {"repository_id", "check_id", "trusted_attestors"}:
            raise KernelError("required check shape is invalid")
        repository_id = check.get("repository_id")
        check_id = check.get("check_id")
        attestors = check.get("trusted_attestors")
        if repository_id not in repos:
            raise KernelError(f"required check references undeclared repository: {repository_id}")
        if not isinstance(check_id, str) or not NAME_RE.fullmatch(check_id):
            raise KernelError(f"required check has invalid check ID: {check_id}")
        if not valid_unique_strings(attestors, IDENTITY_RE):
            raise KernelError(f"required check has invalid trusted attestors: {repository_id}/{check_id}")
        check_repos.add(repository_id)
        normalized_checks.append({
            "repository_id": repository_id,
            "check_id": check_id,
            "trusted_attestors": sorted(attestors),
        })
    normalized_checks.sort(key=lambda item: (item["repository_id"], item["check_id"]))
    if len({(item["repository_id"], item["check_id"]) for item in normalized_checks}) != len(normalized_checks):
        raise KernelError("duplicate required check")
    uncovered = sorted(set(repos) - check_repos)
    if uncovered:
        raise KernelError(f"repositories without required checks: {', '.join(uncovered)}")
    selected = closure(index, root_ids)
    bundle = render_domain_bundle(feature, version, graph_commit, selected)
    payload_digest = digest_json(selected)
    snapshot: dict[str, Any] = {
        "schema_version": 1,
        "feature": feature,
        "snapshot_version": version,
        "state": "frozen",
        "graph_commit": graph_commit,
        "graph_source_root": index["source_root"],
        "graph_index_digest": index["index_digest"],
        "root_nodes": sorted(set(root_ids)),
        "nodes": [{key: node[key] for key in ("id", "type", "source_path", "content_digest")} for node in selected],
        "delivery_lanes": lanes,
        "repositories": repos,
        "required_checks": normalized_checks,
        "domain_bundle": {
            "path": "DOMAIN.md",
            "digest": digest_bytes(bundle.encode()),
            "payload_path": "domain-payload.json",
            "payload_digest": payload_digest,
        },
    }
    if supersedes:
        if not DIGEST_RE.fullmatch(supersedes):
            raise KernelError("supersedes must be a snapshot sha256 digest")
        snapshot["supersedes"] = supersedes
    snapshot["snapshot_digest"] = digest_json(snapshot)
    errors = validate_snapshot(snapshot)
    if errors:
        raise KernelError("\n".join(errors))
    return snapshot, bundle, selected


def validate_snapshot(snapshot: Any, manifest_path: Path | None = None) -> list[str]:
    if not isinstance(snapshot, dict):
        return ["snapshot must be an object"]
    required = {"schema_version", "feature", "snapshot_version", "state", "graph_commit", "graph_source_root", "graph_index_digest", "root_nodes", "nodes", "delivery_lanes", "repositories", "required_checks", "domain_bundle", "snapshot_digest"}
    allowed = required | {"supersedes"}
    errors: list[str] = []
    if set(snapshot) - allowed or required - set(snapshot):
        errors.append("snapshot has missing or unknown fields")
    if snapshot.get("schema_version") != 1 or snapshot.get("state") != "frozen":
        errors.append("snapshot schema/state is invalid")
    if not isinstance(snapshot.get("feature"), str) or not NAME_RE.fullmatch(snapshot.get("feature", "")):
        errors.append("snapshot feature is invalid")
    if not isinstance(snapshot.get("snapshot_version"), str) or not NAME_RE.fullmatch(snapshot.get("snapshot_version", "")):
        errors.append("snapshot_version is invalid")
    if not COMMIT_RE.fullmatch(str(snapshot.get("graph_commit", ""))):
        errors.append("graph_commit is invalid")
    graph_source_root = snapshot.get("graph_source_root")
    if not isinstance(graph_source_root, str) or not graph_source_root or Path(graph_source_root).is_absolute() or ".." in Path(graph_source_root).parts:
        errors.append("graph_source_root is invalid")
    if not DIGEST_RE.fullmatch(str(snapshot.get("graph_index_digest", ""))):
        errors.append("graph_index_digest is invalid")

    nodes = snapshot.get("nodes")
    pinned_by_id: dict[str, dict[str, Any]] = {}
    if not isinstance(nodes, list) or not nodes:
        errors.append("snapshot has no domain nodes")
        nodes = []
    for node in nodes:
        if not isinstance(node, dict) or set(node) != {"id", "type", "source_path", "content_digest"}:
            errors.append("snapshot domain node shape is invalid")
            continue
        node_id = node.get("id")
        if not isinstance(node_id, str) or not ID_RE.fullmatch(node_id):
            errors.append("snapshot domain node ID is invalid")
            continue
        if node_id in pinned_by_id:
            errors.append(f"duplicate snapshot domain node: {node_id}")
        pinned_by_id[node_id] = node
        if node.get("type") not in ALLOWED_TYPES:
            errors.append(f"snapshot domain node type is invalid: {node_id}")
        if not isinstance(node.get("source_path"), str) or not node["source_path"] or node["source_path"].startswith("/") or ".." in Path(node["source_path"]).parts:
            errors.append(f"snapshot domain node path is invalid: {node_id}")
        if not DIGEST_RE.fullmatch(str(node.get("content_digest", ""))):
            errors.append(f"snapshot domain node digest is invalid: {node_id}")

    roots = snapshot.get("root_nodes")
    if not isinstance(roots, list) or not roots:
        errors.append("snapshot has no root nodes")
        roots = []
    elif not valid_unique_strings(roots, ID_RE):
        errors.append("snapshot root nodes are invalid or duplicated")
    for root in roots:
        if root not in pinned_by_id:
            errors.append(f"snapshot root is not pinned: {root}")
    if roots and not any(pinned_by_id.get(root, {}).get("type") in {"capability", "journey"} for root in roots):
        errors.append("snapshot requires a capability or journey root")

    repos = snapshot.get("repositories")
    checks = snapshot.get("required_checks")
    if not valid_unique_strings(repos, NAME_RE):
        errors.append("snapshot has no repositories")
        repos = []
    lanes = snapshot.get("delivery_lanes")
    if not valid_unique_strings(lanes, NAME_RE):
        errors.append("snapshot delivery lanes are invalid")
    if not isinstance(checks, list) or not checks:
        errors.append("snapshot has no required checks")
        checks = []
    seen: set[tuple[str, str]] = set()
    checked_repos: set[str] = set()
    for check in checks:
        if not isinstance(check, dict) or set(check) != {"repository_id", "check_id", "trusted_attestors"}:
            errors.append("required check shape is invalid")
            continue
        repository_id = check.get("repository_id")
        check_id = check.get("check_id")
        if not isinstance(repository_id, str) or not isinstance(check_id, str):
            errors.append("required check repository/check ID must be strings")
            continue
        key = (repository_id, check_id)
        if key in seen:
            errors.append(f"duplicate required check: {key[0]}/{key[1]}")
        seen.add(key)
        if repository_id not in repos or not NAME_RE.fullmatch(repository_id) or not NAME_RE.fullmatch(check_id):
            errors.append(f"invalid required check: {key[0]}/{key[1]}")
        else:
            checked_repos.add(repository_id)
        attestors = check.get("trusted_attestors")
        if not valid_unique_strings(attestors, IDENTITY_RE):
            errors.append(f"required check has no trusted attestor: {key[0]}/{key[1]}")
    for repository_id in sorted(set(repos) - checked_repos):
        errors.append(f"repository has no required check: {repository_id}")

    bundle = snapshot.get("domain_bundle")
    if (
        not isinstance(bundle, dict)
        or set(bundle) != {"path", "digest", "payload_path", "payload_digest"}
        or bundle.get("path") != "DOMAIN.md"
        or bundle.get("payload_path") != "domain-payload.json"
        or not DIGEST_RE.fullmatch(str(bundle.get("digest", "")))
        or not DIGEST_RE.fullmatch(str(bundle.get("payload_digest", "")))
    ):
        errors.append("domain bundle declaration is invalid")
    elif manifest_path:
        bundle_path = manifest_path.parent / bundle["path"]
        payload_path = manifest_path.parent / bundle["payload_path"]
        try:
            bundle_bytes = bundle_path.read_bytes()
            if digest_bytes(bundle_bytes) != bundle["digest"]:
                errors.append("domain bundle digest mismatch")
            payload = load_json(payload_path)
            if digest_json(payload) != bundle["payload_digest"]:
                errors.append("domain payload digest mismatch")
            if not isinstance(payload, list) or not payload:
                errors.append("domain payload is empty or invalid")
            else:
                payload_errors = [error for node in payload for error in validate_node_shape(node)]
                errors.extend(f"domain payload: {error}" for error in payload_errors)
                payload_projection = [
                    {key: node.get(key) for key in ("id", "type", "source_path", "content_digest")}
                    for node in payload if isinstance(node, dict)
                ]
                if payload_projection != nodes:
                    errors.append("domain payload does not match snapshot closure")
                if not payload_errors and all(isinstance(node, dict) for node in payload):
                    payload_by_id = {node["id"]: node for node in payload}
                    if len(payload_by_id) != len(payload):
                        errors.append("domain payload contains duplicate nodes")
                    for node in payload:
                        if node.get("status") != "confirmed" or node.get("readiness") != "L3":
                            errors.append(f"domain payload node is not confirmed L3: {node['id']}")
                        dependencies = list(node.get("requires", []))
                        if node.get("type") != "authority":
                            authority_id = node.get("authority")
                            dependencies.append(authority_id)
                            authority = payload_by_id.get(authority_id)
                            if not authority or authority.get("type") != "authority" or not authority_covers(authority, node["id"]):
                                errors.append(f"domain payload authority does not cover {node['id']}")
                        for dependency in dependencies:
                            if dependency not in payload_by_id:
                                errors.append(f"domain payload closure is missing {dependency} required by {node['id']}")
                    expected_bundle = render_domain_bundle(
                        str(snapshot.get("feature", "")),
                        str(snapshot.get("snapshot_version", "")),
                        str(snapshot.get("graph_commit", "")),
                        payload,
                    ).encode()
                    if expected_bundle != bundle_bytes:
                        errors.append("domain bundle is not the rendering of its payload")
        except (OSError, KernelError) as exc:
            errors.append(f"cannot read domain bundle: {exc}")
    expected = snapshot.get("snapshot_digest")
    unsigned = {key: value for key, value in snapshot.items() if key != "snapshot_digest"}
    if expected != digest_json(unsigned):
        errors.append("snapshot digest does not match content")
    if snapshot.get("supersedes") and not DIGEST_RE.fullmatch(str(snapshot["supersedes"])):
        errors.append("supersedes digest is invalid")
    return errors


def reconstruct_index_at_commit(source_root_value: str, commit: str, cwd: Path) -> dict[str, Any]:
    if not isinstance(source_root_value, str) or not source_root_value or Path(source_root_value).is_absolute() or ".." in Path(source_root_value).parts:
        raise KernelError("graph source root is invalid")
    if not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit):
        raise KernelError("graph commit must be a full 40- or 64-character object ID")
    root = git_root(cwd)
    if root is None:
        raise KernelError("snapshot verification requires the Domain Graph Git repository")
    exists = subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=root, capture_output=True)
    if exists.returncode != 0:
        raise KernelError(f"graph commit does not exist: {commit}")
    source_root = source_root_value.rstrip("/") or "."
    tree_args = ["git", "ls-tree", "-r", "-z", "--name-only", commit, "--"]
    if source_root != ".":
        tree_args.append(source_root)
    tree = subprocess.run(tree_args, cwd=root, capture_output=True)
    if tree.returncode != 0:
        raise KernelError(f"cannot enumerate graph at commit {commit}")
    reconstructed_nodes: list[dict[str, Any]] = []
    prefix = "" if source_root == "." else source_root + "/"
    for raw_path in tree.stdout.split(b"\0"):
        if not raw_path:
            continue
        try:
            repository_path = raw_path.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise KernelError("graph path is not UTF-8") from exc
        if not repository_path.endswith(".md"):
            continue
        relative_path = repository_path[len(prefix):] if prefix else repository_path
        result = subprocess.run(["git", "show", f"{commit}:{repository_path}"], cwd=root, capture_output=True)
        if result.returncode != 0:
            raise KernelError(f"cannot read graph source at {commit}: {repository_path}")
        try:
            text = result.stdout.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise KernelError(f"graph source is not UTF-8: {repository_path}") from exc
        node = parse_markdown_text(text, relative_path)
        if node is not None:
            reconstructed_nodes.append(node)
    reconstructed_nodes.sort(key=lambda item: item["id"])
    reconstructed: dict[str, Any] = {
        "schema_version": 1,
        "source_root": source_root_value,
        "nodes": reconstructed_nodes,
    }
    reconstructed["index_digest"] = digest_json(reconstructed)
    reconstructed_errors = validate_index(reconstructed)
    if reconstructed_errors:
        raise KernelError("graph at pinned commit is invalid:\n" + "\n".join(reconstructed_errors))
    return reconstructed


def verify_index_at_commit(index: dict[str, Any], commit: str, cwd: Path) -> None:
    errors = validate_index(index)
    if errors:
        raise KernelError("\n".join(errors))
    reconstructed = reconstruct_index_at_commit(index["source_root"], commit, cwd)
    if index != reconstructed:
        raise KernelError("graph index is not the deterministic index of the pinned commit")


def verify_snapshot_against_graph(snapshot: dict[str, Any], manifest_path: Path) -> list[str]:
    errors = validate_snapshot(snapshot, manifest_path)
    if errors:
        return errors
    try:
        reconstructed = reconstruct_index_at_commit(
            snapshot["graph_source_root"], snapshot["graph_commit"], manifest_path.parent,
        )
        if reconstructed["index_digest"] != snapshot["graph_index_digest"]:
            errors.append("snapshot graph index digest does not match pinned commit")
        expected_payload = closure(reconstructed, snapshot["root_nodes"])
        actual_payload = load_json(manifest_path.parent / snapshot["domain_bundle"]["payload_path"])
        if actual_payload != expected_payload:
            errors.append("snapshot payload is not the exact root dependency closure at the pinned commit")
    except KernelError as exc:
        errors.append(str(exc))
    return errors


def publish_snapshot(output: Path, snapshot: dict[str, Any], bundle: str, payload: list[dict[str, Any]]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    reserved = False
    try:
        domain_path = temp / "DOMAIN.md"
        payload_path = temp / "domain-payload.json"
        manifest_path = temp / "snapshot-manifest.json"
        domain_path.write_text(bundle, encoding="utf-8")
        payload_path.write_bytes(canonical(payload))
        manifest_path.write_bytes(canonical(snapshot))
        for path in (domain_path, payload_path, manifest_path):
            with path.open("rb") as stream:
                os.fsync(stream.fileno())
        try:
            output.mkdir()
            reserved = True
        except FileExistsError as exc:
            raise KernelError(f"snapshot output already exists and is immutable: {output}") from exc
        for path in (domain_path, payload_path, manifest_path):
            os.rename(path, output / path.name)
        for directory in (output, output.parent):
            descriptor = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        temp.rmdir()
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        if reserved:
            shutil.rmtree(output, ignore_errors=True)
        raise


def detect_drift(snapshot: dict[str, Any], index: dict[str, Any]) -> list[str]:
    errors = validate_snapshot(snapshot) + validate_index(index)
    if errors:
        raise KernelError("\n".join(errors))
    current = {node["id"]: node for node in index["nodes"]}
    drift: list[str] = []
    if snapshot["graph_index_digest"] != index["index_digest"]:
        drift.append("global index changed")
    for pinned in snapshot["nodes"]:
        node = current.get(pinned["id"])
        if node is None:
            drift.append(f"selected node removed: {pinned['id']}")
        elif node["content_digest"] != pinned["content_digest"]:
            drift.append(f"selected node changed: {pinned['id']}")
    return drift


RESULT_FIELDS = {"schema_version", "kind", "snapshot_digest", "repository_id", "check_id", "exit_code", "checker_digest", "repo_commit", "repo_state_digest", "output_digest", "performed_by", "recorded_at", "previous_hash", "entry_hash"}
ATTEST_FIELDS = {"schema_version", "kind", "snapshot_digest", "result_entry_hash", "declared_by", "declaration_mode", "artifact_digest", "recorded_at", "previous_hash", "entry_hash"}


def validate_entry_shape(entry: Any, number: int) -> list[str]:
    prefix = f"entry {number}"
    if not isinstance(entry, dict):
        return [f"{prefix}: must be an object"]
    errors: list[str] = []
    fields = RESULT_FIELDS if entry.get("kind") == "result" else ATTEST_FIELDS if entry.get("kind") == "attestation" else set()
    if not fields or set(entry) != fields:
        errors.append(f"{prefix}: missing or unknown fields")
    if entry.get("schema_version") != 1:
        errors.append(f"{prefix}: schema_version must be 1")
    for field in ("snapshot_digest", "entry_hash"):
        if not DIGEST_RE.fullmatch(str(entry.get(field, ""))):
            errors.append(f"{prefix}: invalid {field}")
    previous = entry.get("previous_hash")
    if previous is not None and not DIGEST_RE.fullmatch(str(previous)):
        errors.append(f"{prefix}: invalid previous_hash")
    if not iso_datetime(entry.get("recorded_at")):
        errors.append(f"{prefix}: recorded_at must include timezone")
    if entry.get("kind") == "result":
        if not NAME_RE.fullmatch(str(entry.get("repository_id", ""))) or not NAME_RE.fullmatch(str(entry.get("check_id", ""))):
            errors.append(f"{prefix}: invalid repository/check ID")
        if entry.get("exit_code") not in {PASS, FAIL, INVALID, NOT_APPLICABLE}:
            errors.append(f"{prefix}: invalid exit code")
        for field in ("checker_digest", "repo_state_digest", "output_digest"):
            if not DIGEST_RE.fullmatch(str(entry.get(field, ""))):
                errors.append(f"{prefix}: invalid {field}")
        if not COMMIT_RE.fullmatch(str(entry.get("repo_commit", ""))):
            errors.append(f"{prefix}: invalid repo_commit")
        if not isinstance(entry.get("performed_by"), str) or not IDENTITY_RE.fullmatch(entry.get("performed_by", "")):
            errors.append(f"{prefix}: invalid performed_by")
    elif entry.get("kind") == "attestation":
        if not DIGEST_RE.fullmatch(str(entry.get("result_entry_hash", ""))) or not DIGEST_RE.fullmatch(str(entry.get("artifact_digest", ""))):
            errors.append(f"{prefix}: invalid attestation digest/reference")
        if entry.get("declaration_mode") not in {"ci_declaration", "signature_declaration", "human_declaration"}:
            errors.append(f"{prefix}: invalid declaration_mode")
        if not isinstance(entry.get("declared_by"), str) or not IDENTITY_RE.fullmatch(entry.get("declared_by", "")):
            errors.append(f"{prefix}: invalid declared_by")
    return errors


def parse_ledger_text(text: str, source: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        value = strict_json_loads(line, f"{source}:{number}")
        entries.append(value)
    return entries


def validate_ledger(snapshot: dict[str, Any], entries: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    previous_hash = None
    result_entries: dict[str, dict[str, Any]] = {}
    for number, entry in enumerate(entries, start=1):
        errors.extend(validate_entry_shape(entry, number))
        if not isinstance(entry, dict):
            continue
        unsigned = {key: value for key, value in entry.items() if key != "entry_hash"}
        if entry.get("entry_hash") != digest_json(unsigned):
            errors.append(f"entry {number}: digest mismatch")
        if entry.get("previous_hash") != previous_hash:
            errors.append(f"entry {number}: chain mismatch")
        if entry.get("snapshot_digest") != snapshot.get("snapshot_digest"):
            errors.append(f"entry {number}: wrong snapshot")
        if entry.get("kind") == "result" and DIGEST_RE.fullmatch(str(entry.get("entry_hash", ""))):
            result_entries[entry["entry_hash"]] = entry
        if entry.get("kind") == "attestation" and entry.get("result_entry_hash") not in result_entries:
            errors.append(f"entry {number}: attestation does not reference a prior result")
        previous_hash = entry.get("entry_hash")
    return errors


def load_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise KernelError(f"cannot read {path}: {exc}") from exc
    return parse_ledger_text(text, str(path))


def append_locked(path: Path, snapshot: dict[str, Any], builder: Callable[[list[dict[str, Any]]], dict[str, Any]]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        stream.seek(0)
        try:
            text = stream.read().decode("utf-8")
        except UnicodeDecodeError as exc:
            raise KernelError(f"cannot read {path}: {exc}") from exc
        entries = parse_ledger_text(text, str(path))
        errors = validate_ledger(snapshot, entries)
        if errors:
            raise KernelError("refusing to append to invalid ledger:\n" + "\n".join(errors))
        entry = builder(entries)
        entry["previous_hash"] = entries[-1]["entry_hash"] if entries else None
        entry["entry_hash"] = digest_json(entry)
        shape_errors = validate_entry_shape(entry, len(entries) + 1)
        if shape_errors:
            raise KernelError("\n".join(shape_errors))
        ledger_errors = validate_ledger(snapshot, entries + [entry])
        if ledger_errors:
            raise KernelError("\n".join(ledger_errors))
        stream.seek(0, os.SEEK_END)
        stream.write(canonical(entry))
        stream.flush()
        os.fsync(stream.fileno())
        return entry


def repo_state(repo: Path) -> tuple[str, str]:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, text=True, capture_output=True)
    if commit.returncode != 0 or not COMMIT_RE.fullmatch(commit.stdout.strip()):
        raise KernelError(f"not a Git repository: {repo}")
    status = subprocess.run(["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=repo, capture_output=True, check=True).stdout
    diff = subprocess.run(["git", "diff", "--binary", "HEAD"], cwd=repo, capture_output=True, check=True).stdout
    untracked = bytearray()
    for record in status.split(b"\0"):
        if record.startswith(b"?? "):
            relative = record[3:].decode(errors="surrogateescape")
            path = repo / relative
            if path.is_file():
                untracked.extend(relative.encode(errors="surrogateescape") + b"\0" + digest_bytes(path.read_bytes()).encode() + b"\0")
    return commit.stdout.strip(), digest_bytes(status + b"\0" + diff + b"\0" + bytes(untracked))


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def verify_evidence(snapshot: dict[str, Any], entries: list[dict[str, Any]]) -> list[str]:
    errors = validate_snapshot(snapshot) + validate_ledger(snapshot, entries)
    if errors:
        return errors
    results: dict[tuple[str, str], dict[str, Any]] = {}
    attestations: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        if entry.get("kind") == "result":
            results[(entry.get("repository_id"), entry.get("check_id"))] = entry
        elif entry.get("kind") == "attestation":
            attestations.setdefault(entry.get("result_entry_hash", ""), []).append(entry)
    for requirement in snapshot.get("required_checks", []):
        key = (requirement["repository_id"], requirement["check_id"])
        result = results.get(key)
        label = f"{key[0]}/{key[1]}"
        if result is None:
            errors.append(f"required check missing: {label}")
            continue
        if result.get("exit_code") != PASS:
            errors.append(f"required check did not pass: {label} (exit {result.get('exit_code')})")
        valid_attestation = False
        for attestation in attestations.get(result.get("entry_hash", ""), []):
            if attestation.get("declared_by") in requirement["trusted_attestors"] and attestation.get("declared_by") != result.get("performed_by"):
                valid_attestation = True
        if not valid_attestation:
            errors.append(f"required check lacks trusted independent attestation declaration: {label}")
    return errors


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))


def command(args: argparse.Namespace) -> int:
    if args.action == "compile":
        index = compile_graph(Path(args.source))
        write_json(Path(args.output), index)
        print(index["index_digest"])
        return PASS
    if args.action == "gate-index":
        errors = validate_index(load_json(Path(args.index)))
        if errors:
            raise KernelError("\n".join(errors))
    elif args.action == "freeze":
        index = load_json(Path(args.index))
        verify_index_at_commit(index, args.graph_commit, Path(args.index).resolve().parent)
        checks = parse_required_checks(args.required_check, args.trusted_attestor)
        snapshot, bundle, payload = freeze_snapshot(args.feature, args.version, index, args.node, args.delivery_lane, args.repository, checks, args.graph_commit, args.supersedes)
        publish_snapshot(Path(args.output), snapshot, bundle, payload)
        print(snapshot["snapshot_digest"])
        return PASS
    elif args.action == "verify-snapshot":
        path = Path(args.snapshot)
        errors = verify_snapshot_against_graph(load_json(path), path)
        if errors:
            raise KernelError("\n".join(errors))
    elif args.action == "drift":
        snapshot_path = Path(args.snapshot)
        snapshot = load_json(snapshot_path)
        snapshot_errors = verify_snapshot_against_graph(snapshot, snapshot_path)
        if snapshot_errors:
            raise KernelError("\n".join(snapshot_errors))
        errors = detect_drift(snapshot, load_json(Path(args.index)))
    elif args.action == "record-result":
        snapshot_path = Path(args.snapshot)
        snapshot = load_json(snapshot_path)
        snapshot_errors = verify_snapshot_against_graph(snapshot, snapshot_path)
        if snapshot_errors:
            raise KernelError("\n".join(snapshot_errors))
        repo_commit, repo_digest = repo_state(Path(args.repo_path))
        base = {
            "schema_version": 1, "kind": "result", "snapshot_digest": snapshot["snapshot_digest"],
            "repository_id": args.repository_id, "check_id": args.check_id, "exit_code": args.exit_code,
            "checker_digest": digest_bytes(Path(args.checker_file).read_bytes()), "repo_commit": repo_commit,
            "repo_state_digest": repo_digest, "output_digest": digest_bytes(Path(args.output_file).read_bytes()),
            "performed_by": args.performed_by, "recorded_at": utc_now(),
        }
        entry = append_locked(Path(args.ledger), snapshot, lambda _entries: dict(base))
        print(entry["entry_hash"])
        return PASS
    elif args.action == "declare-attestation":
        snapshot_path = Path(args.snapshot)
        snapshot = load_json(snapshot_path)
        snapshot_errors = verify_snapshot_against_graph(snapshot, snapshot_path)
        if snapshot_errors:
            raise KernelError("\n".join(snapshot_errors))
        def build(entries: list[dict[str, Any]]) -> dict[str, Any]:
            result = next((entry for entry in entries if entry.get("kind") == "result" and entry.get("entry_hash") == args.result_hash), None)
            if result is None:
                raise KernelError("attestation result hash does not exist")
            requirement = next((item for item in snapshot["required_checks"] if item["repository_id"] == result["repository_id"] and item["check_id"] == result["check_id"]), None)
            if requirement is None or args.declared_by not in requirement["trusted_attestors"]:
                raise KernelError("declared attestor is not trusted for this check")
            if args.declared_by == result["performed_by"]:
                raise KernelError("performer cannot attest its own result")
            return {
                "schema_version": 1, "kind": "attestation", "snapshot_digest": snapshot["snapshot_digest"],
                "result_entry_hash": args.result_hash, "declared_by": args.declared_by,
                "declaration_mode": args.declaration_mode,
                "artifact_digest": digest_bytes(Path(args.attestation_file).read_bytes()), "recorded_at": utc_now(),
            }
        entry = append_locked(Path(args.ledger), snapshot, build)
        print(entry["entry_hash"])
        return PASS
    elif args.action == "verify-evidence":
        path = Path(args.snapshot)
        snapshot = load_json(path)
        entries = load_ledger(Path(args.ledger))
        structural_errors = verify_snapshot_against_graph(snapshot, path) + validate_ledger(snapshot, entries)
        if structural_errors:
            raise KernelError("\n".join(dict.fromkeys(structural_errors)))
        errors = verify_evidence(snapshot, entries)
    else:
        raise KernelError(f"unknown action {args.action}")
    if errors:
        print("\n".join(dict.fromkeys(errors)), file=sys.stderr)
        return FAIL
    return PASS


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    actions = root.add_subparsers(dest="action", required=True)
    compile_cmd = actions.add_parser("compile")
    compile_cmd.add_argument("--source", required=True)
    compile_cmd.add_argument("--output", required=True)
    gate = actions.add_parser("gate-index")
    gate.add_argument("--index", required=True)
    freeze = actions.add_parser("freeze")
    freeze.add_argument("--feature", required=True)
    freeze.add_argument("--version", required=True)
    freeze.add_argument("--index", required=True)
    freeze.add_argument("--node", action="append", default=[])
    freeze.add_argument("--delivery-lane", action="append", default=[])
    freeze.add_argument("--repository", action="append", default=[])
    freeze.add_argument("--required-check", action="append", default=[])
    freeze.add_argument("--trusted-attestor", action="append", default=[])
    freeze.add_argument("--graph-commit", required=True)
    freeze.add_argument("--supersedes")
    freeze.add_argument("--output", required=True)
    verify = actions.add_parser("verify-snapshot")
    verify.add_argument("--snapshot", required=True)
    drift = actions.add_parser("drift")
    drift.add_argument("--snapshot", required=True)
    drift.add_argument("--index", required=True)
    record = actions.add_parser("record-result")
    record.add_argument("--ledger", required=True)
    record.add_argument("--snapshot", required=True)
    record.add_argument("--repository-id", required=True)
    record.add_argument("--check-id", required=True)
    record.add_argument("--exit-code", required=True, type=int)
    record.add_argument("--repo-path", required=True)
    record.add_argument("--checker-file", required=True)
    record.add_argument("--output-file", required=True)
    record.add_argument("--performed-by", required=True)
    attest = actions.add_parser("declare-attestation")
    attest.add_argument("--ledger", required=True)
    attest.add_argument("--snapshot", required=True)
    attest.add_argument("--result-hash", required=True)
    attest.add_argument("--declared-by", required=True)
    attest.add_argument("--declaration-mode", choices=["ci_declaration", "signature_declaration", "human_declaration"], required=True)
    attest.add_argument("--attestation-file", required=True)
    evidence = actions.add_parser("verify-evidence")
    evidence.add_argument("--ledger", required=True)
    evidence.add_argument("--snapshot", required=True)
    return root


def main() -> int:
    try:
        return command(parser().parse_args())
    except (KernelError, OSError, KeyError, TypeError, UnicodeDecodeError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return INVALID


if __name__ == "__main__":
    raise SystemExit(main())
