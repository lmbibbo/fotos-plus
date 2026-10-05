# Proposal

## Why

`openspec/config.yaml` no longer describes this repository. Its project context was
trimmed to a two-line tech stack, its only language rule is about normative keywords in
Spanish, and its archive guidance describes a commit-and-push flow that the automation
contradicts. The result is guidance that an agent following it verbatim will get wrong:
it loses the domain context needed to write artifacts, and it never learns that the
`archive` label is the only thing that merges a pull request.

Two facts make this worth fixing now rather than later. The draft replacement circulated
for discussion does not parse as YAML, and one of its new rule keys targets an artifact id
that does not exist, so it would fail silently. Both are invisible until something breaks.

## What Changes

- Restore the project description in `context`: what the application does (explores a
  directory of photos and organizes them by date, place, and people, plus an ordered
  viewer). It is currently reduced to `App: Python` and it is the context artifacts are
  written from.
- Correct the architecture note. The draft claims "the backend and the frontend are
  separate applications". Observed reality is one Python package: `fotos_plus/server.py`
  serves over `ThreadingHTTPServer` and `fotos_plus/viewer.py` emits a single
  self-contained HTML document with inline CSS and JS and base64 `data:` URIs for
  thumbnails. There is no frontend build, no JS files, and no framework.
- Drop `rules.language`. Rules are keyed by artifact id and `spec-driven` declares only
  `proposal`, `specs`, `design`, and `tasks`, so that key would be injected into nothing.
  The language policy is stated once in `context`, where it actually applies, with a short
  per-artifact reminder in the rules that matter.
- Restate the `specs` rule in English: `MUST` on the first verb of each requirement and
  `MUST NOT` for prohibitions, replacing the Spanish `DEBE (MUST)` rule. This keeps new
  requirements consistent with the 12 already written in English.
- Document that direct commits and pushes to `main` are not allowed.
- Document the `strict: true` consequence: after `main` moves, a long-lived branch must
  merge `main` in and push the merge commit, because force pushes are disabled by branch
  protection.
- Replace "A single commit containing the code, tests, synced specs, and archive" with the
  flow that actually works. The single-commit rule has been violated by every recent
  change (`226f073`, `874e49e`, `fe387e6`, `1052a83`).
- Document that the `archive` label is the sole trigger for the squash merge and branch
  deletion, so a pull request opened under this guidance is otherwise unmerged.
- Remove the commented-out template examples at the end of the file.

Non-goals, recorded deliberately:

- Translating the 38 requirements and 10 archived changes that remain in Spanish. That is
  a separate change.
- Changing `.github/workflows/archive-merge.yml`, which already runs `verify` on every
  pull request as of `5512d17`.
- Any change to the application's behavior. No source file is touched.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This change edits project tooling only. `openspec/config.yaml` governs how the
agent writes artifacts; it does not define any runtime behavior of the photo organizer,
so no requirement in `group-labels`, `photo-marking`, `photo-scanning`, `photo-viewing`,
or `trip-periods` changes. This change therefore sets `skip_specs: true`, which is the
marker the schema reserves for pure tooling and documentation work. Inventing a
"development workflow" capability to satisfy validation would put a requirement in the
main specs that describes nothing about the system those specs are about.

## Impact

- `openspec/config.yaml`: the only file modified.
- Artifacts written after this change will be generated in English and will draw on a
  correct domain description. Existing artifacts are unaffected and stay as they are.
- No effect on `fotos_plus/`, the test suite, dependencies, or runtime behavior.
- Depends on pull request #10 (`chore: generate OpenSpec artifacts in English`), which
  already introduces the language block in `context`. This change builds on top of it and
  must not be merged first, or the two will conflict on the same lines.

## Rollback plan

`git revert <merge-commit>` on the squash commit that lands this change. It is a
single-file change with no code, no dependency, and no generated state, so reverting
restores the previous `openspec/config.yaml` exactly and nothing downstream needs repair.
The reverted file is still valid YAML, so artifacts written during the reverted window
remain readable; only the guidance they were written under changes back.

If the rollback is needed after other artifacts have been generated under the new
context, those artifacts stay valid. OpenSpec does not validate prose against `context`.
