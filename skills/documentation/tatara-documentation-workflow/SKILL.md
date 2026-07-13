---
name: tatara-documentation-workflow
description: "Prescriptive nightly documentation procedure: read the delivered Tasks your batch covers, diff what they actually shipped, judge whether the central docs repo needs an update, then either edit the docs, open the MR with mr_write and call submit_outcome(action=submitted), or call submit_outcome(action=declined) on a clean no-op. Use at the start of every documentation turn."
profiles: ["documentation"]
---

# Tatara Documentation Workflow

TASK content. Follow these steps in order. Do not skip or reorder.

---

## 0. Understand your context

You are a NIGHTLY BATCH, not a per-merge spawn. One documentation Task is minted
per project per night, and it covers EVERY Task delivered in the last 24 hours
that actually shipped code. Those Tasks are named in your Task's
`spec.documentsTasks` - read it with `task_get()`.

**That list is your input.** Do not go looking for "when were the docs last
updated": the operator already decided what this batch covers, and every Task in
`documentsTasks` gets its `documentedBy` stamped when you finish, whatever you
decide.

Unlike an `implement` Task, **your working clone is the central documentation
repo** (mkdocs-based). You also have read-only clones of every enrolled component
repo at their current default-branch HEAD:

- Workspace root: `/workspace/<owner>/<docs-repo>` - the docs repo, already
  cloned on your task branch. **Never commit or push to the docs repo's default
  branch directly.**
- Every other enrolled repo cloned read-only at `/workspace/<owner>/<repo>`
  (`repo_list` names them, per `tatara-mcp-platform`).

You have a 2h stage budget (`docStageBudget`). If you overrun it, the operator
force-moves you to `delivered` and stamps `documentedBy` anyway - no parent Task
is ever pinned by a stuck doc batch. Do not sprawl.

---

## 1. Read what actually shipped

For each Task name in `spec.documentsTasks`:

```
task_context(task="<task-name>")
```

That bundle gives you the Task's Issues (what was asked for, and the human
conversation around it), its merged MRs (title, body, head SHA), and its notes -
including the implement pod's own account of what it did and what was tricky. This
is a far better source than a raw diff, and it is free.

Then confirm against the code. For each repo that a covered Task merged an MR
into:

```bash
cd /workspace/<owner>/<component-repo>
git log --oneline -20
git show <merge-sha>            # the MR head SHA from the bundle
```

When several repos are in play, dispatch one `explorer` subagent per repo (via
the `Agent` tool, `model: haiku`, `effort: low`) to produce a compact summary of
"what changed and whether it looks doc-relevant" for that repo, launched in a
single message so they run concurrently - then make the step-2 judgment yourself
from their reports plus your own reading of the docs repo.

---

## 2. Read the docs repo and judge doc impact

Read `mkdocs.yml` (nav structure) and the relevant pages under `docs/` in
your working clone. Decide, per covered Task, whether what it shipped warrants a
docs update - and whether, taken together, they add up to a meaningful update even
if no single one would.

**Warrants an update:** new user-facing feature or CLI flag, changed
behavior/config contract, new API/tool surface, a renamed or removed concept
still referenced in the docs, an architecture change that an existing page
describes incorrectly.

**Does not warrant an update:** internal refactor with no external contract
change, test-only changes, dependency bumps, typo/lint fixes, CI/tooling
changes, a change already fully covered by existing prose.

This is a judgment call. Do not update docs speculatively "just in case."

---

## 3a. Doc-relevant change: edit, open the MR, submit

Edit the docs repo on your task branch (already created for you; never touch the
docs repo's default branch). Keep edits scoped to what actually shipped - do not
restructure unrelated pages. Commit and push.

Then open the MR yourself:

```
mr_write(action="open", repo="<docs-repo>", title="docs: <concise imperative summary>", body="...")
```

`open` is IDEMPOTENT - a second call for the same repo returns the existing MR
with `"existing": true`. See `tatara-mcp-scm`.

Then end the turn:

```
submit_outcome(
  action="submitted",
  title="docs: <concise imperative summary>",
  body="<which Tasks this batch covered, what shipped in each, what was updated in the docs, and why>",
  change_significance="patch"     # docs are almost always patch
)
```

`merge_order` is only required when this Task's MRs span more than one repo. A doc
batch touches one repo - the docs repo - so you may omit it.

**Your MR IS reviewed.** `submit_outcome(action="submitted")` moves the Task to
`reviewing` and a review pod reads your MR exactly like any other. Write the body
for that reviewer. A `request_changes` verdict routes the Task back and you get
another turn.

---

## 3b. Nothing to document: decline, do not go silent

If step 2 concludes no docs update is warranted:

```
submit_outcome(action="declined", decline_reason="<what the batch covered and why none of it is doc-relevant>")
```

**A silent finish is NOT the no-op terminal.** A Task that receives no outcome
ages out at `stageReason=no-outcome`, its pod is deleted, and the batch is lost.
`action="declined"` IS the clean no-op: it moves the Task to `delivered` and
stamps `documentedBy` on every Task in `spec.documentsTasks`, exactly as a
submitted MR would.

Name what you looked at in `decline_reason`. "Nothing to do" is not a reason.

---

## Decision table

| Situation | Correct call |
|---|---|
| A covered Task shipped an external-facing change the docs do not cover | edit docs, push, `mr_write(action="open")`, then `submit_outcome(action="submitted", ...)` |
| Everything the batch covered is internal-only / already documented / non-functional | `submit_outcome(action="declined", decline_reason=...)` |
| Finishing the turn with no `submit_outcome` at all | **FORBIDDEN** - the Task ages out at `no-outcome` and the batch is lost |

## Before you stop

Write `task_note(kind="handoff", body=...)` - see `handoff`. If the review bounces
your MR back, the next docs pod on this Task reads it.

## Anti-patterns

- Deriving "what to document" from git history when `spec.documentsTasks` already
  says exactly which Tasks this batch covers.
- Editing any component repo - they are read-only clones, for reading only.
- Pushing to the docs repo's default branch.
- Updating docs "just in case" when the change is purely internal.
- Assuming the docs MR auto-merges without review. It goes to `reviewing` like
  every other MR on this platform.
- Merging anything. You have no merge action; the operator merges.
