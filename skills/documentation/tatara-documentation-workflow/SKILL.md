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
`documentsTasks` - read it with `task_get()`.

**That list is your input for Phase 1.** The operator already decided what this
batch covers, and every Task in `documentsTasks` gets its `documentedBy`
stamped when you finish, whatever you decide. Phase 2 below is the other half:
it looks at when pages were last updated, on purpose, because a page no code
Task touches is otherwise invisible to the only process that maintains this
site.

Unlike an `implement` Task, **your working clone is the central documentation
repo** (mkdocs-based). You also have read-only clones of every enrolled component
repo at their current default-branch HEAD:

- Workspace root: `/workspace/<owner>/<docs-repo>` - the docs repo, already
  cloned on your task branch. **Never commit or push to the docs repo's default
  branch directly.**
- Every other enrolled repo cloned read-only at `/workspace/<owner>/<repo>`
  (`repo_list` names them, per `tatara-mcp-platform`).

You have a 2h stage budget (`docStageBudget`). If you overrun it, the operator
force-moves you to `done` with `stateReason=doc-timeout` and stamps
`documentedBy` anyway - no parent Task is ever pinned by a stuck doc batch.
Do not sprawl.

---

## 1. Read what actually shipped

For each Task name in `documentsTasks`:

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
docs repo's default branch). Keep edits scoped to what actually shipped.
Restructuring is in scope only for a page this turn is already editing - never
for a page you merely walked past. Commit and push.

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
`awaiting-review` and a review pod reads your MR exactly like any other. Write
the body for that reviewer. A `request_changes` verdict routes the Task back and
you get another turn.

---

## 3a-2. Phase 2: the three stalest pages on the whole surface

Phase 1 above covers what shipped. Phase 2 covers what nothing shipped against.
Run it on EVERY turn, including a turn where Phase 1 found nothing.

Phase 2's scope is the WHOLE documentation surface, not the newcomer path. A
page rots because no code Task touches it, and that is just as true of a
component overview as of a getting-started index. Three exclusions, each with
its own reason:

- `docs/reference/**` - generated-adjacent CRD field tables. They track the
  operator's types and are corrected by Phase 1 when those types move, not by a
  staleness clock.
- `docs/operations/runbooks.md` - a cross-repo API. Its `tatara-runbook-*`
  anchors are linked from `tatara-observability` alert rules and the anchor set
  is append-only, enforced by `check_runbook_anchors.py`. Editing it on a
  staleness trigger risks breaking an inbound link no local check can see.
- `docs/appendix/**` - a dated archive, never edited. Corrections go in a NEW
  dated document, never as edits to history.

1. **Prove the checkout has git history before you trust any date.** Every
   later step ranks pages by their last commit date, and your docs clone may be
   a SHALLOW clone - one commit, no history. A shallow clone does not make
   `git log -1 --format=%ad -- <path>` fail; it makes it return the SAME date,
   the date of the one commit present, for every file in the repo. The sort in
   step 2 then still prints a plausible-looking list, the order in it is
   meaningless, and you would audit three arbitrary pages while reporting them
   as the stalest on the site. A silent wrong answer is worse than a crash,
   which is why this runs before anything else:

   ```bash
   cd /workspace/<owner>/<docs-repo>
   git rev-parse --is-shallow-repository    # "true" means there is no history
   git fetch --unshallow                    # only if it answered "true"
   git rev-parse --is-shallow-repository    # must now answer "false"
   ```

   If the second check still answers `true`, or `git fetch --unshallow` fails,
   **skip Phase 2 for this turn.** Do not sort anyway, do not pick pages by eye,
   do not guess which ones look old - an arbitrary three audited under the label
   "the stalest three" is exactly the failure this guard exists to prevent. Say
   so in your `submit_outcome` body (or in `decline_reason`, if Phase 1 was also
   a no-op), in these words:

   > Phase 2 skipped: the docs checkout has no git history (shallow clone,
   > `git fetch --unshallow` did not restore it), so page staleness cannot be
   > measured. No pages were audited on a staleness trigger this turn.

   Then finish the turn on Phase 1 alone.

   **Apply the same rule to the symptom, not just the flag.** After the sort in
   step 2, read the dates it printed. If every candidate page carries an
   IDENTICAL last-modified date, the history is not there whatever
   `--is-shallow-repository` claimed - one date for the whole tree is precisely
   what a historyless checkout looks like from the outside. Treat it as the same
   failure: skip Phase 2 and report it in the same words.

2. Sort every remaining page by last-touched date, ascending:

   ```bash
   cd /workspace/<owner>/<docs-repo>
   find docs -name '*.md' \
     -not -path 'docs/reference/*' \
     -not -path 'docs/appendix/*' \
     -not -path 'docs/operations/runbooks.md' \
     | while read -r f; do
         printf '%s %s\n' "$(git log -1 --format=%ad --date=short -- "$f")" "$f"
       done | sort
   ```

3. Take the **3 stalest**. Not four, not "however many look bad".

4. **Look up each page's register in `tatara-writing-voice` before you touch
   it.** The register is a property of the PATH, so look it up in that skill's
   table by path rather than judging it from how the page reads today. This list
   will hand you clinical pages far more often than warm ones, because clinical
   pages are exactly the ones nobody rewrites for tone. A page under
   `docs/components/**`, `docs/architecture/**`, `docs/workflows/**`, or
   `docs/operations/**` is CLINICAL: fix what is factually wrong and change
   nothing else. Do not add second person, do not add contractions, do not
   reorder it to lead with what the reader gets. Warming up a reference page is
   a regression even when every sentence you wrote is true.

5. For each of the 3, verify its claims against the component repos you already
   have cloned read-only at `/workspace/<owner>/<repo>`. You are looking for two
   different defects and they have different remedies:
   - **Factually wrong**: the page describes behavior the code no longer has.
     Fix it, citing the file you read. This applies in BOTH registers.
   - **Off-register**: the page is correct but reads as a capability brochure
     rather than something a newcomer can use. Apply `tatara-writing-voice`.
     This applies to WARM pages only.

   A claim you cannot verify against a repo you have is FLAGGED in the MR body,
   not guessed. A fluent wrong sentence is worse than the clumsy true one.

6. Fan out one `writer` subagent per page - three of them, dispatched via the
   `Agent` tool in a SINGLE message so they run concurrently. Give each one:
   the page path, **the register that page's path maps to**, and the verified
   corrections you found in step 5. The `writer` profile does not decide facts
   and does not decide register; you do, and you pass both in.

7. Roll their output into the SAME MR as Phase 1. No second MR, no second Task.

**The cap is 3 and it is deliberate.** Your stage budget is 2h
(`docStageBudget`), shared with Phase 1, and Phase 1 goes first because
documenting what shipped is this Task's reason to exist. Three pages of verify-
and-rewrite fits inside what Phase 1 leaves. Widening the SCOPE of the sort
does not widen the cap: the surface got bigger so each page's turn comes round
less often, which is the intended trade. Do not raise this number because a
particular night looked quiet - the budget does not grow with it, and a Phase 2
that eats the turn is how a shipped feature goes undocumented.

---

## 3b. Nothing to document: decline, do not go silent

If step 2 concludes no docs update is warranted **and** Phase 2 found the 3
stalest pages on the whole surface accurate and in their own register:

```
submit_outcome(action="declined", decline_reason="<what the batch covered and why none of it is doc-relevant>")
```

**A silent finish is NOT the no-op terminal.** A Task that receives no outcome
ages out at `parkReason=no-outcome`, its pod is deleted, and the batch is lost.
`action="declined"` IS the clean no-op: it moves the Task to `done` with
`stateReason=doc-timeout` - a declined batch is DONE, not parked, because there
was nothing to document - and stamps `documentedBy` on every Task in
`documentsTasks`, exactly as a submitted MR would.

Name what you looked at in `decline_reason` - both halves: which Tasks Phase 1
covered, and which 3 pages Phase 2 checked. "Nothing to do" is not a reason,
and a `decline_reason` that names no Phase 2 pages means Phase 2 did not run.
The one accepted substitute is the shallow-clone skip from Phase 2 step 1: if
history was unavailable, put that exact sentence in `decline_reason` instead of
a page list, so a reader can tell "nothing was stale" apart from "staleness
could not be measured".

---

## Decision table

| Situation | Correct call |
|---|---|
| A covered Task shipped an external-facing change the docs do not cover | edit docs, push, `mr_write(action="open")`, then `submit_outcome(action="submitted", ...)` |
| Nothing the batch covered warrants a doc change, but Phase 2 found real corrections on one of the 3 stalest pages | **still submit** - edit those pages, push, `mr_write(action="open")`, then `submit_outcome(action="submitted", ...)`. Say in the body that Phase 1 was a no-op |
| Both phases found nothing: everything covered is internal-only, and the 3 stalest pages are accurate and in-register | `submit_outcome(action="declined", decline_reason=...)`, naming the 3 pages you checked |
| Finishing the turn with no `submit_outcome` at all | **FORBIDDEN** - the Task ages out at `no-outcome` and the batch is lost |

## Before you stop

Write `task_note(kind="handoff", body=...)` - see `handoff`. If the review bounces
your MR back, the next docs pod on this Task reads it.

## Anti-patterns

- Deriving Phase 1's "what to document" from git history when `documentsTasks`
  already says exactly which Tasks this batch covers. Phase 2's staleness sort
  is the one legitimate use of git history in this turn.
- Editing any component repo - they are read-only clones, for reading only.
- Pushing to the docs repo's default branch.
- Updating docs "just in case" when the change is purely internal.
- Assuming the docs MR auto-merges without review. It goes to `awaiting-review`
  like every other MR on this platform.
- Merging anything. You have no merge action; the operator merges.
- Skipping Phase 2 because Phase 1 found something. They both run, every turn.
- Raising the Phase 2 cap above 3 pages. The 2h `docStageBudget` did not move.
- Running the Phase 2 sort on a shallow clone. Every page reports the same
  date, so the "3 stalest" are 3 arbitrary pages and the report is a lie.
