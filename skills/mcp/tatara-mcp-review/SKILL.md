---
name: tatara-mcp-review
description: >
  Drive the two MCP tools available in the review agent profile
  (review_verdict, submit_handover): exact arg shapes, decision rules,
  sequencing, and the per-MR semver assignment carried on approve. Use
  whenever you are running as a kind=review task and must deliver a verdict
  on a human-authored PR/MR.
profiles: ["review"]
---

# tatara-mcp-review

You are in a `kind=review` task. The PR/MR head branch is already checked
out at `/workspace/<owner>/<repo>`. Two operator tools are available:
`review_verdict` (required, call exactly once at the end) and
`submit_handover` (optional, call any time to park your working notes).

Do NOT commit, push, open a PR, or call any tool not listed in this skill.
Communicate only through `review_verdict`.

---

## Tool index

| Tool | Required args | Optional args |
|------|--------------|--------------|
| `review_verdict` | `decision` | `task`, `body`, `suggestions`, `semver` |
| `submit_handover` | `handover` | `task` |

`task` defaults to the `TATARA_TASK` env var in both tools. Omit it unless
you are explicitly overriding which task you are filing against.

---

## Workflow

Follow these steps in order.

### Step 1 - Read and test the change

The PR head is checked out. Do all of this before forming a verdict:

1. Read the diff: `git -C /workspace/<owner>/<repo> diff main...HEAD`
2. Inspect changed files.
3. Build and run tests/linters if the repo supports it. Note what you ran
   and the exit code.
4. Check for correctness, security, and quality issues.

Nothing you write to disk is kept. The workspace is transient.

### Step 2 - (Optional) Submit a handover before finishing

If your context is growing large, or if you want the next agent to have
your investigation notes regardless of verdict, call `submit_handover`
before the verdict:

```
submit_handover(
  handover="<working notes, evidence gathered, tests run, findings>"
)
```

- `handover` is a plain string. Max 16 KB; the server truncates at a UTF-8
  rune boundary silently if you exceed it. Keep it under 16 000 bytes.
- Call at most once per task. A second call overwrites the first.
- This is never required. Skip it if context is light.

### Step 3 - Call review_verdict (required)

Call exactly once before the session ends.

```
review_verdict(
  decision="<approve | request_changes | comment>",
  body="<narrative summary of findings>",
  suggestions=[...],  # only when decision=request_changes
  semver=[...]        # only when decision=approve; see below
)
```

The operator's writeback controller reads `Status.ReviewVerdict` and posts
it to SCM. After posting, the task transitions to "Reviewed" and the pod
terminates. A missing verdict leaves the task stuck.

---

## Decision table

| Situation | decision | body | suggestions |
|-----------|----------|------|-------------|
| Change is correct, tests pass, no issues | `approve` | Summary of what you verified | omit |
| Change has blocking issues that must be fixed before merge | `request_changes` | Explanation of each issue | include (see below) |
| You have questions or non-blocking notes but no position to approve/reject | `comment` | Your questions or notes | omit |
| PR/MR is unmergeable (conflict or failed required CI) | `request_changes` | State the mergeability problem plainly; this routes the Task back to `implement` | omit unless you also have code findings |

Use `comment` sparingly. If you can form a clear position, use `approve`
or `request_changes` instead.

`approve` does not merge anything - it applies the `tatara-approved` label
and posts a native approval; the operator's deploy supervisor is the sole
merge caller, gated on green CI AND the approval. Never call `approve` on an
unmergeable change even if the code itself looks correct; the mergeability
check comes first.

---

## Inline suggestions (request_changes only)

`suggestions` is only sent to SCM when `decision=request_changes`. For
`approve` and `comment`, any `suggestions` array you provide is silently
ignored by the writeback controller.

Each item in `suggestions`:

```json
{
  "path": "internal/foo/bar.go",
  "line": 42,
  "body": "Consider wrapping the error: fmt.Errorf(\"context: %w\", err)"
}
```

| Field | Type | Constraint |
|-------|------|------------|
| `path` | string | Repository-root-relative path to the file |
| `line` | integer | Line number in the file (>= 1) |
| `body` | string | The suggestion text; shown as a review comment |

All three fields are required on every suggestion object. Omit the array
entirely if you have no inline suggestions.

---

## Semver assignment (approve only)

`semver` is only sent to SCM when `decision=approve`. For `request_changes`
and `comment`, any `semver` array you provide is silently ignored by the
writeback controller - nothing merges on those decisions, so there is
nothing to tag.

When you approve, assign a release level to EVERY MR in the stream, not
just the one you built/tested - each repo touched by this stream has its
own PR/MR, and each one gets its own entry. This includes
human/maintainer-authored MRs: review is the only point in the pipeline
that ever stamps a release level on a human PR, since humans never call
`change_summary`. Skip a human MR here and it merges with no release label
- push-CD then has nothing to cut a tag from.

Judge the level from each MR's diff:

| Diff shape | `level` |
|---|---|
| Breaking change | `major` |
| Backward-compatible feature | `minor` |
| Fix, refactor, docs, chore, other | `patch` |

Each item in `semver`:

```json
{
  "repo": "acme/api-service",
  "number": 142,
  "level": "minor"
}
```

| Field | Type | Constraint |
|-------|------|------------|
| `repo` | string | `owner/repo` slug of the MR's repo |
| `number` | integer | PR/MR number in that repo |
| `level` | string | one of `major`, `minor`, `patch` |

All three fields are required on every `semver` item. If a member MR
already carries a `semver:*` label (visible in the turn-0 bundle or via
`task_get`), assign your best judgment anyway - the operator keeps an
existing human-set label over your assignment, so there is no harm in
always emitting one; it only fills the gap when the label is missing.

---

## Worked examples

### Approve a single human PR (one repo, one semver entry)

The whole stream is one repo, one MR - `semver` still carries one entry for
the source PR, human-authored or not.

```
review_verdict(
  decision="approve",
  body="Reviewed main.go and pkg/handler.go. Tests pass (go test ./... exit 0). Change is correct; error is wrapped and the nil check is safe.",
  semver=[
    {
      "repo": "acme/api-service",
      "number": 142,
      "level": "patch"
    }
  ]
)
```

### Approve a multi-repo umbrella (one entry per member PR)

A stream spanning several repos gets one `semver` entry per member MR, each
judged independently from its own diff - here the API repo shipped a
backward-compatible new endpoint (`minor`) while the docs repo only updated
prose (`patch`), even though both belong to the same approved stream.

```
review_verdict(
  decision="approve",
  body="All three member MRs build, test, and lint clean. api-service adds a new endpoint (backward compatible); docs and helm-chart are follow-on updates.",
  semver=[
    {
      "repo": "acme/api-service",
      "number": 142,
      "level": "minor"
    },
    {
      "repo": "acme/docs",
      "number": 58,
      "level": "patch"
    },
    {
      "repo": "acme/helm-chart",
      "number": 9,
      "level": "patch"
    }
  ]
)
```

### Request changes with inline suggestions

```
review_verdict(
  decision="request_changes",
  body="Two issues: unwrapped error in handler.go:42 and missing bounds check in parser.go:17.",
  suggestions=[
    {
      "path": "pkg/handler/handler.go",
      "line": 42,
      "body": "Wrap the error: return fmt.Errorf(\"handle request: %w\", err)"
    },
    {
      "path": "pkg/parser/parser.go",
      "line": 17,
      "body": "Add bounds check before indexing: if i >= len(tokens) { return nil, ErrShortInput }"
    }
  ]
)
```

### Comment (questions only)

```
review_verdict(
  decision="comment",
  body="Why is the retry count hardcoded to 3? Should this come from config? Not blocking, but worth clarifying before merge."
)
```

---

## Anti-patterns

- Do NOT call `review_verdict` more than once. The second call overwrites
  the first; the first SCM post may already have been made.
- Do NOT include `suggestions` when `decision=approve` or `decision=comment`.
  The writeback controller only calls `Suggest()` on `request_changes`.
- Do NOT include `semver` on `request_changes` or `comment` - it is silently
  ignored. Do NOT omit it on `approve` for a human MR just because a human
  didn't call `change_summary` - your judgment is the only stamp it gets.
- Do NOT commit or push changes. The workspace is read-only for review; no
  changes are kept.
- Do NOT call `pr_outcome`, `issue_outcome`, `comment`, `comment_on_issue`,
  or any other operator tool. The review profile only exposes `task_update`,
  `subtask_list`, `review_verdict`, and `submit_handover`.
- Do NOT finish without calling `review_verdict`. A silent exit leaves the
  task in WritebackPending forever.
- Do NOT set `line=0`. The `Suggestion.Line` field has a minimum of 1.
