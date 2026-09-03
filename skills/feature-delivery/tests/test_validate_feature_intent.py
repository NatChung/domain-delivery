import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL_ROOT / "scripts" / "validate_feature_intent.py"
if str(VALIDATOR.parent) not in sys.path:
    sys.path.insert(0, str(VALIDATOR.parent))

import validate_feature_intent as contract


def ready_intent():
    return {
        "schema_version": "feature-intent/v0.1",
        "intake_status": "ready_for_domain_lookup",
        "ticket": {
            "key": "TCK-123",
            "url": "https://tracker.example.com/browse/TCK-123",
            "project": "SHOP",
            "issue_type": "Story",
            "status": "Open",
            "summary": "提醒商品時可選擇尺寸",
            "freshness": "live",
        },
        "request_type": "feature",
        "business_outcomes": ["顧客提醒商品時，系統保留其感興趣的尺寸"],
        "request_shape": {
            "actors": ["顧客"],
            "triggers": ["顧客將商品加入 Reminder"],
            "actions": [{"verb": "選擇", "object": "尺寸"}],
            "observable_results": ["Reminder item 顯示並保留顧客選擇的尺寸"],
        },
        "scope": {"included": [], "excluded": []},
        "constraints": [],
        "dependencies": [],
        "domain_hooks": {"terms": ["Reminder", "product", "size"]},
        "evidence": {
            "observed": [
                {
                    "statement": "顧客提醒商品時可以選擇尺寸",
                    "source_ids": ["ticket:TCK-123/field/description"],
                }
            ],
            "inferred": [
                {
                    "statement": "選擇尺寸可能不是必填",
                    "basis": "Ticket 使用「可以選擇」的表述",
                    "source_ids": ["ticket:TCK-123/field/description"],
                }
            ],
            "unknown": [
                {
                    "question": "尺寸為選填或必填？",
                    "reason_required": "會改變 invalid cases 與 acceptance criteria",
                    "blocks_domain_lookup": False,
                }
            ],
            "contradicted": [],
        },
        "source_coverage": {
            "reviewed": [
                {
                    "id": "ticket:TCK-123/fields",
                    "kind": "collection",
                    "material": False,
                    "author": None,
                    "updated_at": None,
                },
                {
                    "id": "ticket:TCK-123/comments",
                    "kind": "collection",
                    "material": False,
                    "author": None,
                    "updated_at": None,
                },
                {
                    "id": "ticket:TCK-123/attachments",
                    "kind": "collection",
                    "material": False,
                    "author": None,
                    "updated_at": None,
                },
                {
                    "id": "ticket:TCK-123/links",
                    "kind": "collection",
                    "material": False,
                    "author": None,
                    "updated_at": None,
                },
                {
                    "id": "ticket:TCK-123/field/description",
                    "kind": "field",
                    "material": True,
                    "author": None,
                    "updated_at": None,
                },
            ],
            "unavailable": [],
            "not_applicable": [],
        },
        "extensions": {},
    }


class FeatureIntentValidatorCliTests(unittest.TestCase):
    def run_validator(self, intent, *extra_args):
        return self.run_raw(json.dumps(intent, ensure_ascii=False), *extra_args)

    def run_raw(self, text, *extra_args):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feature-intent.json"
            path.write_text(text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-B", str(VALIDATOR), "--input", str(path), *extra_args],
                text=True,
                capture_output=True,
            )

    def test_ready_feature_intent_passes_required_gate(self):
        result = self.run_validator(ready_intent(), "--require-ready")

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_contract_field_is_invalid(self):
        intent = copy.deepcopy(ready_intent())
        del intent["domain_hooks"]

        result = self.run_validator(intent)

        self.assertEqual(result.returncode, 2)
        self.assertIn("top-level fields", result.stderr)

    def test_claimed_ready_status_must_match_recomputed_gate(self):
        intent = copy.deepcopy(ready_intent())
        intent["business_outcomes"] = []

        result = self.run_validator(intent)

        self.assertEqual(result.returncode, 2)
        self.assertIn("recomputed intake_status is incomplete", result.stderr)

    def test_evidence_cannot_reference_an_unreviewed_source(self):
        intent = copy.deepcopy(ready_intent())
        intent["evidence"]["observed"][0]["source_ids"] = [
            "ticket:TCK-123/field/unreviewed"
        ]

        result = self.run_validator(intent)

        self.assertEqual(result.returncode, 2)
        self.assertIn("source is not reviewed", result.stderr)

    def test_action_requires_both_verb_and_object(self):
        intent = copy.deepcopy(ready_intent())
        intent["request_shape"]["actions"] = [{"verb": "選擇"}]
        intent["intake_status"] = "incomplete"

        result = self.run_validator(intent)

        self.assertEqual(result.returncode, 2)
        self.assertIn("request_shape.actions[0]", result.stderr)

    def test_nested_contract_rejects_unknown_fields(self):
        intent = copy.deepcopy(ready_intent())
        intent["ticket"]["implementation_repo"] = "reminder-service"

        result = self.run_validator(intent)

        self.assertEqual(result.returncode, 2)
        self.assertIn("ticket has missing or unknown fields", result.stderr)

    def test_valid_incomplete_intent_only_fails_when_ready_is_required(self):
        intent = copy.deepcopy(ready_intent())
        intent["business_outcomes"] = []
        intent["evidence"]["unknown"].append(
            {
                "question": "PO 預期的 business outcome 是什麼？",
                "reason_required": "Domain Graph lookup 需要知道需求目的",
                "blocks_domain_lookup": True,
            }
        )
        intent["intake_status"] = "incomplete"

        validation = self.run_validator(intent)
        gate = self.run_validator(intent, "--require-ready")

        self.assertEqual(validation.returncode, 0, validation.stderr)
        self.assertEqual(gate.returncode, 1, gate.stderr)

    def test_duplicate_json_keys_are_invalid(self):
        text = json.dumps(ready_intent(), ensure_ascii=False)
        text = text.replace(
            '"schema_version": "feature-intent/v0.1",',
            '"schema_version": "wrong", "schema_version": "feature-intent/v0.1",',
            1,
        )

        result = self.run_raw(text)

        self.assertEqual(result.returncode, 2)
        self.assertIn("duplicate JSON key", result.stderr)


class FeatureIntentSchemaParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema_path = SKILL_ROOT / "references" / "feature-intent.schema.json"
        cls.schema = json.loads(schema_path.read_text(encoding="utf-8"))

    def assert_object_fields(self, schema_object, runtime_fields):
        self.assertFalse(schema_object["additionalProperties"])
        self.assertEqual(set(schema_object["required"]), runtime_fields)
        self.assertEqual(set(schema_object["properties"]), runtime_fields)

    def test_runtime_and_schema_shapes_match(self):
        schema = self.schema
        self.assert_object_fields(schema, contract.TOP_LEVEL_FIELDS)
        properties = schema["properties"]
        definitions = schema["$defs"]
        self.assert_object_fields(properties["ticket"], contract.TICKET_FIELDS)
        self.assert_object_fields(
            properties["request_shape"], contract.REQUEST_SHAPE_FIELDS
        )
        self.assert_object_fields(properties["scope"], contract.SCOPE_FIELDS)
        self.assert_object_fields(
            properties["domain_hooks"], contract.DOMAIN_HOOK_FIELDS
        )
        self.assert_object_fields(properties["evidence"], contract.EVIDENCE_FIELDS)
        self.assert_object_fields(
            properties["source_coverage"], contract.SOURCE_COVERAGE_FIELDS
        )
        self.assert_object_fields(definitions["action"], contract.ACTION_FIELDS)
        self.assert_object_fields(definitions["observed"], contract.OBSERVED_FIELDS)
        self.assert_object_fields(definitions["inferred"], contract.INFERRED_FIELDS)
        self.assert_object_fields(definitions["unknown"], contract.UNKNOWN_FIELDS)
        self.assert_object_fields(
            definitions["contradicted"], contract.CONTRADICTED_FIELDS
        )
        self.assert_object_fields(
            definitions["reviewedSource"], contract.REVIEWED_SOURCE_FIELDS
        )
        self.assert_object_fields(
            definitions["unavailableSource"], contract.UNAVAILABLE_SOURCE_FIELDS
        )

    def test_runtime_and_schema_versions_enums_and_patterns_match(self):
        properties = self.schema["properties"]
        definitions = self.schema["$defs"]
        self.assertEqual(properties["schema_version"]["const"], contract.SCHEMA_VERSION)
        self.assertEqual(set(properties["intake_status"]["enum"]), contract.INTAKE_STATUSES)
        self.assertEqual(set(properties["request_type"]["enum"]), contract.REQUEST_TYPES)
        self.assertEqual(
            set(properties["ticket"]["properties"]["freshness"]["enum"]),
            contract.FRESHNESS_VALUES,
        )
        self.assertEqual(
            set(definitions["reviewedSource"]["properties"]["kind"]["enum"]),
            contract.SOURCE_KINDS,
        )
        self.assertEqual(
            properties["ticket"]["properties"]["key"]["pattern"],
            contract.TICKET_KEY_RE.pattern,
        )
        self.assertEqual(definitions["sourceId"]["pattern"], contract.SOURCE_ID_RE.pattern)


if __name__ == "__main__":
    unittest.main()
