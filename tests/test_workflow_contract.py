"""Consistency checks for the published workflow contract."""

import re
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class WorkflowHierarchyTests(unittest.TestCase):
    def test_canonical_hierarchy_lists_every_template_domain_folder(self):
        workflow = (PACKAGE_ROOT / "docs" / "workflow.md").read_text(
            encoding="utf-8"
        )
        hierarchy = workflow.split("## 7.", 1)[1].split("## 8.", 1)[0]
        documented = set(
            re.findall(r"^  ([a-z][a-z-]*/)", hierarchy, flags=re.MULTILINE)
        )
        template_root = PACKAGE_ROOT / "template" / "docs" / "domain"
        canonical = {
            f"{path.name}/" for path in template_root.iterdir() if path.is_dir()
        }

        self.assertEqual(documented, canonical)


if __name__ == "__main__":
    unittest.main()
