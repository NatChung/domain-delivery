"""Behaviour of the delivery-hub CLI at its public seam: the command line.

Every test drives `hub.py` as a subprocess against a throwaway Hub directory and
observes only exit codes, stdout/stderr and files on disk.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
HUB_CLI = PACKAGE_ROOT / "skills" / "delivery-hub" / "scripts" / "hub.py"
SUBMODULE_NAME = ".domain-delivery"

PASS, FAIL, INVALID = 0, 1, 2


def run(*args, cwd=None):
    return subprocess.run(
        [sys.executable, "-B", str(HUB_CLI), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )


class HubDir:
    """A temporary Git repository standing in for a Delivery Hub."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "hub"
        self.path.mkdir()
        git(self.path.parent, "init", "-q", str(self.path))
        git(self.path, "config", "user.email", "test@example.com")
        git(self.path, "config", "user.name", "test")
        return self

    def __exit__(self, *exc):
        self._tmp.cleanup()

    def init(self, *extra):
        return run(
            "init",
            "--hub", str(self.path),
            "--package", str(PACKAGE_ROOT),
            "--project", "example",
            *extra,
        )

    def commit_all(self, message="wip"):
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "-m", message)

    def lock(self):
        return json.loads((self.path / "workflow.lock").read_text(encoding="utf-8"))


class InitTests(unittest.TestCase):
    def test_init_creates_the_hub_skeleton_and_lock(self):
        with HubDir() as hub:
            result = hub.init()
            self.assertEqual(result.returncode, PASS, result.stderr)
            for relative in (
                "hub.yaml",
                "workflow.lock",
                "CONTEXT-MAP.md",
                "AGENTS.md",
                "CLAUDE.md",
                "docs/domain/INDEX.md",
                "docs/domain/SCHEMA.md",
                "docs/adr/README.md",
                ".claude-plugin/marketplace.json",
                ".agents/plugins/marketplace.json",
            ):
                self.assertTrue(
                    (hub.path / relative).is_file(), f"missing {relative}"
                )

    def test_generated_hub_yaml_carries_the_project_name(self):
        with HubDir() as hub:
            hub.init()
            self.assertIn("project: example", (hub.path / "hub.yaml").read_text())

    def test_both_marketplaces_point_at_the_submodule_path(self):
        with HubDir() as hub:
            hub.init()
            for relative in (
                ".claude-plugin/marketplace.json",
                ".agents/plugins/marketplace.json",
            ):
                content = json.loads((hub.path / relative).read_text(encoding="utf-8"))
                sources = json.dumps(content)
                self.assertIn("./.domain-delivery", sources, relative)

    def test_lock_pins_tag_commit_and_package_digest(self):
        with HubDir() as hub:
            hub.init()
            lock = hub.lock()
            self.assertEqual(lock["version"], (PACKAGE_ROOT / "VERSION").read_text().strip())
            self.assertRegex(lock["commit"], r"^[0-9a-f]{40}$")
            self.assertRegex(lock["package_digest"], r"^sha256:[0-9a-f]{64}$")
            self.assertTrue(lock["tag"])

    def test_init_refuses_when_a_lock_already_exists(self):
        with HubDir() as hub:
            hub.init()
            result = hub.init()
            self.assertEqual(result.returncode, INVALID)
            self.assertIn("upgrade", result.stderr)

    def test_init_adds_only_missing_files_and_never_overwrites(self):
        with HubDir() as hub:
            (hub.path / "CONTEXT-MAP.md").write_text("mine\n", encoding="utf-8")
            hub.init()
            self.assertEqual((hub.path / "CONTEXT-MAP.md").read_text(), "mine\n")

    def test_force_overwrites_template_files_but_not_domain_or_specs(self):
        with HubDir() as hub:
            (hub.path / "CONTEXT-MAP.md").write_text("mine\n", encoding="utf-8")
            (hub.path / "docs" / "domain").mkdir(parents=True)
            (hub.path / "docs" / "domain" / "INDEX.md").write_text("mine\n", encoding="utf-8")
            (hub.path / "specs").mkdir()
            (hub.path / "specs" / "keep.md").write_text("mine\n", encoding="utf-8")
            result = hub.init("--force")
            self.assertEqual(result.returncode, PASS, result.stderr)
            self.assertNotEqual((hub.path / "CONTEXT-MAP.md").read_text(), "mine\n")
            self.assertEqual(
                (hub.path / "docs" / "domain" / "INDEX.md").read_text(), "mine\n"
            )
            self.assertEqual((hub.path / "specs" / "keep.md").read_text(), "mine\n")

    def test_force_does_not_bypass_the_installed_lock(self):
        with HubDir() as hub:
            hub.init()
            result = hub.init("--force")
            self.assertEqual(result.returncode, INVALID)
            self.assertIn("upgrade", result.stderr)

    def test_init_never_deletes_unrelated_files(self):
        with HubDir() as hub:
            (hub.path / "unrelated.txt").write_text("keep\n", encoding="utf-8")
            hub.init("--force")
            self.assertTrue((hub.path / "unrelated.txt").is_file())


if __name__ == "__main__":
    unittest.main()


class DoctorTests(unittest.TestCase):
    def doctor(self, hub):
        return run("doctor", "--hub", str(hub.path), "--package", str(PACKAGE_ROOT))

    def test_doctor_passes_on_a_fresh_install(self):
        # A committed package, so "healthy" cannot be masked by this working
        # copy's own uncommitted edits.
        with FakePackage() as package, HubDir() as hub:
            run("init", "--hub", str(hub.path), "--package", str(package.path),
                "--project", "example")
            result = run("doctor", "--hub", str(hub.path), "--package", str(package.path))
            self.assertEqual(result.returncode, PASS, result.stdout + result.stderr)
            self.assertIn("healthy", result.stdout)

    def test_doctor_reports_a_lock_that_does_not_match_the_installation(self):
        with HubDir() as hub:
            hub.init()
            lock = hub.lock()
            lock["commit"] = "0" * 40
            (hub.path / "workflow.lock").write_text(json.dumps(lock), encoding="utf-8")
            result = self.doctor(hub)
            self.assertEqual(result.returncode, FAIL)
            self.assertIn("commit", result.stdout)

    def test_doctor_reports_a_digest_that_does_not_match_the_lock(self):
        with HubDir() as hub:
            hub.init()
            lock = hub.lock()
            lock["package_digest"] = "sha256:" + "0" * 64
            (hub.path / "workflow.lock").write_text(json.dumps(lock), encoding="utf-8")
            result = self.doctor(hub)
            self.assertEqual(result.returncode, FAIL)
            self.assertIn("digest", result.stdout)

    def test_doctor_reports_missing_hub_files(self):
        with HubDir() as hub:
            hub.init()
            (hub.path / "hub.yaml").unlink()
            result = self.doctor(hub)
            self.assertEqual(result.returncode, FAIL)
            self.assertIn("hub.yaml", result.stdout)

    def test_doctor_changes_nothing(self):
        with HubDir() as hub:
            hub.init()
            hub.commit_all()
            self.doctor(hub)
            self.assertEqual(git(hub.path, "status", "--porcelain").stdout, "")

    def test_doctor_without_a_lock_is_invalid(self):
        with HubDir() as hub:
            result = self.doctor(hub)
            self.assertEqual(result.returncode, INVALID)
            self.assertIn("init", result.stderr)


class UpgradeTests(unittest.TestCase):
    def upgrade(self, hub, package=None):
        target = str(package.path) if package else str(PACKAGE_ROOT)
        return run("upgrade", "--hub", str(hub.path), "--package", target)

    def test_upgrade_refuses_a_dirty_working_tree(self):
        with HubDir() as hub:
            hub.init()
            hub.commit_all()
            (hub.path / "CONTEXT-MAP.md").write_text("edited\n", encoding="utf-8")
            result = self.upgrade(hub)
            self.assertEqual(result.returncode, INVALID)
            self.assertIn("dirty", result.stderr)

    def test_upgrade_without_a_lock_is_invalid(self):
        with HubDir() as hub:
            result = self.upgrade(hub)
            self.assertEqual(result.returncode, INVALID)
            self.assertIn("init", result.stderr)

    def test_upgrade_on_a_clean_hub_refreshes_the_lock(self):
        with FakePackage() as package, HubDir() as hub:
            run("init", "--hub", str(hub.path), "--package", str(package.path),
                "--project", "example")
            hub.commit_all()
            result = self.upgrade(hub, package)
            self.assertEqual(result.returncode, PASS, result.stderr)
            self.assertIn("snapshots and evidence were not touched", result.stdout)

    def test_upgrade_leaves_snapshots_and_evidence_alone(self):
        with HubDir() as hub:
            hub.init()
            (hub.path / "specs").mkdir()
            (hub.path / "specs" / "frozen.json").write_text("{}\n", encoding="utf-8")
            (hub.path / "evidence").mkdir()
            (hub.path / "evidence" / "ledger.jsonl").write_text("{}\n", encoding="utf-8")
            hub.commit_all()
            self.upgrade(hub)
            self.assertEqual((hub.path / "specs" / "frozen.json").read_text(), "{}\n")
            self.assertEqual((hub.path / "evidence" / "ledger.jsonl").read_text(), "{}\n")


class PackageDigestTests(unittest.TestCase):
    def digest(self, hub):
        hub.init()
        return hub.lock()["package_digest"]

    def test_digest_is_stable_across_runs(self):
        with HubDir() as first, HubDir() as second:
            self.assertEqual(self.digest(first), self.digest(second))

    def test_digest_changes_when_a_released_file_changes(self):
        with HubDir() as hub:
            before = self.digest(hub)
        marker = PACKAGE_ROOT / "template" / "CONTEXT-MAP.md"
        original = marker.read_bytes()
        try:
            marker.write_bytes(original + b"\n<!-- digest probe -->\n")
            with HubDir() as hub:
                after = self.digest(hub)
        finally:
            marker.write_bytes(original)
        self.assertNotEqual(before, after)


class FakePackage:
    """A minimal package directory, used to exercise migrations."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "package"
        (self.path / "migrations").mkdir(parents=True)
        (self.path / "VERSION").write_text("0.2.0\n", encoding="utf-8")
        shutil.copytree(PACKAGE_ROOT / "template", self.path / "template")
        git(self.path.parent, "init", "-q", str(self.path))
        git(self.path, "config", "user.email", "test@example.com")
        git(self.path, "config", "user.name", "test")
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "-m", "package")
        return self

    def __exit__(self, *exc):
        self._tmp.cleanup()

    def add_migration(self, name, body):
        directory = self.path / "migrations" / name
        directory.mkdir()
        (directory / "migrate.py").write_text(body, encoding="utf-8")
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "-m", name)


TOUCH_MIGRATION = """
def migrate(hub_root):
    marker = hub_root / "migrated-{tag}.txt"
    marker.write_text("{tag}\\n", encoding="utf-8")
    return ["wrote " + marker.name]
"""


class MigrationTests(unittest.TestCase):
    def install(self, hub, package):
        return run(
            "init", "--hub", str(hub.path), "--package", str(package.path),
            "--project", "example",
        )

    def test_init_records_existing_migrations_as_already_applied(self):
        with FakePackage() as package:
            package.add_migration("0002-example", TOUCH_MIGRATION.format(tag="a"))
            with HubDir() as hub:
                self.install(hub, package)
                self.assertEqual(hub.lock()["migrations_applied"], ["0002-example"])
                self.assertFalse((hub.path / "migrated-a.txt").exists())

    def test_upgrade_runs_pending_migrations_in_order(self):
        with FakePackage() as package:
            with HubDir() as hub:
                self.install(hub, package)
                hub.commit_all()
                package.add_migration("0002-first", TOUCH_MIGRATION.format(tag="first"))
                package.add_migration("0003-second", TOUCH_MIGRATION.format(tag="second"))
                result = run(
                    "upgrade", "--hub", str(hub.path), "--package", str(package.path)
                )
                self.assertEqual(result.returncode, PASS, result.stderr)
                self.assertLess(
                    result.stdout.index("0002-first"), result.stdout.index("0003-second")
                )
                self.assertTrue((hub.path / "migrated-first.txt").is_file())
                self.assertTrue((hub.path / "migrated-second.txt").is_file())
                self.assertEqual(
                    hub.lock()["migrations_applied"], ["0002-first", "0003-second"]
                )

    def test_a_migration_is_not_run_twice(self):
        with FakePackage() as package:
            with HubDir() as hub:
                self.install(hub, package)
                hub.commit_all()
                package.add_migration("0002-once", TOUCH_MIGRATION.format(tag="once"))
                run("upgrade", "--hub", str(hub.path), "--package", str(package.path))
                (hub.path / "migrated-once.txt").unlink()
                hub.commit_all("after first upgrade")
                run("upgrade", "--hub", str(hub.path), "--package", str(package.path))
                self.assertFalse((hub.path / "migrated-once.txt").exists())

    def test_doctor_reports_a_pending_migration(self):
        with FakePackage() as package:
            with HubDir() as hub:
                self.install(hub, package)
                package.add_migration("0002-pending", TOUCH_MIGRATION.format(tag="p"))
                result = run(
                    "doctor", "--hub", str(hub.path), "--package", str(package.path)
                )
                self.assertEqual(result.returncode, FAIL)
                self.assertIn("pending migration: 0002-pending", result.stdout)


KERNEL_CLI = PACKAGE_ROOT / "kernel" / "scripts" / "kernel.py"


def kernel(*args, cwd=None):
    return subprocess.run(
        [sys.executable, "-B", str(KERNEL_CLI), *args],
        capture_output=True, text=True, cwd=str(cwd) if cwd else None,
    )


class InstalledHubSmokeTests(unittest.TestCase):
    """A freshly created Hub must be usable end to end without editing anything."""

    def test_a_fresh_hub_compiles_and_gates_its_empty_graph(self):
        with HubDir() as hub:
            hub.init()
            index = hub.path / "domain-index" / "index.json"
            index.parent.mkdir(parents=True, exist_ok=True)
            compiled = kernel(
                "compile", "--source", str(hub.path / "docs" / "domain"),
                "--output", str(index),
            )
            self.assertEqual(compiled.returncode, PASS, compiled.stderr)
            gated = kernel("gate-index", "--index", str(index))
            self.assertEqual(gated.returncode, PASS, gated.stdout + gated.stderr)

    def test_the_synthetic_example_graph_compiles_and_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / "index.json"
            compiled = kernel(
                "compile", "--source", str(PACKAGE_ROOT / "examples" / "domain-nodes"),
                "--output", str(index),
            )
            self.assertEqual(compiled.returncode, PASS, compiled.stderr)
            gated = kernel("gate-index", "--index", str(index))
            self.assertEqual(gated.returncode, PASS, gated.stdout + gated.stderr)

    def test_no_template_file_still_carries_the_placeholder(self):
        with HubDir() as hub:
            hub.init()
            for path in hub.path.rglob("*"):
                if path.is_file() and ".git" not in path.parts:
                    self.assertNotIn(
                        "{{PROJECT}}", path.read_text(encoding="utf-8"),
                        f"placeholder left in {path.relative_to(hub.path)}",
                    )


class UpgradeDirtinessTests(unittest.TestCase):
    """Moving the submodule is how an upgrade starts, so it cannot be the thing
    that blocks one. Every other uncommitted change still must."""

    def setUp(self):
        self.package = FakePackage().__enter__()

    def tearDown(self):
        self.package.__exit__(None, None, None)

    def test_upgrade_proceeds_when_only_the_submodule_pointer_moved(self):
        with HubDir() as hub:
            run("init", "--hub", str(hub.path), "--package", str(self.package.path),
                "--project", "example")
            hub.commit_all()
            (hub.path / ".domain-delivery").mkdir()
            (hub.path / ".domain-delivery" / "VERSION").write_text("0.9.9\n", encoding="utf-8")
            git(hub.path, "add", "-A")
            result = run(
                "upgrade", "--hub", str(hub.path), "--package", str(self.package.path)
            )
            self.assertEqual(result.returncode, PASS, result.stderr)

    def test_upgrade_proceeds_when_the_submodule_change_is_unstaged(self):
        """An unstaged entry starts with a space in porcelain output, which is
        exactly where naive parsing loses the first character of the path."""
        with HubDir() as hub:
            run("init", "--hub", str(hub.path), "--package", str(self.package.path),
                "--project", "example")
            (hub.path / ".domain-delivery").mkdir()
            (hub.path / ".domain-delivery" / "VERSION").write_text("0.9.9\n", encoding="utf-8")
            git(hub.path, "add", "-A")
            hub.commit_all()
            (hub.path / ".domain-delivery" / "VERSION").write_text("1.0.0\n", encoding="utf-8")
            self.assertTrue(
                git(hub.path, "status", "--porcelain").stdout.startswith(" ")
            )
            result = run(
                "upgrade", "--hub", str(hub.path), "--package", str(self.package.path)
            )
            self.assertEqual(result.returncode, PASS, result.stderr)

    def test_upgrade_still_refuses_other_uncommitted_changes(self):
        with HubDir() as hub:
            run("init", "--hub", str(hub.path), "--package", str(self.package.path),
                "--project", "example")
            hub.commit_all()
            (hub.path / ".domain-delivery").mkdir()
            (hub.path / ".domain-delivery" / "VERSION").write_text("0.9.9\n", encoding="utf-8")
            (hub.path / "CONTEXT-MAP.md").write_text("edited\n", encoding="utf-8")
            git(hub.path, "add", "-A")
            result = run(
                "upgrade", "--hub", str(hub.path), "--package", str(self.package.path)
            )
            self.assertEqual(result.returncode, INVALID)
            self.assertIn("CONTEXT-MAP.md", result.stderr)


class DigestCoverageTests(unittest.TestCase):
    """workflow.lock exists to notice a modified installation. Every released
    file must therefore be inside the digest, not just the executable ones."""

    def digest_after_touching(self, relative):
        with HubDir() as hub:
            hub.init()
            before = hub.lock()["package_digest"]
        target = PACKAGE_ROOT / relative
        original = target.read_bytes()
        try:
            target.write_bytes(original + b"\n<!-- digest probe -->\n")
            with HubDir() as hub:
                hub.init()
                after = hub.lock()["package_digest"]
        finally:
            target.write_bytes(original)
        return before, after

    def test_editing_the_method_document_changes_the_digest(self):
        before, after = self.digest_after_touching("docs/workflow.md")
        self.assertNotEqual(before, after)

    def test_editing_a_method_decision_record_changes_the_digest(self):
        before, after = self.digest_after_touching(
            "docs/adr/0008-distribute-shared-workflow-as-pinned-submodule.md"
        )
        self.assertNotEqual(before, after)

    def test_editing_an_example_changes_the_digest(self):
        before, after = self.digest_after_touching("examples/README.md")
        self.assertNotEqual(before, after)

    def test_doctor_reports_an_untracked_file_inside_the_installation(self):
        with HubDir() as hub:
            hub.init()
            stray = PACKAGE_ROOT / "STRAY-PROBE.txt"
            stray.write_text("not tracked\n", encoding="utf-8")
            try:
                result = run(
                    "doctor", "--hub", str(hub.path), "--package", str(PACKAGE_ROOT)
                )
            finally:
                stray.unlink()
            self.assertEqual(result.returncode, FAIL, result.stdout)
            self.assertIn("STRAY-PROBE.txt", result.stdout)


class InstallationIntegrityTests(unittest.TestCase):
    """The lock exists to record bytes nobody edited by hand. A command that
    blesses a hand-edited installation destroys that guarantee."""

    def install(self, hub, package):
        return run(
            "init", "--hub", str(hub.path), "--package", str(package.path),
            "--project", "example",
        )

    def test_upgrade_refuses_when_the_installation_itself_is_modified(self):
        with FakePackage() as package, HubDir() as hub:
            self.install(hub, package)
            hub.commit_all()
            target = package.path / "template" / "CONTEXT-MAP.md"
            target.write_text(target.read_text(encoding="utf-8") + "edited\n", encoding="utf-8")
            result = run(
                "upgrade", "--hub", str(hub.path), "--package", str(package.path)
            )
            self.assertEqual(result.returncode, INVALID, result.stdout)
            self.assertIn("CONTEXT-MAP.md", result.stderr)

    def test_doctor_reports_a_modified_installation_rather_than_blessing_it(self):
        with FakePackage() as package, HubDir() as hub:
            self.install(hub, package)
            target = package.path / "template" / "CONTEXT-MAP.md"
            target.write_text(target.read_text(encoding="utf-8") + "edited\n", encoding="utf-8")
            result = run(
                "doctor", "--hub", str(hub.path), "--package", str(package.path)
            )
            self.assertEqual(result.returncode, FAIL, result.stdout)


class DoctorIsReadOnlyTests(unittest.TestCase):
    """ADR 0008 calls doctor read-only. Nothing it does may write, and it must
    not reach the network on the user's behalf."""

    def test_doctor_reports_a_missing_installation_instead_of_fetching_it(self):
        with HubDir() as hub:
            hub.init()
            hub.commit_all()
            result = run("doctor", "--hub", str(hub.path))
            self.assertEqual(result.returncode, FAIL, result.stdout + result.stderr)
            self.assertIn(".domain-delivery", result.stdout)
            self.assertFalse((hub.path / ".domain-delivery").exists())
            self.assertEqual(git(hub.path, "status", "--porcelain").stdout, "")


class GitlinkAgreementTests(unittest.TestCase):
    """The lock and the commit a fresh clone would produce must agree. If they
    can drift while doctor says healthy, the lock stops describing the Hub."""

    def hub_with_real_submodule(self, package, hub):
        git(hub.path, "-c", "protocol.file.allow=always", "submodule", "add",
            "--name", SUBMODULE_NAME, str(package.path), SUBMODULE_NAME)
        run("init", "--hub", str(hub.path), "--project", "example")
        hub.commit_all("install")

    def test_doctor_reports_a_lock_that_disagrees_with_the_recorded_gitlink(self):
        with FakePackage() as package, HubDir() as hub:
            self.hub_with_real_submodule(package, hub)
            package.add_migration("0002-later", TOUCH_MIGRATION.format(tag="later"))
            head = git(package.path, "rev-parse", "HEAD").stdout.strip()
            git(hub.path / SUBMODULE_NAME, "fetch", "-q", "origin")
            git(hub.path / SUBMODULE_NAME, "checkout", "-q", head)
            run("upgrade", "--hub", str(hub.path))
            result = run("doctor", "--hub", str(hub.path))
            self.assertEqual(result.returncode, FAIL, result.stdout)
            self.assertIn("gitlink", result.stdout)

    def test_doctor_passes_once_the_gitlink_move_is_committed(self):
        with FakePackage() as package, HubDir() as hub:
            self.hub_with_real_submodule(package, hub)
            package.add_migration("0002-later", TOUCH_MIGRATION.format(tag="later"))
            head = git(package.path, "rev-parse", "HEAD").stdout.strip()
            git(hub.path / SUBMODULE_NAME, "fetch", "-q", "origin")
            git(hub.path / SUBMODULE_NAME, "checkout", "-q", head)
            run("upgrade", "--hub", str(hub.path))
            hub.commit_all("move the submodule and the lock together")
            result = run("doctor", "--hub", str(hub.path))
            self.assertEqual(result.returncode, PASS, result.stdout)


class VersionDirectionTests(unittest.TestCase):
    """A command named upgrade must not report a downgrade as an upgrade."""

    def test_moving_to_a_lower_version_is_not_called_an_upgrade(self):
        with FakePackage() as package, HubDir() as hub:
            run("init", "--hub", str(hub.path), "--package", str(package.path),
                "--project", "example")
            hub.commit_all()
            (package.path / "VERSION").write_text("0.1.0\n", encoding="utf-8")
            git(package.path, "add", "-A")
            git(package.path, "commit", "-q", "-m", "older release")
            result = run(
                "upgrade", "--hub", str(hub.path), "--package", str(package.path)
            )
            self.assertEqual(result.returncode, PASS, result.stderr)
            self.assertNotIn("upgraded", result.stdout)
            self.assertIn("downgrade", result.stdout.lower())
