# Design

## Context

See `proposal.md` for motivation. The constraints that shape the approach:

- `config.yaml` is *project-provided data*, not code. It is read by the agent when
  writing artifacts and is never validated against the artifacts it produces. A change
  to it is therefore always silent: nothing fails if it is wrong.
- `rules` is keyed by artifact id. `openspec schemas --json` reports exactly
  `proposal`, `specs`, `design`, `tasks` for the `spec-driven` schema. A key that matches
  none of them is injected nowhere, and `openspec doctor` does not report it.
- The repository currently ships one pull request automation,
  `.github/workflows/archive-merge.yml`, whose `merge` job is gated on
  `if: github.event.label.name == 'archive'`. Its `verify` job now runs on every pull
  request (`5512d17`), but merging still happens only when a human applies that label.
- Branch protection on `main` requires the `verify` check with `strict: true`, and sets
  `allow_force_pushes: false`.

The pull request lifecycle the guidance has to describe:

```
  agent / dev
      |
      v
  [feature branch] --push--> [PR contra main]
      |                            |
      |                            v
      |                   verify corre solo (opened/synchronize)
      |                            |
      |                   +--------+--------+
      |                   |                 |
      |              verify pass      verify fail
      |                   |                 |
      |                   v                 v
      |              CLEAN, esperando   corregir y pushar
      |                   |            (synchronize -> verify)
      |                   |
      |     +-------------+-------------+
      |     |             |             |
      |  etiqueta      etiqueta      sin etiqueta
      |  `archive`     otra           |
      |     |             |             |
      |     v             v             v
      |  squash       queda CLEAN    queda CLEAN
      |  merge +      esperando       sin merge:
      |  borra rama   merge manual    NADIE mergea
      |
      +-- main se movio --> la rama queda BEHIND:
                             gh: "Required status check verify is expected"
                             fix: git merge origin/main && git push
```

## Goals / Non-Goals

**Goals:**

- Every key in `rules` maps to a real artifact id, so no rule is dead weight.
- The file is internally consistent: a reader who follows it lands on English output,
  a feature branch, and a merged pull request.
- The domain description survives, corrected against the actual code.
- Guidance that the repository cannot or does not enforce is either removed or labelled
  as a convention rather than presented as a step.

**Non-Goals:**

- Adding enforcement. Nothing checks commit shape, and this change does not add a check
  for it.
- Renaming the `archive` label or changing which job it triggers.
- Changing any spec, source file, or test.

## Decisions

### D1. The language policy lives in `context`, once

**Chosen:** a single `Language:` block inside `context`, plus a one-line
"Write in English" reminder inside the rules of the artifacts it applies to.

**Alternatives rejected:**

- *A `rules.language` key.* Matches no artifact id, so it is injected into nothing. This
  is the specific failure in the draft under discussion: a rule that reads as policy and
  behaves as a no-op. Rejected on evidence from `openspec schemas --json`.
- *Stating it only in `context`, with no per-artifact reminder.* Single source of truth,
  but `context` is read once at the start of writing and is easy to lose by the time an
  agent fills in the seventeenth scenario. The reminder is cheap and its cost is one
  duplicated sentence.
- *Stating it in all four `rules` blocks with full text.* Four copies to keep in sync,
  which is how the draft ended up stating it twice and contradicting itself.

### D2. The normative-keyword rule is restated in English, not deleted

**Chosen:** keep the rule, worded in English — `MUST` on the first verb of a
requirement, `MUST NOT` for prohibitions.

**Alternatives rejected:**

- *Delete the rule.* Then nothing tells a future artifact which keyword to use, and the
  repository drifts further: 12 requirements already use `MUST`, and new ones would pick
  whatever the author happened to type.
- *Keep it in Spanish.* Contradicts the English rule in the same file.

**Accepted trade-off:** `photo-viewing` keeps 5 English `MUST` requirements next to 11
Spanish `DEBE` ones until the translation change lands. The validator accepts both
because it only requires that `MUST` or `SHALL` appear, so nothing breaks in the
meantime. The alternative — leaving new requirements in Spanish — makes the drift grow.

### D3. The "single commit" instruction is removed, not repaired

**Chosen:** drop `A single commit containing the code, tests, synced specs, and archive`
and keep only the steps that are real: archive on the feature branch, validate before
committing, push, open the PR, do not open a second one.

**Rationale:** the rule has been false for every recent change (`226f073`, `874e49e`,
`fe387e6`, `1052a83` were four separate commits, and pull request #10 ended with a merge
commit). Nothing enforces it. Rewriting it into something equally unenforceable, such as
"prefer one commit", would add a rule that agents will read as permission and maintainers
will ignore. Removing it makes the file honest; if commit discipline is wanted later, it
belongs in a check, not in prose.

### D4. The label is documented as the merge trigger

**Chosen:** state in the archive guidance that the pull request merges only when the
`archive` label is applied, because that label is the sole condition on the `merge` job.

**Alternatives rejected:**

- *Leave it undocumented.* This is the current state and it is the direct cause of a
  pull request sitting finished and unmerged.
- *Change the workflow to merge automatically on green verify.* That would remove the
  deliberate human step from a repository whose automation is otherwise conservative, and
  it is a workflow change, out of scope here. Raised as an open question instead.

### D5. The domain description is translated, not just retained

**Chosen:** keep the substance of the current `Proyecto:` block and write it in English,
with the architecture corrected.

The `Language:` rule applies to what the agent produces. `context` is what the agent
produces guidance from, and a Spanish block next to an English instruction set is the
same split this change exists to remove. The content is preserved: photo organizer,
explores a directory, organizes by date/place/people, includes an ordered viewer.

The architecture sentence is corrected rather than carried over, because the draft's
"backend and frontend are separate applications" is false for this repository, and a
future artifact that takes it at face value would describe a split that does not exist.

### D6. `skip_specs: true`, and no capability delta

**Chosen:** the change declares no capabilities and sets `skip_specs: true`.

`config.yaml` governs how artifacts are written. No requirement in `group-labels`,
`photo-marking`, `photo-scanning`, `photo-viewing`, or `trip-periods` describes it, and
none changes. A capability such as `development-workflow` would put a requirement in the
main specs that says nothing about the photo organizer those specs exist to describe, and
the schema instruction explicitly forbids inventing a requirement to satisfy validation.

## Risks / Trade-offs

- **The language drift is institutionalized, not fixed** → Recorded as a non-goal with
  its own change. 38 requirements and 10 archived changes stay in Spanish, so the
  repository is knowingly bilingual for now.
- **The translation change grows harder the longer it waits** → Each new English artifact
  widens the gap. The non-goal is a deferral, not a cancellation.
- **`photo-viewing` reads as two documents stitched together** → Accepted per D2; the
  translation change is what repairs it. Cosmetic until then.
- **A rule key can silently become dead again** → Only four artifact ids exist. A future
  edit could add `rules.tasks` style keys for artifacts that do not exist. `openspec
  doctor` does not catch this; nothing does.
- **Two pull requests touch `config.yaml`** → Hard ordering dependency on #10, stated in
  the proposal. Merging this one first produces a conflict on the same lines and risks
  silently dropping the language block.
- **Documenting the `archive` label does not enforce it** → A reader still can open a
  pull request, wait for green, and stop. The guidance removes the reason for confusion,
  not the possibility of omission.

## Migration Plan

1. Merge #10 first. It lands the English artifact rule and the `Language:` block in
   `context`. Do not skip this: the two changes conflict on the same lines.
2. Rebase this change's branch onto the updated `main` by merging `main` in and pushing
   the merge commit, since `allow_force_pushes` is `false`.
3. Apply the change to `openspec/config.yaml` as described in `tasks.md`.
4. Verify `openspec validate --specs --strict` and `openspec validate --all --strict`
   still pass, confirming the file parses and no spec was disturbed.
5. Confirm the corrected context is actually consumed: generate one throwaway artifact
   and check that it comes out in English and reflects the single-application
   architecture note.

**Rollback:** `git revert` of the squash merge commit. Single file, no code, no
dependencies, no generated state. Artifacts written under the reverted context stay
valid, because `context` is never validated against artifacts.

## Open Questions

- Should the `archive` label be renamed to reflect that it now means "merge", given
  `verify` runs on every pull request? It is a repository label plus a workflow
  condition, and renaming it touches both. Deferrable; does not change this approach.
- Do the 10 archived changes ever get translated, or is the archive treated as frozen
  history that stays in its original language? Affects the scope of the future
  translation change, not this one.
