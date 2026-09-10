"""Published entrypoint and upgrade behavior for pinned Skill selection."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migrations/001-pinned-skill-entry/migrate.py"

class SkillBootstrapTests(unittest.TestCase):
    def migrate(self, hub):
        spec = importlib.util.spec_from_file_location("skill_entry_migration", MIGRATION)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.migrate(hub)

    def test_upgrade_preserves_local_guides_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp)
            for name in ("AGENTS.md", "CLAUDE.md"):
                (hub / name).write_text("Existing local scope stays authoritative.\n")
            (hub / "specs").mkdir()
            (hub / "specs/frozen.txt").write_text("immutable")
            self.migrate(hub)
            first = {p.relative_to(hub): p.read_bytes() for p in hub.rglob("*") if p.is_file()}
            self.migrate(hub)
            second = {p.relative_to(hub): p.read_bytes() for p in hub.rglob("*") if p.is_file()}
            self.assertEqual(first, second)
            for name in ("AGENTS.md", "CLAUDE.md"):
                content = (hub / name).read_text()
                self.assertTrue(content.startswith("Existing local scope stays authoritative."))
                self.assertIn("docs/skill-entry.md", content)
            self.assertEqual((hub / "docs/skill-entry.md").read_bytes(),
                             (ROOT / "template/docs/skill-entry.md").read_bytes())
            self.assertEqual((hub / "specs/frozen.txt").read_text(), "immutable")

    def test_upgrade_refuses_existing_different_entry_without_editing_guides(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp)
            (hub / "docs").mkdir()
            (hub / "docs/skill-entry.md").write_text("User-owned instructions")
            (hub / "AGENTS.md").write_text("User-owned guide")
            with self.assertRaisesRegex(ValueError, "existing"):
                self.migrate(hub)
            self.assertEqual((hub / "AGENTS.md").read_text(), "User-owned guide")
            self.assertFalse((hub / "CLAUDE.md").exists())

    def test_new_hub_and_upgrade_expose_same_entry(self):
        for name in ("AGENTS.md", "CLAUDE.md"):
            self.assertIn("docs/skill-entry.md", (ROOT / "template" / name).read_text())
        entry = (ROOT / "template/docs/skill-entry.md").read_text()
        self.assertIn("--skill-source", entry)
        self.assertIn(".domain-delivery/skills/", entry)

    def test_manifests_follow_package_version(self):
        version = (ROOT / "VERSION").read_text().strip()
        for name in (".claude-plugin", ".codex-plugin"):
            self.assertEqual(json.loads((ROOT / name / "plugin.json").read_text())["version"], version)

    def test_workflow_points_to_package_version_not_an_independent_current_version(self):
        workflow = (ROOT / "docs/workflow.md").read_text()
        preamble = workflow.split("## 1.", 1)[0]
        self.assertIn("[VERSION](../VERSION)", preamble)
        self.assertNotIn("Accepted，version", preamble)

if __name__ == "__main__":
    unittest.main()
