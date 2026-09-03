"""Locate the shared package root and the consuming Hub root.

These scripts ship inside the shared workflow package and are executed from a
Delivery Hub. The package sits at the Hub-relative path `.domain-delivery/`
(ADR 0008), so the layout is::

    <hub>/.domain-delivery/skills/feature-delivery/scripts/<this file>

The Hub root is found by walking up for the file every Hub carries,
`workflow.lock`, rather than by counting directories, so a Hub that vendors the
package at a different depth still resolves correctly.
"""

from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[3]
KERNEL_ROOT = PACKAGE_ROOT / "kernel"
LOCK_NAME = "workflow.lock"


def hub_root(start: Path | None = None) -> Path:
    """Return the Hub root, or the package's parent when no lock is found."""
    base = (start or PACKAGE_ROOT).resolve()
    for candidate in [base, *base.parents]:
        if (candidate / LOCK_NAME).is_file():
            return candidate
    return PACKAGE_ROOT.parent
