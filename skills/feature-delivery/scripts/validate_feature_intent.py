#!/usr/bin/env python3
"""Validate a Feature Delivery Feature Intent JSON artifact."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PASS, FAIL, INVALID = 0, 1, 2
SCHEMA_VERSION = "feature-intent/v0.1"
INTAKE_STATUSES = {"ready_for_domain_lookup", "incomplete"}
REQUEST_TYPES = {"feature", "change", "bug", "discovery", "unknown"}
FRESHNESS_VALUES = {"live", "provided", "snapshot"}
SOURCE_KINDS = {"collection", "field", "comment", "attachment", "linked_issue"}
TICKET_KEY_RE = re.compile(r"^(?:[A-Z][A-Z0-9]*-[0-9]+|UNKEYED)$")
SOURCE_ID_RE = re.compile(
    r"^(?:ticket|provided|snapshot):(?:[A-Z][A-Z0-9]*-[0-9]+|UNKEYED)/"
    r"(?:fields|comments|attachments|links|"
    r"field/[a-z0-9][a-z0-9._-]*|"
    r"comment/[A-Za-z0-9][A-Za-z0-9._-]*|"
    r"attachment/[A-Za-z0-9][A-Za-z0-9._-]*(?:#[^\s]+)?|"
    r"linked/[A-Z][A-Z0-9]*-[0-9]+/field/[a-z0-9][a-z0-9._-]*)$"
)
TOP_LEVEL_FIELDS = {
    "schema_version",
    "intake_status",
    "ticket",
    "request_type",
    "business_outcomes",
    "request_shape",
    "scope",
    "constraints",
    "dependencies",
    "domain_hooks",
    "evidence",
    "source_coverage",
    "extensions",
}
TICKET_FIELDS = {"key", "url", "project", "issue_type", "status", "summary", "freshness"}
REQUEST_SHAPE_FIELDS = {"actors", "triggers", "actions", "observable_results"}
ACTION_FIELDS = {"verb", "object"}
SCOPE_FIELDS = {"included", "excluded"}
DOMAIN_HOOK_FIELDS = {"terms"}
EVIDENCE_FIELDS = {"observed", "inferred", "unknown", "contradicted"}
OBSERVED_FIELDS = {"statement", "source_ids"}
INFERRED_FIELDS = {"statement", "basis", "source_ids"}
UNKNOWN_FIELDS = {"question", "reason_required", "blocks_domain_lookup"}
CONTRADICTED_FIELDS = {"question", "claims", "blocks_domain_lookup"}
SOURCE_COVERAGE_FIELDS = {"reviewed", "unavailable", "not_applicable"}
REVIEWED_SOURCE_FIELDS = {"id", "kind", "material", "author", "updated_at"}
UNAVAILABLE_SOURCE_FIELDS = {"id", "reason"}


class ValidationError(ValueError):
    pass


def nonempty_strings(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and bool(item.strip()) for item in value
    )


def exact_object(
    value: Any,
    path: str,
    fields: set[str],
    errors: list[str],
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return None
    if set(value) != fields:
        missing = sorted(fields - set(value))
        unknown = sorted(set(value) - fields)
        errors.append(
            f"{path} has missing or unknown fields"
            f" (missing={missing}, unknown={unknown})"
        )
    return value


def require_nonempty_string(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path} must be a non-empty string")


def validate_string_list(
    value: Any,
    path: str,
    errors: list[str],
    *,
    allow_empty: bool = True,
) -> None:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        errors.append(f"{path} must be an array of non-empty strings")
        return
    if not allow_empty and not value:
        errors.append(f"{path} must not be empty")
    if len(value) != len(set(value)):
        errors.append(f"{path} must not contain duplicates")


def validate_evidence_items(evidence: dict[str, Any], errors: list[str]) -> None:
    shapes = {
        "observed": OBSERVED_FIELDS,
        "inferred": INFERRED_FIELDS,
        "unknown": UNKNOWN_FIELDS,
        "contradicted": CONTRADICTED_FIELDS,
    }
    for field, fields in shapes.items():
        items = evidence.get(field)
        if not isinstance(items, list):
            errors.append(f"evidence.{field} must be an array")
            continue
        for index, item in enumerate(items):
            path = f"evidence.{field}[{index}]"
            item = exact_object(item, path, fields, errors)
            if item is None:
                continue
            if field in {"observed", "inferred"}:
                require_nonempty_string(item.get("statement"), f"{path}.statement", errors)
                validate_string_list(
                    item.get("source_ids"), f"{path}.source_ids", errors, allow_empty=False
                )
                if field == "inferred":
                    require_nonempty_string(item.get("basis"), f"{path}.basis", errors)
            elif field == "unknown":
                require_nonempty_string(item.get("question"), f"{path}.question", errors)
                require_nonempty_string(
                    item.get("reason_required"), f"{path}.reason_required", errors
                )
                if not isinstance(item.get("blocks_domain_lookup"), bool):
                    errors.append(f"{path}.blocks_domain_lookup must be a boolean")
            else:
                require_nonempty_string(item.get("question"), f"{path}.question", errors)
                if not isinstance(item.get("blocks_domain_lookup"), bool):
                    errors.append(f"{path}.blocks_domain_lookup must be a boolean")
                claims = item.get("claims")
                if not isinstance(claims, list) or len(claims) < 2:
                    errors.append(f"{path}.claims must contain at least two claims")
                    continue
                for claim_index, claim in enumerate(claims):
                    claim_path = f"{path}.claims[{claim_index}]"
                    claim = exact_object(
                        claim, claim_path, OBSERVED_FIELDS, errors
                    )
                    if claim is None:
                        continue
                    require_nonempty_string(
                        claim.get("statement"), f"{claim_path}.statement", errors
                    )
                    validate_string_list(
                        claim.get("source_ids"),
                        f"{claim_path}.source_ids",
                        errors,
                        allow_empty=False,
                    )


def validate_source_coverage(coverage: dict[str, Any], errors: list[str]) -> None:
    all_ids: list[str] = []
    reviewed = coverage.get("reviewed")
    if not isinstance(reviewed, list):
        errors.append("source_coverage.reviewed must be an array")
    else:
        for index, item in enumerate(reviewed):
            path = f"source_coverage.reviewed[{index}]"
            item = exact_object(
                item,
                path,
                REVIEWED_SOURCE_FIELDS,
                errors,
            )
            if item is None:
                continue
            source_id = item.get("id")
            if not isinstance(source_id, str) or not SOURCE_ID_RE.fullmatch(source_id):
                errors.append(f"{path}.id is not a valid Feature Intent source ID")
            else:
                all_ids.append(source_id)
            if item.get("kind") not in SOURCE_KINDS:
                errors.append(f"{path}.kind is invalid")
            if not isinstance(item.get("material"), bool):
                errors.append(f"{path}.material must be a boolean")
            for field in ("author", "updated_at"):
                if item.get(field) is not None:
                    require_nonempty_string(item.get(field), f"{path}.{field}", errors)
    for field in ("unavailable", "not_applicable"):
        items = coverage.get(field)
        if not isinstance(items, list):
            errors.append(f"source_coverage.{field} must be an array")
            continue
        for index, item in enumerate(items):
            path = f"source_coverage.{field}[{index}]"
            item = exact_object(item, path, UNAVAILABLE_SOURCE_FIELDS, errors)
            if item is None:
                continue
            source_id = item.get("id")
            if not isinstance(source_id, str) or not SOURCE_ID_RE.fullmatch(source_id):
                errors.append(f"{path}.id is not a valid Feature Intent source ID")
            else:
                all_ids.append(source_id)
            require_nonempty_string(item.get("reason"), f"{path}.reason", errors)
    if len(all_ids) != len(set(all_ids)):
        errors.append("source_coverage source IDs must be unique across all states")


def validate_shape(intent: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ticket = exact_object(
        intent.get("ticket"),
        "ticket",
        TICKET_FIELDS,
        errors,
    )
    if ticket is not None:
        if not isinstance(ticket.get("key"), str) or not TICKET_KEY_RE.fullmatch(
            ticket["key"]
        ):
            errors.append("ticket.key must be a tracker issue key or UNKEYED")
        for field in ("url", "project", "issue_type", "status", "summary"):
            if ticket.get(field) is not None:
                require_nonempty_string(ticket.get(field), f"ticket.{field}", errors)
        if ticket.get("freshness") not in FRESHNESS_VALUES:
            errors.append("ticket.freshness must be live, provided, or snapshot")
    if intent.get("request_type") not in REQUEST_TYPES:
        errors.append("request_type is invalid")
    validate_string_list(intent.get("business_outcomes"), "business_outcomes", errors)
    request_shape = exact_object(
        intent.get("request_shape"),
        "request_shape",
        REQUEST_SHAPE_FIELDS,
        errors,
    )
    if request_shape is not None:
        for field in ("actors", "triggers", "observable_results"):
            validate_string_list(
                request_shape.get(field), f"request_shape.{field}", errors
            )
    errors.extend(validate_actions(intent))
    scope = exact_object(
        intent.get("scope"), "scope", SCOPE_FIELDS, errors
    )
    if scope is not None:
        validate_string_list(scope.get("included"), "scope.included", errors)
        validate_string_list(scope.get("excluded"), "scope.excluded", errors)
    validate_string_list(intent.get("constraints"), "constraints", errors)
    validate_string_list(intent.get("dependencies"), "dependencies", errors)
    hooks = exact_object(intent.get("domain_hooks"), "domain_hooks", DOMAIN_HOOK_FIELDS, errors)
    if hooks is not None:
        validate_string_list(hooks.get("terms"), "domain_hooks.terms", errors)
    evidence = exact_object(
        intent.get("evidence"),
        "evidence",
        EVIDENCE_FIELDS,
        errors,
    )
    if evidence is not None:
        validate_evidence_items(evidence, errors)
    coverage = exact_object(
        intent.get("source_coverage"),
        "source_coverage",
        SOURCE_COVERAGE_FIELDS,
        errors,
    )
    if coverage is not None:
        validate_source_coverage(coverage, errors)
    if not isinstance(intent.get("extensions"), dict):
        errors.append("extensions must be an object")
    return errors


def recompute_intake_status(intent: dict[str, Any]) -> str:
    ticket = intent.get("ticket")
    request_shape = intent.get("request_shape")
    domain_hooks = intent.get("domain_hooks")
    evidence = intent.get("evidence")
    coverage = intent.get("source_coverage")
    if not all(isinstance(value, dict) for value in (ticket, request_shape, domain_hooks, evidence, coverage)):
        return "incomplete"

    freshness = ticket.get("freshness")
    key = ticket.get("key")
    prefix = freshness if freshness in {"provided", "snapshot"} else "ticket"
    covered_ids = {
        item.get("id")
        for field in ("reviewed", "unavailable", "not_applicable")
        for item in coverage.get(field, [])
        if isinstance(item, dict)
    }
    required_collection_ids = {
        f"{prefix}:{key}/fields",
        f"{prefix}:{key}/comments",
        f"{prefix}:{key}/attachments",
        f"{prefix}:{key}/links",
    }
    coverage_complete = (
        isinstance(key, str)
        and bool(key)
        and required_collection_ids <= covered_ids
        and not coverage.get("unavailable")
    )
    actions = request_shape.get("actions")
    has_action = isinstance(actions, list) and any(
        isinstance(action, dict)
        and isinstance(action.get("verb"), str)
        and bool(action["verb"].strip())
        and isinstance(action.get("object"), str)
        and bool(action["object"].strip())
        for action in actions
    )
    unknowns = evidence.get("unknown")
    has_blocking_unknown = not isinstance(unknowns, list) or any(
        not isinstance(item, dict) or item.get("blocks_domain_lookup") is True
        for item in unknowns
    )
    contradictions = evidence.get("contradicted")
    has_blocking_contradiction = not isinstance(contradictions, list) or any(
        not isinstance(item, dict) or item.get("blocks_domain_lookup") is not False
        for item in contradictions
    )
    ready = (
        coverage_complete
        and freshness in {"live", "provided"}
        and nonempty_strings(intent.get("business_outcomes"))
        and has_action
        and nonempty_strings(request_shape.get("observable_results"))
        and nonempty_strings(domain_hooks.get("terms"))
        and not has_blocking_unknown
        and not has_blocking_contradiction
    )
    return "ready_for_domain_lookup" if ready else "incomplete"


def validate_traceability(intent: dict[str, Any]) -> list[str]:
    coverage = intent.get("source_coverage")
    evidence = intent.get("evidence")
    if not isinstance(coverage, dict) or not isinstance(evidence, dict):
        return []
    reviewed_ids = {
        item.get("id")
        for item in coverage.get("reviewed", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    referenced_ids: list[str] = []
    for field in ("observed", "inferred"):
        for item in evidence.get(field, []):
            if isinstance(item, dict) and isinstance(item.get("source_ids"), list):
                referenced_ids.extend(
                    source_id for source_id in item["source_ids"] if isinstance(source_id, str)
                )
    for contradiction in evidence.get("contradicted", []):
        if not isinstance(contradiction, dict):
            continue
        for claim in contradiction.get("claims", []):
            if isinstance(claim, dict) and isinstance(claim.get("source_ids"), list):
                referenced_ids.extend(
                    source_id for source_id in claim["source_ids"] if isinstance(source_id, str)
                )
    errors = [
        f"{source_id}: evidence source is not reviewed"
        for source_id in referenced_ids
        if source_id not in reviewed_ids
    ]
    material_ids = {
        item.get("id")
        for item in coverage.get("reviewed", [])
        if isinstance(item, dict) and item.get("material") is True
    }
    errors.extend(
        f"{source_id}: material reviewed source is not referenced by evidence"
        for source_id in sorted(material_ids - set(referenced_ids))
    )
    return errors


def validate_actions(intent: dict[str, Any]) -> list[str]:
    request_shape = intent.get("request_shape")
    if not isinstance(request_shape, dict):
        return ["request_shape must be an object"]
    actions = request_shape.get("actions")
    if not isinstance(actions, list):
        return ["request_shape.actions must be an array"]
    errors: list[str] = []
    for index, action in enumerate(actions):
        if (
            not isinstance(action, dict)
            or set(action) != ACTION_FIELDS
            or not all(isinstance(action.get(field), str) and action[field].strip() for field in ("verb", "object"))
        ):
            errors.append(
                f"request_shape.actions[{index}] must contain exactly non-empty verb and object"
            )
    return errors


def load_json(path: Path) -> Any:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValidationError(f"{path}: duplicate JSON key {key!r}")
            value[key] = item
        return value

    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicates,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"{path}: invalid JSON: {exc}") from exc


def validate(intent: Any) -> list[str]:
    if not isinstance(intent, dict):
        return ["Feature Intent must be a JSON object"]
    errors: list[str] = []
    if set(intent) != TOP_LEVEL_FIELDS:
        missing = sorted(TOP_LEVEL_FIELDS - set(intent))
        unknown = sorted(set(intent) - TOP_LEVEL_FIELDS)
        errors.append(
            "Feature Intent has missing or unknown top-level fields"
            f" (missing={missing}, unknown={unknown})"
        )
    if intent.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if intent.get("intake_status") not in INTAKE_STATUSES:
        errors.append("intake_status must be ready_for_domain_lookup or incomplete")
    errors.extend(validate_shape(intent))
    errors.extend(validate_traceability(intent))
    if not errors and intent.get("intake_status") != recompute_intake_status(intent):
        errors.append(
            f"recomputed intake_status is {recompute_intake_status(intent)}, "
            f"not {intent.get('intake_status')}"
        )
    return errors


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--input", required=True)
    root.add_argument("--require-ready", action="store_true")
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        intent = load_json(Path(args.input))
        errors = validate(intent)
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return INVALID
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return INVALID
    if args.require_ready and intent["intake_status"] != "ready_for_domain_lookup":
        print("Feature Intent is valid but incomplete", file=sys.stderr)
        return FAIL
    return PASS


if __name__ == "__main__":
    raise SystemExit(main())
