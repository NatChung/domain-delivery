#!/usr/bin/env python3
"""Evaluate Feature Intent outputs against request-intake case invariants."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from validate_feature_intent import ValidationError, load_json, validate


PASS, FAIL, INVALID = 0, 1, 2
from _paths import hub_root  # noqa: E402

HUB_ROOT = hub_root()
EXPECTED_FIELDS = {
    "intake_status",
    "required_domain_term_any_of",
    "required_actions",
    "required_observed_source_ids",
    "required_unknown_question_terms",
    "forbidden_observed_statements",
}


def string_array(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValidationError(f"expected.{field} must be an array of non-empty strings")
    return value


def string_groups(value: Any, field: str) -> list[list[str]]:
    if not isinstance(value, list) or not value:
        raise ValidationError(f"expected.{field} must be a non-empty array")
    groups: list[list[str]] = []
    for index, group in enumerate(value):
        groups.append(string_array(group, f"{field}[{index}]"))
        if not group:
            raise ValidationError(f"expected.{field}[{index}] must not be empty")
    return groups


def load_expected(path: Path) -> dict[str, Any]:
    expected = load_json(path)
    if not isinstance(expected, dict) or set(expected) != EXPECTED_FIELDS:
        raise ValidationError(f"{path}: expected.json has missing or unknown fields")
    if expected["intake_status"] not in {
        "ready_for_domain_lookup",
        "incomplete",
    }:
        raise ValidationError(f"{path}: expected.intake_status is invalid")
    for field in (
        "required_observed_source_ids",
        "forbidden_observed_statements",
    ):
        string_array(expected[field], field)
    string_groups(expected["required_domain_term_any_of"], "required_domain_term_any_of")
    string_groups(
        expected["required_unknown_question_terms"],
        "required_unknown_question_terms",
    )
    actions = expected["required_actions"]
    if not isinstance(actions, list) or any(
        not isinstance(action, dict)
        or set(action) != {"verb", "object"}
        or any(not isinstance(action[field], str) or not action[field].strip() for field in action)
        for action in actions
    ):
        raise ValidationError(
            f"{path}: expected.required_actions must contain verb/object pairs"
        )
    return expected


def evaluate(intent: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if intent["intake_status"] != expected["intake_status"]:
        errors.append(
            f"intake_status expected {expected['intake_status']}, "
            f"got {intent['intake_status']}"
        )

    terms = intent["domain_hooks"]["terms"]
    for alternatives in expected["required_domain_term_any_of"]:
        if not any(
            alternative.lower() in term.lower()
            for alternative in alternatives
            for term in terms
        ):
            errors.append(
                "missing required domain concept (any of): "
                + ", ".join(alternatives)
            )

    actions = intent["request_shape"]["actions"]
    for action in expected["required_actions"]:
        if action not in actions:
            errors.append(
                f"missing required action: {action['verb']} {action['object']}"
            )

    observed = intent["evidence"]["observed"]
    observed_source_ids = {
        source_id for item in observed for source_id in item["source_ids"]
    }
    for source_id in expected["required_observed_source_ids"]:
        if source_id not in observed_source_ids:
            errors.append(f"missing required observed source: {source_id}")

    unknown_questions = [item["question"] for item in intent["evidence"]["unknown"]]
    for required_terms in expected["required_unknown_question_terms"]:
        if not any(
            all(term.lower() in question.lower() for term in required_terms)
            for question in unknown_questions
        ):
            errors.append(
                "missing unknown question containing: " + ", ".join(required_terms)
            )

    observed_statements = {item["statement"] for item in observed}
    for statement in expected["forbidden_observed_statements"]:
        if statement in observed_statements:
            errors.append(f"forbidden observed statement: {statement}")
    return errors


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--cases", required=True)
    root.add_argument(
        "--outputs",
        required=True,
        help="Directory containing freshly generated <case-id>.json outputs",
    )
    return root


def main() -> int:
    args = parser().parse_args()
    cases_root = Path(args.cases)
    outputs_root = Path(args.outputs).resolve()
    if outputs_root == HUB_ROOT or outputs_root.is_relative_to(HUB_ROOT):
        print("--outputs must be outside the Hub Git repository", file=sys.stderr)
        return INVALID
    try:
        cases = sorted(path for path in cases_root.iterdir() if path.is_dir())
    except OSError as exc:
        print(f"{cases_root}: cannot read cases: {exc}", file=sys.stderr)
        return INVALID
    if not cases:
        print(f"{cases_root}: no eval case directories found", file=sys.stderr)
        return INVALID

    failed = False
    try:
        for case in cases:
            load_json(case / "ticket.json")
            expected = load_expected(case / "expected.json")
            actual_path = outputs_root / f"{case.name}.json"
            intent = load_json(actual_path)
            validation_errors = validate(intent)
            if validation_errors:
                raise ValidationError(
                    f"{actual_path}: invalid Feature Intent:\n"
                    + "\n".join(validation_errors)
                )
            eval_errors = evaluate(intent, expected)
            if eval_errors:
                failed = True
                print(f"FAIL {case.name}: " + "; ".join(eval_errors))
            else:
                print(f"PASS {case.name}")
    except (ValidationError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return INVALID
    return FAIL if failed else PASS


if __name__ == "__main__":
    raise SystemExit(main())
