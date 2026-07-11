---
name: tatara-review-checklist
description: >
  Prescriptive PR/MR review gate for kind=review Tasks: build + test + lint the
  checked-out PR head locally, evaluate correctness/security/quality/test
  dimensions, apply severity routing to decide approve/request_changes/comment,
  and call review_verdict before finishing. Use whenever the turn-0 directive
  confirms this is a review task (contains "This is an MR/PR REVIEW").
profiles: ["review"]
---

# tatara-review-checklist

TASK content. Follow these steps exactly, in order, for every kind=review turn.

The PR head branch is already checked out at `/workspace/<owner>/<repo>` when
this turn starts. The workspace is transient and read-only: nothing you write
to disk is kept, so communicate exclusively through `review_verdict`.

---

## Step 1 - Orient

Confirm context before touching code.

```
task_get(task="$TATARA_TASK")
```

Verify `kind=review`. Note the PR/MR reference from the task spec.

Then understand the diff scope:

```sh
cd /workspace/<owner>/<repo>
git log origin/main..HEAD --oneline
git diff origin/main..HEAD --stat
```

Read the diff (`git diff origin/main..HEAD`) for any files where stat shows
meaningful change. Use `code_search` or `code_entity` from the code-graph tools
to navigate unfamiliar call sites without reading entire files.

Also check the PR/MR's mergeability state (from your turn-0 context, or via
`task_get` if not already present - do not re-crawl SCM for state already
injected). If it is unmergeable (conflict, failed required CI), that fact
alone routes the outcome to "changes required, route to implement" (Step 4) -
still run Steps 2-3 for whatever evidence you can gather, but the verdict
must not be `approve`.

---

## Step 2 - Build, test, lint (required)

Do this for every changed repo under `/workspace`. Do not skip even if the diff
looks trivial. A failing test or lint error is a finding, not a reason to abort.

```sh
cd /workspace/<owner>/<repo>
mise install                            # install pinned toolchain once
mise run build    # or: mise exec -- go build ./...
mise run test     # or: mise exec -- go test ./...
mise run lint     # or: mise exec -- golangci-lint run
```

If the repo has no `.mise.toml` or no build/test/lint tasks, note
"no build targets found" and proceed.

Record exactly:
- Commands run (full invocation)
- Exit code
- Pass/fail count or first error line

This evidence goes verbatim into the verdict body.

---

## Step 3 - Evaluate dimensions

For each dimension: record finding (pass or severity+evidence) and skip none.

### 3a. Correctness

- Logic errors, off-by-ones, nil dereferences, race conditions
- Dropped or incorrectly wrapped errors (Go: `fmt.Errorf("ctx: %w", err)` expected)
- Contract violations (wrong function semantics, interface misuse)
- Data loss or corruption paths

### 3b. Security

- Secret or credential exposure (env vars logged, plaintext in YAML/values)
- Injection risks (shell, SQL, Go template)
- Auth/authz bypass or missing enforcement gate
- Insecure type assertions or deserialization

### 3c. Quality

- YAGNI/KISS violations: abstraction introduced for a single call site
- DRY violations: non-trivial logic copy-pasted more than twice
- Missing structured INFO log for every business action (with fields: action,
  resource_id, duration_ms where relevant) - platform rule
- Missing Prometheus counter/histogram/gauge for anything that counts, times
  out, or can fail - platform rule
- Naming clarity, dead code, unnecessary complexity

### 3d. Tests

- New behavior covered by tests?
- Go: table-driven tests with `t.Run`?
- Added tests actually compile and run (not skipped)?
- Build + lint still pass with the new tests in place?

---

## Step 4 - Severity routing

| Condition | `decision` |
|---|---|
| All dimensions pass, build + tests + lint pass | `"approve"` |
| Any correctness or security finding | `"request_changes"` |
| Quality or test gap only (no correctness/security issue) | `"request_changes"` (must-fix) or `"comment"` (optional) |
| Concerns noted but safe to merge; no blocking issue | `"comment"` |
| PR/MR is unmergeable (conflict or failed required CI), regardless of code quality | `"request_changes"` - this routes the Task back to `implement` |

Use `"request_changes"` for anything that must be resolved before merge.
Use `"comment"` for style or quality concerns the author may address at will.
Use `"approve"` only when every gate above passes.

`approve` never merges anything. Approving means: apply `tatara-approved` and
post a native PR/MR approval; the operator's deploy supervisor is the ONLY
caller that ever merges, and only once CI is green AND the approval is set.
`review` calling `approve` on an unmergeable PR is a protocol violation - the
mergeability check in Step 1 must gate this before you compose the verdict.

---

## Step 5 - Submit review_verdict (required)

Compose the verdict body:

1. One-sentence summary (approve / requesting changes / noting concerns).
2. Test run: commands run, exit codes, pass/fail count.
3. Findings per dimension - format each as:
   `FINDING [severity: critical|high|medium|low] - <file:line> - <description>`
   Omit passing dimensions or write "no issues found".
4. Inline suggestions (optional): include in `suggestions` array only when you
   can specify the exact replacement (path + line + body all known).

Call `review_verdict` - this is the sole required tool call and must complete
before the turn ends:

```
review_verdict(
  task="$TATARA_TASK",               # omit if TATARA_TASK env is set; auto-read
  decision="approve"|"request_changes"|"comment",
  body="<verdict body>",
  suggestions=[                      # optional; omit array entirely if none
    {
      "path": "internal/foo/bar.go", # repo-relative path
      "line": 42,                    # integer
      "body": "suggested fix or note"
    }
  ]
)
```

All three fields (`path`, `line`, `body`) are required on every suggestions
item. Omit the `suggestions` key entirely rather than passing an empty array
or partial items.

---

## Step 6 - Finish

After `review_verdict` returns, the turn is complete. Hard stops:

- Do NOT `git commit` or `git push` anything.
- Do NOT call `change_summary`, `pr_outcome`, or `decline_implementation`
  (those are implement-profile tools, not available in this profile).
- Do NOT open, comment on, or close issues.

If a platform tool failed (MCP error, tool unavailable) during the review,
call `report_internal_issue` with the exact error and the tool name, then note
the incomplete check in the verdict body with its impact on confidence.
