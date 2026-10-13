import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_validate_delivery_plan import kernel, contract, ready_projection, ready_task_plan, VALIDATOR, PACKAGE_ROOT


class UIProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q'], cwd=self.root, check=True)
        request = json.loads((PACKAGE_ROOT / 'kernel/tests/fixtures/ui-accepted-request.json').read_text())
        checks = [{'repository_id': 'sample-web', 'check_id': 'unit-tests', 'trusted_attestors': ['ci:test-runner']}]
        self.snapshot, bundle, payload = kernel.freeze_snapshot('dialog-copy', 'v1', None, [], ['web'], ['sample-web'], checks, None, kind='ui', accepted_request=request)
        output = self.root / 'snapshot'
        kernel.publish_snapshot(output, self.snapshot, bundle, payload)
        self.manifest = output / 'snapshot-manifest.json'
        self.path = self.root / '05-check-projection.json'
        self.projection = ready_projection(self.snapshot)
        self.projection['schema_version'] = 'check-projection/v0.2'
        self.projection['projections'][0]['snapshot_rule_refs'] = [
            {'node_id': ac['id'], 'field': 'acceptance_criteria', 'statement': ac['text']}
            for ac in request['acceptance_criteria']
        ]
        for item in self.projection['projections']:
            for relative in item['specification_paths']:
                (self.root / relative).write_text('# Synthetic UI specification\n')

    def validate(self, projection=None):
        return contract.validate_projection(projection or self.projection, self.path, self.snapshot, self.manifest)

    def test_all_ac_coverage_and_cli_no_graph(self):
        self.assertEqual(self.validate(), [])
        self.path.write_bytes(kernel.canonical(self.projection))
        result = subprocess.run(['python3', '-B', str(VALIDATOR), '--snapshot', str(self.manifest), '--projection', str(self.path)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_empty_nodes_do_not_allow_missing_ac_coverage(self):
        for refs in ([], self.projection['projections'][0]['snapshot_rule_refs'][:1]):
            projection = copy.deepcopy(self.projection)
            projection['projections'][0]['snapshot_rule_refs'] = refs
            errors = self.validate(projection)
            self.assertTrue(any('not projected' in error for error in errors), errors)

    def test_exact_text_id_and_field_required(self):
        for field, value in (('statement', 'Reworded text'), ('node_id', 'ac:unknown'), ('field', 'scope')):
            projection = copy.deepcopy(self.projection)
            projection['projections'][0]['snapshot_rule_refs'][0][field] = value
            self.assertTrue(self.validate(projection))

    def test_repository_refs_cannot_substitute_for_ac_and_checks(self):
        projection = copy.deepcopy(self.projection)
        projection['projections'][0]['snapshot_rule_refs'] = []
        self.assertTrue(self.validate(projection))
        projection['projections'] = []
        self.assertTrue(self.validate(projection))

    def test_ui_requires_new_projection_version(self):
        projection = copy.deepcopy(self.projection)
        projection['schema_version'] = 'check-projection/v0.1'
        self.assertTrue(self.validate(projection))

    def test_task_plan_routing_after_ui_projection(self):
        plan = ready_task_plan(self.root, self.snapshot, self.projection)
        errors = contract.validate_task_plan(plan, self.snapshot, self.manifest, self.projection)
        self.assertEqual(errors, [])

    def test_tampered_payload_rejected_before_projection(self):
        (self.manifest.parent / 'ui-payload.json').write_text('{}\n')
        with self.assertRaises(contract.ValidationError):
            contract.load_verified_snapshot(self.manifest)

    def test_ui_schema_and_runtime_version_match(self):
        schema = json.loads((PACKAGE_ROOT / 'skills/delivery-workflow/references/05-06-delivery-plan.schema.json').read_text())
        definitions = schema['$defs']
        self.assertEqual(definitions['uiCheckProjection']['properties']['schema_version']['const'], contract.UI_PROJECTION_VERSION)
        self.assertEqual(definitions['checkProjection']['properties']['schema_version']['const'], contract.PROJECTION_VERSION)
        self.assertEqual(definitions['uiSnapshotRuleRef']['properties']['field'], {'const': 'acceptance_criteria'})
        self.assertEqual(set(definitions['uiCheckProjection']['required']), contract.PROJECTION_FIELDS)
        self.assertEqual(set(definitions['uiCheckProjection']['properties']), contract.PROJECTION_FIELDS)
        self.assertEqual(set(definitions['uiProjection']['required']), contract.PROJECTION_ITEM_FIELDS)
        self.assertEqual(set(definitions['uiSnapshotRuleRef']['required']), contract.SNAPSHOT_RULE_REF_FIELDS)
        self.assertEqual(definitions['uiSnapshotRuleRef']['properties']['node_id']['pattern'], r'^ac:[a-z0-9][a-z0-9._-]*$')
        self.assertEqual(set(definitions['uiCheckProjection']['properties']['projection_status']['enum']), contract.PROJECTION_STATUSES)
        self.assertEqual(set(definitions['uiProjection']['properties']['layers']['items']['enum']), contract.LAYERS)
