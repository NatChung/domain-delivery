# Issue tracker: GitHub

Todos, improvements and specs for this repository live in
`NatChung/domain-delivery` GitHub Issues. Local Markdown can hold supporting
material; the issue owns scope, acceptance criteria and work status.

These conventions are **prose-only, unenforced**: agents apply them when using
the tracker; the kernel does not control GitHub operations.

## Conventions

Always specify `--repo NatChung/domain-delivery` when using `gh`:

- Create: `gh issue create --repo NatChung/domain-delivery --title "..." --body-file <file> --label needs-triage`.
- Read: `gh issue view <number> --repo NatChung/domain-delivery --json number,title,body,labels,comments`.
- List: `gh issue list --repo NatChung/domain-delivery --state all --json number,title,labels`.
- Comment: `gh issue comment <number> --repo NatChung/domain-delivery --body-file <file>`.
- Label: `gh issue edit <number> --repo NatChung/domain-delivery --add-label "..."` or `--remove-label "..."`.
- Close: `gh issue close <number> --repo NatChung/domain-delivery`, after checking the latest acceptance criteria and evidence.

Before creating an issue, search open and closed issues for the same work.
Keep one canonical issue per request and link implementation PRs to it. Include
the problem, evidence, proposed scope, acceptance criteria, validation and
unresolved decisions. Distinguish intended outcomes from verified results.

Use body files for multiline content. Follow the current session's approval
requirements before external writes; read back the result and retain its URL.
Use repository-scoped authentication without changing global account state.

## Public content

Publish only repository-neutral workflow details or synthetic examples. Keep
consumer identifiers, private paths, private URLs, credentials and source
material out of issues, comments and PRs, as required by
[the repository rules](../../AGENTS.md#product-neutrality).

## Triage workflow

Use [the canonical labels](triage-labels.md). Labels classify work; they do not
grant approval. Keep implementation, review, merge, deployment, retest and
acceptance evidence distinct.

## Pull requests as a triage surface

**PRs as a request surface: no.** Requests belong in issues; PRs carry the
implementation and validation evidence.
