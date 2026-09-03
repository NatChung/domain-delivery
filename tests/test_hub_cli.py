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
        # This working copy is usually sitting on an untagged development
        # commit, and whether it is tagged has nothing to do with what these
        # tests assert. ReleaseIdentityTests covers the tag rule itself.
        return run(
            "init",
            "--hub", str(self.path),
            "--package", str(PACKAGE_ROOT),
            "--project", "example",
            "--allow-untagged",
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

    def test_lock_records_the_release_tag_when_there_is_one(self):
        with FakePackage() as package, HubDir() as hub:
            run("init", "--hub", str(hub.path), "--package", str(package.path),
                "--project", "example")
            self.assertEqual(hub.lock()["tag"], "v0.2.0")

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
        self.patch = 0
        (self.path / "VERSION").write_text("0.2.0\n", encoding="utf-8")
        shutil.copytree(PACKAGE_ROOT / "template", self.path / "template")
        git(self.path.parent, "init", "-q", str(self.path))
        git(self.path, "config", "user.email", "test@example.com")
        git(self.path, "config", "user.name", "test")
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "-m", "package")
        git(self.path, "tag", "-a", "v0.2.0", "-m", "v0.2.0")
        return self

    def release(self, version, message="release"):
        """Commit the current tree as a tagged release, like a real upstream."""
        (self.path / "VERSION").write_text(version + "\n", encoding="utf-8")
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "-m", message)
        git(self.path, "tag", "-a", f"v{version}", "-m", f"v{version}")

    def __exit__(self, *exc):
        self._tmp.cleanup()

    def add_migration(self, name, body):
        directory = self.path / "migrations" / name
        directory.mkdir()
        (directory / "migrate.py").write_text(body, encoding="utf-8")
        self.patch += 1
        self.release(f"0.2.{self.patch}", name)


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
            package.release("0.1.0", "older release")
            result = run(
                "upgrade", "--hub", str(hub.path), "--package", str(package.path)
            )
            self.assertEqual(result.returncode, PASS, result.stderr)
            self.assertNotIn("upgraded", result.stdout)
            self.assertIn("downgrade", result.stdout.lower())


REWRITE_MIGRATION = """
def migrate(hub_root):
    for relative in ("specs/frozen/snapshot-manifest.json",
                     "evidence/run-001/check-ledger.jsonl"):
        target = hub_root / relative
        if target.exists():
            target.write_text("rewritten\\n", encoding="utf-8")
    return ["rewrote frozen artifacts"]
"""


class ReleaseIdentityTests(unittest.TestCase):
    """workflow.lock pins a release. A commit nobody tagged is not one."""

    def test_init_refuses_an_untagged_commit(self):
        with FakePackage() as package, HubDir() as hub:
            (package.path / "NOTES.md").write_text("wip\n", encoding="utf-8")
            git(package.path, "add", "-A")
            git(package.path, "commit", "-q", "-m", "untagged work")
            result = run("init", "--hub", str(hub.path),
                         "--package", str(package.path), "--project", "example")
            self.assertEqual(result.returncode, INVALID, result.stdout)
            self.assertIn("tag", result.stderr)

    def test_init_writes_nothing_when_it_refuses_an_untagged_commit(self):
        """A refusal that already installed adapters is not a refusal."""
        with FakePackage() as package, HubDir() as hub:
            (package.path / "NOTES.md").write_text("wip\n", encoding="utf-8")
            git(package.path, "add", "-A")
            git(package.path, "commit", "-q", "-m", "untagged work")
            before = sorted(p.name for p in hub.path.iterdir())
            result = run("init", "--hub", str(hub.path),
                         "--package", str(package.path), "--project", "example")
            self.assertEqual(result.returncode, INVALID, result.stdout)
            self.assertEqual(
                sorted(p.name for p in hub.path.iterdir()), before,
                "an untagged package installed the template before being refused",
            )

    def test_forced_init_overwrites_nothing_when_it_refuses(self):
        with FakePackage() as package, HubDir() as hub:
            (package.path / "NOTES.md").write_text("wip\n", encoding="utf-8")
            git(package.path, "add", "-A")
            git(package.path, "commit", "-q", "-m", "untagged work")
            adapter = hub.path / "AGENTS.md"
            adapter.write_text("hub-owned\n", encoding="utf-8")
            result = run("init", "--hub", str(hub.path), "--force",
                         "--package", str(package.path), "--project", "example")
            self.assertEqual(result.returncode, INVALID, result.stdout)
            self.assertEqual(adapter.read_text(encoding="utf-8"), "hub-owned\n")

    def test_init_refuses_a_tag_that_disagrees_with_VERSION(self):
        with FakePackage() as package, HubDir() as hub:
            (package.path / "VERSION").write_text("9.9.9\n", encoding="utf-8")
            git(package.path, "add", "-A")
            git(package.path, "commit", "-q", "-m", "bump without retagging")
            git(package.path, "tag", "-a", "v0.3.0", "-m", "v0.3.0")
            result = run("init", "--hub", str(hub.path),
                         "--package", str(package.path), "--project", "example")
            self.assertEqual(result.returncode, INVALID, result.stdout)

    def test_untagged_use_is_possible_but_must_be_asked_for(self):
        with FakePackage() as package, HubDir() as hub:
            (package.path / "NOTES.md").write_text("wip\n", encoding="utf-8")
            git(package.path, "add", "-A")
            git(package.path, "commit", "-q", "-m", "untagged work")
            result = run("init", "--hub", str(hub.path), "--package", str(package.path),
                         "--project", "example", "--allow-untagged")
            self.assertEqual(result.returncode, PASS, result.stderr)
            self.assertIsNone(hub.lock()["tag"])

    def test_doctor_reports_an_untagged_installation(self):
        with FakePackage() as package, HubDir() as hub:
            (package.path / "NOTES.md").write_text("wip\n", encoding="utf-8")
            git(package.path, "add", "-A")
            git(package.path, "commit", "-q", "-m", "untagged work")
            run("init", "--hub", str(hub.path), "--package", str(package.path),
                "--project", "example", "--allow-untagged")
            result = run("doctor", "--hub", str(hub.path), "--package", str(package.path))
            self.assertEqual(result.returncode, FAIL, result.stdout)
            self.assertIn("tag", result.stdout)


class MissingGitlinkTests(unittest.TestCase):
    """A workflow present only in someone's working copy is not installed."""

    def test_doctor_reports_a_workflow_absent_from_the_hub_history(self):
        with FakePackage() as package, HubDir() as hub:
            git(hub.path, "-c", "protocol.file.allow=always", "submodule", "add",
                "--name", SUBMODULE_NAME, str(package.path), SUBMODULE_NAME)
            run("init", "--hub", str(hub.path), "--project", "example")
            hub.commit_all("install the workflow")
            # `git add -A` would re-stage the gitlink, so commit the removal alone.
            git(hub.path, "rm", "-q", "--cached", SUBMODULE_NAME)
            git(hub.path, "commit", "-q", "-m", "hub history without the workflow")
            result = run("doctor", "--hub", str(hub.path))
            self.assertEqual(result.returncode, FAIL, result.stdout)
            self.assertIn("gitlink", result.stdout)


class ImmutableArtifactTests(unittest.TestCase):
    """Snapshots and evidence are the record of what was delivered. A migration
    that can rewrite them can rewrite history after the fact."""

    def hub_with_frozen_artifacts(self, package, hub):
        run("init", "--hub", str(hub.path), "--package", str(package.path),
            "--project", "example")
        for relative in ("specs/frozen/snapshot-manifest.json",
                         "evidence/run-001/check-ledger.jsonl"):
            target = hub.path / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("original\n", encoding="utf-8")
        hub.commit_all("freeze")

    def test_upgrade_refuses_a_migration_that_rewrites_frozen_artifacts(self):
        with FakePackage() as package, HubDir() as hub:
            self.hub_with_frozen_artifacts(package, hub)
            package.add_migration("0002-rewriter", REWRITE_MIGRATION)
            result = run("upgrade", "--hub", str(hub.path), "--package", str(package.path))
            self.assertEqual(result.returncode, INVALID, result.stdout)
            self.assertIn("0002-rewriter", result.stderr)

    def test_frozen_artifacts_survive_such_a_migration(self):
        with FakePackage() as package, HubDir() as hub:
            self.hub_with_frozen_artifacts(package, hub)
            package.add_migration("0002-rewriter", REWRITE_MIGRATION)
            run("upgrade", "--hub", str(hub.path), "--package", str(package.path))
            for relative in ("specs/frozen/snapshot-manifest.json",
                             "evidence/run-001/check-ledger.jsonl"):
                self.assertEqual(
                    (hub.path / relative).read_text(encoding="utf-8"), "original\n",
                    relative,
                )


ADD_MIGRATION = """
def migrate(hub_root):
    target = hub_root / "specs" / "frozen" / "created-by-migration.json"
    target.write_text("added\\n", encoding="utf-8")
    return ["added a spec file"]
"""

DELETE_MIGRATION = """
import shutil


def migrate(hub_root):
    shutil.rmtree(hub_root / "evidence")
    return ["deleted the evidence tree"]
"""

# The external copy holds the same bytes as the artifact it replaces, so a
# fingerprint taken by reading through the link cannot tell the two apart.
SYMLINK_FILE_MIGRATION = """
import tempfile
from pathlib import Path


def migrate(hub_root):
    target = hub_root / "specs" / "frozen" / "snapshot-manifest.json"
    external = Path(tempfile.mkdtemp()) / "snapshot-manifest.json"
    external.write_bytes(target.read_bytes())
    target.unlink()
    target.symlink_to(external)
    return ["relinked a frozen artifact"]
"""

SYMLINK_TREE_MIGRATION = """
import shutil
import tempfile
from pathlib import Path


def migrate(hub_root):
    target = hub_root / "evidence"
    external = Path(tempfile.mkdtemp()) / "evidence"
    shutil.copytree(target, external)
    shutil.rmtree(target)
    target.symlink_to(external, target_is_directory=True)
    return ["relinked the evidence tree"]
"""

# A hard link leaves no link to see: the bytes match and `is_symlink()` is
# false, yet the frozen path is one of two names for an inode that can be
# rewritten from outside the Hub. The external name is recorded outside the
# immutable prefixes so the test can write through it afterwards.
HARDLINK_FILE_MIGRATION = """
import os
import tempfile
from pathlib import Path


def migrate(hub_root):
    target = hub_root / "specs" / "frozen" / "snapshot-manifest.json"
    external = Path(tempfile.mkdtemp(dir=hub_root.parent)) / "snapshot-manifest.json"
    external.write_bytes(target.read_bytes())
    target.unlink()
    os.link(external, target)
    (hub_root / "external-alias.txt").write_text(str(external), encoding="utf-8")
    return ["hard-linked a frozen artifact"]
"""

RAISING_MIGRATION = """
def migrate(hub_root):
    (hub_root / "specs" / "frozen" / "snapshot-manifest.json").write_text(
        "rewritten\\n", encoding="utf-8"
    )
    raise RuntimeError("migration blew up after writing")
"""


class ImmutableRollbackTests(unittest.TestCase):
    """Detecting the change is only half of it. The record has to come back.

    Each case asserts the same three things: the upgrade fails cleanly with exit
    2, the message does not claim a restore that did not happen, and the frozen
    bytes on disk are exactly what they were before the migration ran.
    """

    FROZEN = ("specs/frozen/snapshot-manifest.json",
              "evidence/run-001/check-ledger.jsonl")

    def hub_with_frozen_artifacts(self, package, hub):
        run("init", "--hub", str(hub.path), "--package", str(package.path),
            "--project", "example")
        for relative in self.FROZEN:
            target = hub.path / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("original\n", encoding="utf-8")
        hub.commit_all("freeze")

    def assert_record_intact(self, hub):
        """Byte-for-byte, file-for-file and kind-for-kind.

        A leftover addition is a rewrite too, and so is a link standing where a
        regular file was: reading through it would report the right bytes while
        the record's future contents lived outside the Hub.
        """
        for prefix in ("specs", "evidence"):
            base = hub.path / prefix
            self.assertFalse(base.is_symlink(), f"{prefix} is a link, not a tree")
        for relative in self.FROZEN:
            path = hub.path / relative
            self.assertFalse(path.is_symlink(), f"{relative} is a link, not a file")
            self.assertTrue(path.is_file(), f"{relative} is missing")
            self.assertEqual(
                path.stat().st_nlink, 1,
                f"{relative} is still an alias for an inode named elsewhere",
            )
            self.assertEqual(
                path.read_text(encoding="utf-8"), "original\n", relative
            )
        present = sorted(
            path.relative_to(hub.path).as_posix()
            for prefix in ("specs", "evidence")
            for path in (hub.path / prefix).rglob("*")
            if path.is_symlink() or path.is_file()
        )
        self.assertEqual(present, sorted(self.FROZEN))

    def upgrade_with(self, migration_name, body, then=None):
        with FakePackage() as package, HubDir() as hub:
            self.hub_with_frozen_artifacts(package, hub)
            package.add_migration(migration_name, body)
            result = run(
                "upgrade", "--hub", str(hub.path), "--package", str(package.path)
            )
            self.assertEqual(result.returncode, INVALID, result.stdout)
            self.assertIn("restored", result.stderr.lower())
            self.assertNotIn("NOT be fully restored", result.stderr)
            self.assert_record_intact(hub)
            self.assertNotIn(migration_name, hub.lock()["migrations_applied"])
            if then is not None:
                then(hub.path)
            return result

    def test_a_migration_that_adds_a_spec_file_has_that_file_removed(self):
        result = self.upgrade_with("0002-adder", ADD_MIGRATION)
        self.assertIn("created-by-migration.json", result.stderr)

    def test_a_migration_that_deletes_the_evidence_tree_has_it_checked_out(self):
        result = self.upgrade_with("0002-deleter", DELETE_MIGRATION)
        self.assertIn("check-ledger.jsonl", result.stderr)

    def test_a_migration_that_relinks_a_frozen_file_is_caught_and_undone(self):
        result = self.upgrade_with("0002-relinker", SYMLINK_FILE_MIGRATION)
        self.assertIn("snapshot-manifest.json", result.stderr)

    def test_a_migration_that_relinks_an_immutable_tree_is_caught_and_undone(self):
        result = self.upgrade_with("0002-tree-relinker", SYMLINK_TREE_MIGRATION)
        self.assertIn("check-ledger.jsonl", result.stderr)

    def test_a_migration_that_hardlinks_a_frozen_file_is_caught_and_undone(self):
        def the_alias_is_broken(hub_path):
            """Link count 1 says the alias is gone; writing through it proves it."""
            external = Path(
                (hub_path / "external-alias.txt").read_text(encoding="utf-8")
            )
            external.write_text("rewritten from outside\n", encoding="utf-8")
            self.assertEqual(
                (hub_path / "specs/frozen/snapshot-manifest.json").read_text(
                    encoding="utf-8"
                ),
                "original\n",
                "the frozen artifact still changes when the outside name is written",
            )

        result = self.upgrade_with(
            "0002-hardlinker", HARDLINK_FILE_MIGRATION, then=the_alias_is_broken
        )
        self.assertIn("snapshot-manifest.json", result.stderr)

    def test_a_migration_that_raises_after_writing_is_still_rolled_back(self):
        result = self.upgrade_with("0002-raiser", RAISING_MIGRATION)
        self.assertIn("RuntimeError", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


class ReleasePreflightTests(unittest.TestCase):
    """An untagged package is refused before it can change anything."""

    def test_upgrade_runs_no_migration_when_the_package_is_untagged(self):
        with FakePackage() as package, HubDir() as hub:
            run("init", "--hub", str(hub.path), "--package", str(package.path),
                "--project", "example")
            hub.commit_all("install")
            before = hub.lock()

            directory = package.path / "migrations" / "0002-untagged"
            directory.mkdir()
            (directory / "migrate.py").write_text(
                TOUCH_MIGRATION.format(tag="untagged"), encoding="utf-8"
            )
            git(package.path, "add", "-A")
            git(package.path, "commit", "-q", "-m", "untagged migration")

            result = run(
                "upgrade", "--hub", str(hub.path), "--package", str(package.path)
            )
            self.assertEqual(result.returncode, INVALID, result.stdout)
            self.assertFalse(
                (hub.path / "migrated-untagged.txt").exists(),
                "an untagged package mutated the Hub before being refused",
            )
            self.assertEqual(hub.lock(), before)


class DoctorTagIdentityTests(unittest.TestCase):
    """The lock's tag text is a claim about Git, so Git is what settles it."""

    def test_doctor_reports_a_release_tag_that_no_longer_points_at_HEAD(self):
        with FakePackage() as package, HubDir() as hub:
            run("init", "--hub", str(hub.path), "--package", str(package.path),
                "--project", "example")
            self.assertEqual(
                run("doctor", "--hub", str(hub.path),
                    "--package", str(package.path)).returncode,
                PASS,
            )
            git(package.path, "tag", "-d", f"v{package.path.joinpath('VERSION').read_text().strip()}")
            result = run(
                "doctor", "--hub", str(hub.path), "--package", str(package.path)
            )
            self.assertEqual(result.returncode, FAIL, result.stdout)
            self.assertIn("does not point at the checked-out commit", result.stdout)


class VersionOrderingTests(unittest.TestCase):
    """SemVer: a prerelease precedes the release it leads to."""

    def test_prerelease_precedes_its_release(self):
        sys.path.insert(0, str(HUB_CLI.parent))
        import hub as hub_module

        self.assertLess(hub_module.version_key("1.0.0-alpha"), hub_module.version_key("1.0.0"))
        self.assertLess(hub_module.version_key("1.0.0-alpha"), hub_module.version_key("1.0.0-beta"))
        self.assertLess(hub_module.version_key("1.0.0-alpha.1"), hub_module.version_key("1.0.0-alpha.2"))
        self.assertLess(hub_module.version_key("0.9.9"), hub_module.version_key("1.0.0-alpha"))
        self.assertLess(hub_module.version_key("1.0.0"), hub_module.version_key("1.0.1"))
