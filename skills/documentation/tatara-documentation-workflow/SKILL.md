---
name: tatara-documentation-workflow
description: "Prescriptive scheduled documentation procedure: determine when docs were last updated, diff every enrolled component repo's default branch since then, judge whether the central docs repo needs an update, then either edit the docs and call change_summary or just finish the turn (no tool call) on a clean no-op. Use at the start of every documentation-kind task."
profiles: ["documentation"]
---

# Tatara Documentation Workflow

TASK content. Follow these steps in order. Do not skip or reorder.

---

## 0. Understand your context

You are spawned on a schedule (cron), not by a specific merge event. Unlike
an `implement` task, **your working clone is the central documentation repo**
(mkdocs-based). You also have read-only clones of every enrolled component
repo at their current default-branch HEAD (the project-scoped clone set, same
mechanism `brainstorm`/`incident` use) - use these to diff, not a single
triggering repo:

- `task` (env `TATARA_TASK`) and `project` (env `TATARA_PROJECT`) - pass to
  every MCP tool call.
- Workspace root: `/workspace/<owner>/<docs-repo>` - the docs repo, already
  cloned on your task branch. **Never commit or push to the docs repo's
  default branch directly.**
- Every other enrolled repo cloned read-only at `/workspace/<owner>/<repo>`
  (list them with `repo_list`, per `tatara-mcp-platform`), at their current
  default-branch HEAD.

**Confirm this against the operator's actual scheduled-trigger
implementation** - if it instead injects an explicit per-repo "last
ingested SHA" cursor rather than relying on the docs repo's own git history
(Step 1 below), use that cursor instead of the derivation this skill
describes.

---

## 1. Determine "since when" per repo, then diff each one

Find the last time THIS documentation task actually made a change: in the
docs repo clone, `git log --all --grep="docs:" --since="90 days ago"
--format="%H %ad %s" --date=short -- .` (or, more precisely, the most recent
commit whose message matches the `change_summary` `pr_title` convention this
skill itself uses, `"docs: ..."`) gives you a timestamp T. If no prior
doc-update commit is found (first run, or none in the lookback window),
default T to 30 days ago rather than the full repo history - a full-history
diff on first run would be enormous and mostly irrelevant.

For each enrolled component repo (`repo_list`), diff its default branch since
T:

```bash
cd /workspace/<owner>/<component-repo>
git log --since="<T>" --oneline
git diff "$(git rev-list -1 --before="<T>" HEAD)"..HEAD
```

If a repo has no commits since T, skip it - nothing to evaluate. Read the
full diff for repos that do, not just file names - the decision in step 2
depends on what actually changed, not which files changed. When several
repos have commits since T, dispatch one `explorer` subagent per repo (via
the `Agent` tool, `model: haiku`, `effort: low`) to produce a compact
summary of "what changed and whether it looks doc-relevant" for that repo,
launched in a single message so they run concurrently - then make the
step-2 judgment yourself from their reports plus your own reading of the
docs repo.

---

## 2. Read the docs repo and judge doc impact

Read `mkdocs.yml` (nav structure) and the relevant pages under `docs/` in
your working clone. Decide, per repo with commits since T, whether that
repo's changes warrant a docs update - and whether, taken together, they add
up to a meaningful update even if no single repo's diff alone would.

**Warrants an update:** new user-facing feature or CLI flag, changed
behavior/config contract, new API/tool surface, a renamed or removed concept
still referenced in the docs, an architecture change that an existing page
describes incorrectly.

**Does not warrant an update:** internal refactor with no external contract
change, test-only changes, dependency bumps, typo/lint fixes, CI/tooling
changes, a change already fully covered by existing prose.

This is a judgment call - use the diff from step 1 and the existing docs
structure. Do not update docs speculatively "just in case."

---

## 3a. Doc-relevant change: edit and hand off

Edit the docs repo on your task branch (already created for you; never touch
the docs repo's default branch). Keep edits scoped to what the merge actually
changed - do not restructure unrelated pages.

Before ending the turn, call `change_summary`:

```
change_summary(
  task="<TATARA_TASK>",
  pr_title="docs: <concise imperative summary>",
  pr_body="<which repo(s) changed since the last doc update, what changed upstream in each, what was updated in the docs, and why>",
  delivered_scope="<pages/sections edited>",
  remaining_scope="",       # optional
  most_problematic=""       # optional
)
```

Then finish the turn. The operator opens the MR against the docs repo
(`writeBackOpenChange`), stamps the auto-merge label, and the docs repo's
mkdocs-build CI gates the merge. You do not open the MR yourself and this MR
is exempt from the platform's review/mrScan agents - do not wait for a human
or bot review.

---

## 3b. Not doc-relevant: finish with no change

If step 2 concludes no docs update is warranted, just end the turn with no docs
edit and no tool call. That empty finish IS the correct terminal for a no-op
documentation task: the operator records a no-change writeback and marks the
task Succeeded.

Do NOT call `decline_implementation` (or `already_done`) here. Those post an
implement-outcome, which the operator accepts only for `implement` tasks;
a `documentation` task gets a deterministic `409 "implement outcome only applies
to an implement task"`. There is nothing to retry - it is a backend
constraint on task kind, not a validation error. The `refused-no-explanation`
requeue applies only to `implement` tasks, never to this kind, so
a silent no-op finish is safe and expected.

---

## Decision table

| Situation | Correct call |
|---|---|
| Diff has an external-facing change the docs don't cover | edit docs, then `change_summary(...)` |
| Diff is internal-only / already covered / non-functional / no docs change warranted | finish the turn: no edit, no tool call (operator marks it Succeeded, no-change) |
| `decline_implementation` / `already_done` on a documentation task | never - 409 implement-only; just finish instead |

## Anti-patterns

- Do not edit any component repo - they are read-only clones, for diffing only.
- Do not push to the docs repo's default branch.
- Do not update docs "just in case" when the change is purely internal.
- Do not wait for a human/bot review on the docs MR - it auto-merges on green
  mkdocs CI.
