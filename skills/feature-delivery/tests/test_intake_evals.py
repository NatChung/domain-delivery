import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_validate_feature_intent import ready_intent


SKILL_ROOT = Path(__file__).resolve().parents[1]
RUNNER = SKILL_ROOT / "scripts" / "run_intake_evals.py"


class IntakeEvalCliTests(unittest.TestCase):
    def write_case(self, root):
        case = root / "reminder-size"
        case.mkdir()
        (case / "ticket.json").write_text(
            json.dumps(
                {
                    "key": "TCK-123",
                    "summary": "提醒商品時可選擇尺寸",
                    "description": "顧客提醒商品時可以選擇尺寸。",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (case / "expected.json").write_text(
            json.dumps(
                {
                    "intake_status": "ready_for_domain_lookup",
                    "required_domain_term_any_of": [
                        ["提醒", "Reminder"],
                        ["尺寸", "size"],
                    ],
                    "required_actions": [{"verb": "選擇", "object": "尺寸"}],
                    "required_observed_source_ids": [
                        "ticket:TCK-123/field/description"
                    ],
                    "required_unknown_question_terms": [["尺寸", "選填", "必填"]],
                    "forbidden_observed_statements": ["尺寸為必填"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    def write_output(self, outputs, actual):
        outputs.mkdir()
        (outputs / "reminder-size.json").write_text(
            json.dumps(actual, ensure_ascii=False), encoding="utf-8"
        )

    def run_evals(self, cases, outputs=None):
        command = [sys.executable, "-B", str(RUNNER), "--cases", str(cases)]
        if outputs is not None:
            command.extend(["--outputs", str(outputs)])
        return subprocess.run(
            command,
            text=True,
            capture_output=True,
        )

    def test_case_passes_when_feature_intent_satisfies_expected_invariants(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = root / "cases"
            outputs = root / "outputs"
            cases.mkdir()
            self.write_case(cases)
            self.write_output(outputs, ready_intent())
            result = self.run_evals(cases, outputs)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS reminder-size", result.stdout)

    def test_case_fails_when_required_domain_term_is_missing(self):
        actual = ready_intent()
        actual["domain_hooks"]["terms"].remove("size")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = root / "cases"
            outputs = root / "outputs"
            cases.mkdir()
            self.write_case(cases)
            self.write_output(outputs, actual)
            result = self.run_evals(cases, outputs)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("missing required domain concept", result.stdout)

    def test_outputs_directory_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            cases = Path(directory) / "cases"
            cases.mkdir()
            self.write_case(cases)
            result = self.run_evals(cases)

        self.assertEqual(result.returncode, 2)
        self.assertIn("--outputs", result.stderr)

    def test_committed_case_actual_is_not_used_as_fresh_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = root / "cases"
            outputs = root / "outputs"
            cases.mkdir()
            outputs.mkdir()
            self.write_case(cases)
            (cases / "reminder-size" / "actual.json").write_text(
                json.dumps(ready_intent(), ensure_ascii=False), encoding="utf-8"
            )
            result = self.run_evals(cases, outputs)

        self.assertEqual(result.returncode, 2)
        self.assertIn("outputs/reminder-size.json", result.stderr)
        self.assertIn("No such file or directory", result.stderr)

    def test_outputs_inside_hub_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            cases = Path(directory) / "cases"
            cases.mkdir()
            self.write_case(cases)
            result = self.run_evals(cases, SKILL_ROOT)

        self.assertEqual(result.returncode, 2)
        self.assertIn("outside the Hub Git repository", result.stderr)


if __name__ == "__main__":
    unittest.main()
