import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_kernel import kernel, frozen, required_checks, result_entry, attestation_entry

FIXTURE = Path(__file__).parent / 'fixtures' / 'ui-accepted-request.json'
CLI = Path(__file__).resolve().parents[1] / 'scripts' / 'kernel.py'


def accepted_request():
    return json.loads(FIXTURE.read_text())


def ui_frozen(request=None, **overrides):
    args = dict(feature='dialog-copy', version='v1', index=None, root_ids=[],
                delivery_lanes=['web'], repositories=['sample-web'],
                required_checks=required_checks('sample-web'), graph_commit=None,
                kind='ui', accepted_request=accepted_request() if request is None else request)
    args.update(overrides)
    return kernel.freeze_snapshot(**args)


class UISnapshotTests(unittest.TestCase):
    def test_roundtrip_without_graph_and_immutable_publication(self):
        snapshot, bundle, payload = ui_frozen()
        self.assertEqual(kernel.validate_snapshot(snapshot), [])
        self.assertEqual(snapshot['nodes'], [])
        self.assertNotIn('graph_commit', snapshot)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'v1'
            kernel.publish_snapshot(output, snapshot, bundle, payload)
            self.assertEqual(kernel.verify_snapshot_against_graph(snapshot, output / 'snapshot-manifest.json'), [])
            with self.assertRaises(kernel.KernelError):
                kernel.publish_snapshot(output, snapshot, bundle, payload)

    def test_cli_freeze_verify_no_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'v1'
            args = ['python3', '-B', str(CLI), 'freeze', '--kind', 'ui', '--feature', 'dialog-copy', '--version', 'v1', '--accepted-request', str(FIXTURE), '--delivery-lane', 'web', '--repository', 'sample-web', '--required-check', 'sample-web/unit-tests', '--trusted-attestor', 'ci:test-runner', '--output', str(output)]
            result = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run(['python3', '-B', str(CLI), 'verify-snapshot', '--snapshot', str(output / 'snapshot-manifest.json')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            for extra in (['--node', 'capability:sample'], ['--graph-commit', 'a' * 40], ['--index', 'absent.json'], ['--graph-repo', tmp]):
                result = subprocess.run(args + extra, capture_output=True, text=True)
                self.assertEqual(result.returncode, kernel.INVALID, result.stderr)

    def test_acceptance_missing_or_agent_or_role(self):
        for who in (None, '', 'agent:reviewer', 'Agent:reviewer', 'role:reviewer', 'reviewer'):
            with self.subTest(who=who):
                request = accepted_request()
                request['accepted_by'] = who
                with self.assertRaises(kernel.KernelError):
                    ui_frozen(request)
        request = accepted_request()
        del request['accepted_by']
        with self.assertRaises(kernel.KernelError):
            ui_frozen(request)

    def test_acceptance_date_source_and_request_required(self):
        for field, value in (('accepted_at', '2026-09-01'), ('source', ' '), ('request', ''), ('request_digest', 'sha256:' + '0' * 64)):
            request = accepted_request()
            request[field] = value
            with self.subTest(field=field), self.assertRaises(kernel.KernelError):
                ui_frozen(request)

    def test_ac_digest_and_unique_ids(self):
        request = accepted_request()
        request['acceptance_criteria'][0]['text'] = 'Changed criterion'
        with self.assertRaisesRegex(kernel.KernelError, 'criterion digest mismatch'):
            ui_frozen(request)
        request = accepted_request()
        request['acceptance_criteria'][1]['id'] = 'ac:1'
        with self.assertRaisesRegex(kernel.KernelError, 'duplicate'):
            ui_frozen(request)
        request['acceptance_criteria'] = []
        with self.assertRaises(kernel.KernelError):
            ui_frozen(request)

    def test_missing_checks_attestors_and_repo_coverage(self):
        for overrides in ({'required_checks': []}, {'required_checks': [{'repository_id': 'sample-web', 'check_id': 'unit-tests', 'trusted_attestors': []}]}, {'repositories': ['sample-web', 'sample-other']}, {'delivery_lanes': []}):
            with self.subTest(overrides=overrides), self.assertRaises(kernel.KernelError):
                ui_frozen(**overrides)

    def test_scope_exclusions_and_category(self):
        for field in kernel.UI_SCOPE_FIELDS:
            for value in (True, None, 0, 'false'):
                request = accepted_request()
                request['scope'][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(kernel.KernelError):
                    ui_frozen(request)
        for field, value in (('category', 'business'), ('rationale', '')):
            request = accepted_request()
            request['scope'][field] = value
            with self.assertRaises(kernel.KernelError):
                ui_frozen(request)

    def test_graph_inputs_and_nodes_rejected(self):
        for overrides in ({'root_ids': ['capability:sample']}, {'graph_commit': 'a' * 40}, {'index': {}}):
            with self.assertRaises(kernel.KernelError):
                ui_frozen(**overrides)
        snapshot, _, _ = ui_frozen()
        for field, value in (('nodes', [{'id': 'capability:sample'}]), ('root_nodes', ['capability:sample']), ('graph_commit', 'a' * 40), ('domain_bundle', {})):
            changed = copy.deepcopy(snapshot)
            changed[field] = value
            changed['snapshot_digest'] = kernel.digest_json({k:v for k,v in changed.items() if k != 'snapshot_digest'})
            self.assertTrue(kernel.validate_snapshot(changed))

    def test_verify_detects_each_artifact_tampering(self):
        snapshot, bundle, payload = ui_frozen()
        for file in ('UI.md', 'ui-payload.json', 'snapshot-manifest.json'):
            with self.subTest(file=file), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / 'v1'
                kernel.publish_snapshot(output, snapshot, bundle, payload)
                path = output / file
                if file == 'snapshot-manifest.json':
                    changed = copy.deepcopy(snapshot)
                    changed['accepted_request']['acceptance_criteria'][0]['text'] = 'Altered'
                    path.write_bytes(kernel.canonical(changed))
                else:
                    path.write_text('{}\n')
                loaded = kernel.load_json(output / 'snapshot-manifest.json')
                self.assertTrue(kernel.verify_snapshot_against_graph(loaded, output / 'snapshot-manifest.json'))

    def test_redigested_request_with_stale_payload_rejected(self):
        snapshot, bundle, payload = ui_frozen()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'v1'
            kernel.publish_snapshot(output, snapshot, bundle, payload)
            changed = copy.deepcopy(snapshot)
            changed['accepted_request']['source'] = 'document:other'
            new_bundle = kernel.render_ui_bundle(changed['feature'], changed['snapshot_version'], changed['accepted_request'])
            changed['ui_bundle']['digest'] = kernel.digest_bytes(new_bundle.encode())
            changed['ui_bundle']['payload_digest'] = kernel.digest_json(changed['accepted_request'])
            changed['snapshot_digest'] = kernel.digest_json({k:v for k,v in changed.items() if k != 'snapshot_digest'})
            self.assertTrue(kernel.verify_snapshot_against_graph(changed, output / 'snapshot-manifest.json'))

    def test_caller_mutation_does_not_mutate_frozen_request(self):
        request = accepted_request()
        snapshot, _, _ = ui_frozen(request)
        request['source'] = 'document:changed'
        self.assertEqual(kernel.validate_snapshot(snapshot), [])

    def test_evidence_requires_same_trusted_attestation(self):
        snapshot, _, _ = ui_frozen()
        result = result_entry(snapshot, repository='sample-web')
        self.assertTrue(kernel.verify_evidence(snapshot, [result]))
        self.assertEqual(kernel.verify_evidence(snapshot, [result, attestation_entry(snapshot, result)]), [])

    def test_domain_default_is_byte_compatible_and_explicit_kind_valid(self):
        snapshot, bundle, payload = frozen()
        # Golden bytes from the v0.4.0 implementation: default domain output is unchanged.
        self.assertEqual(snapshot['snapshot_digest'], 'sha256:314ca028250f43c76beaa60d092bea9513859ad8c597cdeaa58fc68e170ffe0c')
        self.assertEqual(kernel.digest_bytes(bundle.encode()), 'sha256:a6e083e7098a3555001b88dba29f87017bd463869ce1fe18287a42b0126860d7')
        self.assertEqual(kernel.digest_json(payload), 'sha256:db11d7d0bf7d699bd096d1908dd025884447423ac870baf9d1b5cf384f7535e1')
        self.assertNotIn('kind', snapshot)
        self.assertEqual(snapshot['schema_version'], 1)
        snapshot['kind'] = 'domain'
        snapshot['snapshot_digest'] = kernel.digest_json({k:v for k,v in snapshot.items() if k != 'snapshot_digest'})
        self.assertEqual(kernel.validate_snapshot(snapshot), [])
        snapshot['kind'] = 'other'
        self.assertTrue(kernel.validate_snapshot(snapshot))

    def test_new_version_supersedes_and_graph_drift_not_applicable(self):
        prior, _, _ = ui_frozen()
        next_snapshot, _, _ = ui_frozen(version='v2', supersedes=prior['snapshot_digest'])
        self.assertEqual(next_snapshot['supersedes'], prior['snapshot_digest'])
        with self.assertRaises(kernel.KernelError):
            ui_frozen(supersedes='invalid')
        with self.assertRaises(kernel.KernelError):
            kernel.detect_drift(prior, {})

    def test_manifest_validation_routing_and_schema_version(self):
        snapshot, _, _ = ui_frozen()
        for field, value in (('required_checks', []), ('repositories', []), ('schema_version', 1), ('kind', 'domain')):
            changed = copy.deepcopy(snapshot)
            changed[field] = value
            self.assertTrue(kernel.validate_snapshot(changed))

    def test_schema_keeps_domain_minimums_and_ui_exclusions(self):
        schema = json.loads((CLI.parents[1] / 'schema/feature-snapshot.schema.json').read_text())
        domain = schema['$defs']['domainSnapshot']
        ui = schema['$defs']['uiSnapshot']
        self.assertEqual(domain['properties']['schema_version'], {'const': 1})
        for field in ('nodes', 'root_nodes'):
            self.assertEqual(domain['properties'][field]['minItems'], 1)
            self.assertEqual(ui['properties'][field]['maxItems'], 0)
        for field in ('graph_commit', 'graph_source_root', 'graph_index_digest'):
            self.assertIn(field, domain['required'])
            self.assertNotIn(field, ui['properties'])
        self.assertFalse(ui['additionalProperties'])
        self.assertEqual(ui['properties']['kind'], {'const': 'ui'})
        snapshot, _, _ = ui_frozen()
        self.assertEqual(set(ui['required']), set(snapshot))
        accepted_schema = ui['properties']['accepted_request']
        self.assertEqual(set(accepted_schema['required']), set(snapshot['accepted_request']))
        self.assertEqual(set(accepted_schema['properties']), set(snapshot['accepted_request']))
        scope_schema = accepted_schema['properties']['scope']
        self.assertEqual(set(scope_schema['required']), kernel.UI_SCOPE_FIELDS | {'category', 'rationale'})
        self.assertEqual(set(scope_schema['properties']['category']['enum']), {'ui', 'copy', 'style', 'explicit_bug'})
        for field in kernel.UI_SCOPE_FIELDS:
            self.assertEqual(scope_schema['properties'][field], {'const': False})
        criterion = accepted_schema['properties']['acceptance_criteria']['items']
        self.assertEqual(set(criterion['required']), {'id', 'text', 'digest'})
        self.assertEqual(criterion['properties']['id']['pattern'], r'^ac:[a-z0-9][a-z0-9._-]*$')
        self.assertEqual(ui['properties']['required_checks'], domain['properties']['required_checks'])
        self.assertEqual(ui['properties']['delivery_lanes'], domain['properties']['delivery_lanes'])
        self.assertEqual(ui['properties']['repositories'], domain['properties']['repositories'])
