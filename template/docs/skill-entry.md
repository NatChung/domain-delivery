# Pinned Skill entry

Use this entry only when the task selects Domain Delivery under this Hub's existing workflow scope. Other team workflows keep their own entrypoints and authority.

1. Read this Hub's `workflow.lock` and select the required lifecycle (`delivery-hub`, `domain-graph` or `feature-delivery`). Read its procedure from `.domain-delivery/skills/<lifecycle>/SKILL.md` in this Hub. A host-cached Skill is a discovery entry, not a replacement for that pinned procedure.
2. From the Hub root, verify the actual Skill file you intend to use:

   ```bash
   python3 -B .domain-delivery/skills/delivery-hub/scripts/hub.py doctor \
     --skill-source .domain-delivery/skills/<lifecycle>/SKILL.md
   ```

   To inspect a known host-cache source, supply its absolute `SKILL.md` path instead. A mismatch means use the Hub's pinned file and repeat the check against that file; preserve the finding in the task report. If the pinned installation itself fails doctor, resolve that finding before lane work. Installation or upgrade tasks may use the reported findings to repair the installation under their existing authorization.
3. Follow the pinned Skill's current reference and completion criteria. Changing steps does not change the package source. If the host's loaded source is unknown, state that limit and explicitly read the pinned file before proceeding.

The CLI mechanically checks the supplied source against the installed release's tracked file paths and bytes, including references and kernel files. It neither discovers the host's loaded source nor proves that an agent followed a file. Host-added files outside the release manifest are not compared. Source declaration, choosing this workflow and following the pinned procedure are `prose-only, unenforced` because they are agent/host decisions. This check does not add domain authority or release authorization.
