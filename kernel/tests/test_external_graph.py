"""Public CLI contract for independent graph and delivery repositories."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "kernel/scripts/kernel.py"


class ExternalGraphTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.graph = self.root / "graph"
        self.hub = self.root / "hub"
        for repo in (self.graph, self.hub):
            repo.mkdir()
            self.git(repo, "init", "-q")
            self.git(repo, "config", "user.email", "test@example.com")
            self.git(repo, "config", "user.name", "Test")
        shutil.copytree(ROOT / "examples/domain-nodes", self.graph / "docs/domain")
        self.git(self.graph, "add", ".")
        self.git(self.graph, "commit", "-qm", "Graph fixture")
        self.commit = self.git(self.graph, "rev-parse", "HEAD").strip()
        (self.hub / "checker.py").write_text("print('pass')\n")
        self.git(self.hub, "add", ".")
        self.git(self.hub, "commit", "-qm", "Delivery fixture")
        self.index = self.hub / "index.json"
        self.run_cli("compile", "--source", self.graph / "docs/domain", "--output", self.index)
        self.manifest = self.hub / "snapshot/snapshot-manifest.json"
        self.ledger = self.hub / "ledger.jsonl"
        self.output = self.hub / "output.txt"
        self.output.write_text("pass\n")

    def git(self, repo, *args):
        return subprocess.run(["git", *args], cwd=repo, check=True, text=True, capture_output=True).stdout

    def run_cli(self, *args, expected=0):
        result = subprocess.run([sys.executable, "-B", str(CLI), *map(str, args)],
                                cwd=self.hub, text=True, capture_output=True)
        self.assertEqual(result.returncode, expected, result.stderr)
        return result

    def freeze(self, output=None, resolver=True):
        args = ["freeze", "--feature", "reminder-digest", "--version", "v1",
                "--index", self.index, "--node", "capability:reminder",
                "--graph-commit", self.commit, "--delivery-lane", "server",
                "--repository", "reminder-service", "--required-check", "reminder-service/unit-tests",
                "--trusted-attestor", "ci:test-runner", "--output", output or self.manifest.parent]
        if resolver:
            args.extend(["--graph-repo", self.graph])
        return self.run_cli(*args)

    def test_external_graph_supports_freeze_through_verified_evidence(self):
        self.freeze()
        common = ["--snapshot", self.manifest, "--graph-repo", self.graph]
        self.run_cli("verify-snapshot", *common)
        self.run_cli("drift", *common, "--index", self.index)
        result = self.run_cli("record-result", *common, "--ledger", self.ledger,
                             "--repository-id", "reminder-service", "--check-id", "unit-tests",
                             "--exit-code", 0, "--repo-path", self.hub,
                             "--checker-file", self.hub / "checker.py", "--output-file", self.output,
                             "--performed-by", "agent:implementation")
        self.run_cli("declare-attestation", *common, "--ledger", self.ledger,
                     "--result-hash", result.stdout.strip(), "--declared-by", "ci:test-runner",
                     "--declaration-mode", "ci_declaration", "--attestation-file", self.output)
        self.run_cli("verify-evidence", *common, "--ledger", self.ledger)

    def test_external_snapshot_rejects_missing_or_wrong_graph_repository(self):
        self.freeze()
        for resolver in ([], ["--graph-repo", self.hub], ["--graph-repo", self.root / "absent"]):
            with self.subTest(resolver=resolver):
                self.run_cli("verify-snapshot", "--snapshot", self.manifest, *resolver, expected=2)

    def test_same_repository_resolution_remains_compatible(self):
        self.index = self.graph / "index.json"
        self.run_cli("compile", "--source", self.graph / "docs/domain", "--output", self.index)
        self.manifest = self.graph / "snapshot/snapshot-manifest.json"
        self.freeze(resolver=False)
        self.run_cli("verify-snapshot", "--snapshot", self.manifest)

    def test_pinned_commit_ignores_later_worktree_changes_and_accepts_a_clone(self):
        self.freeze()
        (self.graph / "docs/domain/capabilities/reminder.md").write_text("uncommitted replacement")
        self.run_cli("verify-snapshot", "--snapshot", self.manifest, "--graph-repo", self.graph)
        clone = self.root / "clone"
        self.git(self.root, "clone", "-q", str(self.graph), str(clone))
        self.run_cli("verify-snapshot", "--snapshot", self.manifest, "--graph-repo", clone)
