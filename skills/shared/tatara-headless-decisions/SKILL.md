---
name: tatara-headless-decisions
description: "Step-by-step procedure for making and recording a decision without a human at the terminal: surface options via comment_on_issue and proceed; use decline_implementation only when completely blocked. Invoke whenever you would normally call AskUserQuestion, ExitPlanMode, or EnterPlanMode."
---

# Headless decision procedure

Tatara agent pods run headless. There is no human at the terminal. The three
Claude interactive tools `AskUserQuestion`, `ExitPlanMode`, and `EnterPlanMode`
are permanently denied in `settings.json` (they error on any call, even under
`bypassPermissions`). They cannot fire. Do not call them.

The issue thread is your only channel to a human. Every decision, question, or
clarification goes there via `comment_on_issue`.

---

## When to use this procedure

Use this procedure every time you would have called an interactive tool:

- You need to choose between two approaches with non-obvious tradeoffs.
- A requirement is ambiguous and the code + issue do not resolve it.
- You are about to take a destructive or hard-to-reverse action and want
  to flag the risk.
- You need to confirm scope before significant work.

Do NOT use it for trivia. If the answer is inferable from the issue text,
code, or git history, infer it, note your assumption in one line, and
proceed.

---

## Step-by-step procedure

### Step 1 - Decide whether you are actually blocked

If you can make a reasonable default choice and proceed safely, do so.
Note the choice in one sentence at the top of your next action ("Assuming
X; proceeding"). Skip to Step 5.

If you cannot proceed without human input (two paths both carry real risk
of being wrong and the cost of the wrong one is high), continue to Step 2.

### Step 2 - Draft the comment body

The body must contain:

1. **Context** (one to two sentences): what you were about to do and what
   stopped you.
2. **Options** (bullet list): each option labeled A, B, C. One sentence per
   option: what it is and its key tradeoff.
3. **Recommendation**: the option you would pick and why, in one sentence.
4. **Your default**: what you will do if there is no reply within a
   reasonable turn window. This prevents the task from stalling silently.

Keep the body under 20 lines.

### Step 3 - Post the comment via comment_on_issue

Required args (all must be non-empty):

```
comment_on_issue(
  repo   = "<owner>/<repo>",          // e.g. "szymonrychu/tatara-operator"
  number = <issue_number>,             // integer, the issue this task works on
  body   = "<your drafted body>",
  // project: omit; resolved from env TATARA_PROJECT automatically
)
```

`project` is read from the environment variable `TATARA_PROJECT` when not
supplied. You do not need to pass it explicitly.

### Step 4 - Continue with your stated default

Do not wait for a reply. Proceed immediately with the default you declared
in Step 2. The human will see the comment in the issue thread and can steer
the next turn if they disagree.

If the decision truly blocks all forward progress (no safe default exists),
go to Step 5 instead.

### Step 5 - Declare a hard block via decline_implementation

Use this only when:
- No option is safe to proceed with without human guidance, AND
- You have already posted a comment (Step 3) explaining the situation.

Required args:

```
decline_implementation(
  reason = "<concise explanation of what you tried, what the block is, and
             what the human needs to resolve before a new task can proceed>",
  // task: omit; resolved from env TATARA_TASK automatically
)
```

`task` is read from `TATARA_TASK` when not supplied.

This parks the task and posts the reason to the issue. The operator will
create a new task on the next scan once the human has commented.

---

## Decision table

| Situation | Action |
|-----------|--------|
| Clear enough to infer a default | Note assumption, proceed |
| Ambiguous, but one option is obviously safer | Pick it, post comment noting choice |
| Two viable options with real risk on the wrong pick | Post comment (Steps 2-3), proceed with stated default (Step 4) |
| Completely blocked, no safe default | Post comment, then decline_implementation (Step 5) |
| Tempted to call AskUserQuestion / ExitPlanMode / EnterPlanMode | Use comment_on_issue instead; the interactive tools are denied |

---

## Worked example

Scenario: you are implementing an issue that asks to "add retries to the
ingester". You are unsure whether the retry limit should be 3 (fast failure)
or 10 (tolerant of slow Ceph). The issue does not say.

**Bad (DO NOT DO):**
```
AskUserQuestion("Should I use 3 or 10 retries?")
```
This errors. The tool is denied.

**Correct:**

Post via `comment_on_issue`:
```
Decision needed: retry limit for the ingester.

Options:
A. 3 retries - fails fast, surfaces errors quickly, may cause false negatives
   under brief Ceph latency spikes.
B. 10 retries - tolerant of slow storage, delays error visibility by ~90 s.

Recommendation: B (10) - Ceph latency spikes are common in this cluster
and the ingester is not latency-sensitive.

Proceeding with B unless you comment otherwise before the next operator scan.
```

Then implement with 10 retries. Continue. Do not wait.

---

## Source references

- Deny list: `tatara-claude-code-wrapper/internal/bootstrap/settings.go` (line 33)
- Headless directive text injected into every agent's `CLAUDE.md`:
  `tatara-claude-code-wrapper/internal/bootstrap/bootstrap.go` (const `headlessDirective`, line 295)
- `comment_on_issue` tool schema and handler:
  `tatara-cli/internal/mcp/tools.go` (line 749); args: `repo` (string), `number` (integer), `body` (string); `project` from env `TATARA_PROJECT`
- `decline_implementation` tool schema and handler:
  `tatara-cli/internal/mcp/tools.go` (line 570); args: `reason` (string); `task` from env `TATARA_TASK`
