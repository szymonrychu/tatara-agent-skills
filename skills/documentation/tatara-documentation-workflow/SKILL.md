---
name: tatara-documentation-workflow
description: "Prescriptive post-merge documentation procedure: clone the merged source repo, diff base..head, judge whether the central docs repo needs an update, then either edit the docs and call change_summary or just finish the turn (no tool call) on a clean no-op. Use at the start of every documentation-kind task."
profiles: ["documentation"]
---

# Tatara Documentation Workflow

TASK content. Follow these steps in order. Do not skip or reorder.

---

## 0. Understand your context

You are spawned after a merge lands on some component repo's default branch.
Unlike an `implement` task, **your working clone is the central documentation
repo** (mkdocs-based), not the repo that changed. The repo and SHA range that
triggered you ride as environment variables, not as your workspace:

- `task` (env `TATARA_TASK`) and `project` (env `TATARA_PROJECT`) - pass to
  every MCP tool call.
- `TATARA_SOURCE_REPO` - the full git clone URL of the merged component repo,
  provider-agnostic (GitHub or GitLab), e.g. `https://github.com/szymonrychu/tatara-cli`.
- `TATARA_SOURCE_BASE_SHA` - the commit before the merge.
- `TATARA_SOURCE_HEAD_SHA` - the commit after the merge.
- Workspace root: `/workspace/<owner>/<docs-repo>` - the docs repo, already
  cloned on your task branch. **Never commit or push to the docs repo's
  default branch directly.**

The source repo is NOT pre-cloned. You clone it yourself in step 1.

---

## 1. Shallow-clone the source repo and diff the merge

Source repos are public; no auth is needed.

```bash
git clone --depth 50 "$TATARA_SOURCE_REPO" /tmp/source-repo
cd /tmp/source-repo
git fetch --depth 50 origin "$TATARA_SOURCE_BASE_SHA" "$TATARA_SOURCE_HEAD_SHA" 2>/dev/null || true
git diff "$TATARA_SOURCE_BASE_SHA".."$TATARA_SOURCE_HEAD_SHA"
```

If the shallow depth does not reach `TATARA_SOURCE_BASE_SHA` (old or squash-merged
history), re-fetch with a larger depth or `git fetch --unshallow` before
diffing. Read the full diff, not just file names - the decision in step 2
depends on what actually changed, not which files changed.

---

## 2. Read the docs repo and judge doc impact

Read `mkdocs.yml` (nav structure) and the relevant pages under `docs/` in your
working clone. Decide whether the merged change warrants a docs update.

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
  pr_body="<what changed upstream, what was updated in the docs, and why>",
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
implement-outcome, which the operator accepts only for `issueLifecycle` tasks;
a `documentation` task gets a deterministic `409 "implement outcome only applies
to an issueLifecycle task"`. There is nothing to retry - it is a backend
constraint on task kind, not a validation error. The `refused-no-explanation`
requeue applies only to `issueLifecycle` implement tasks, never to this kind, so
a silent no-op finish is safe and expected.

---

## Decision table

| Situation | Correct call |
|---|---|
| Diff has an external-facing change the docs don't cover | edit docs, then `change_summary(...)` |
| Diff is internal-only / already covered / non-functional / no docs change warranted | finish the turn: no edit, no tool call (operator marks it Succeeded, no-change) |
| `decline_implementation` / `already_done` on a documentation task | never - 409 issueLifecycle-only; just finish instead |

## Anti-patterns

- Do not clone or edit the source repo - it is read-only, for diffing only.
- Do not push to the docs repo's default branch.
- Do not update docs "just in case" when the change is purely internal.
- Do not wait for a human/bot review on the docs MR - it auto-merges on green
  mkdocs CI.
