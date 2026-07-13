---
name: tatara-headless-decisions
description: "Step-by-step procedure for making and recording a decision without a human at the terminal: proceed on your best-judgment default, use whatever comment tool your profile owns (if any) to surface it, and fall back to your kind's blocked/discuss outcome shape only when no safe default exists. Invoke whenever you would normally call AskUserQuestion, ExitPlanMode, or EnterPlanMode."
profiles: ["*"]
---

# Headless decision procedure

Tatara agent pods run headless. There is no human at the terminal. The three
Claude interactive tools `AskUserQuestion`, `ExitPlanMode`, and `EnterPlanMode`
are permanently denied in `settings.json` (they error on any call, even under
`bypassPermissions`). They cannot fire. Do not call them.

Your channel to a human is not uniform across profiles - it depends on which
SCM write tool your kind owns (see `tatara-platform-contract`'s tool surface
table and `tatara-mcp-scm`). Know your channel before you need it.

---

## Your channel, by profile

| Profile | Direct comment channel | If you have none (or none yet) |
|---|---|---|
| `clarify`, `refine` | `issue_write(action="comment")` on the issue you own | n/a - you always have one |
| `implement`, `review`, `documentation` | `mr_write(action="comment"\|"reply")`, but only once your Task has an open MR | Proceed on your default; surface reasoning at outcome time instead |
| `brainstorm`, `incident` | none | Proceed on your default; surface reasoning at outcome time |

`task_note(kind=note)` is NOT a channel to a human. It is read by the next
pod and the operator's own logs (see `tatara-mcp-platform`), never rendered
to the issue or MR thread. Use it to record your reasoning for continuity,
not to reach a maintainer.

"Surface reasoning at outcome time" means: put the tradeoff and your default
choice into the `reason` / `decline_reason` / finding body your kind's
`submit_outcome` shape requires. When a Task enters `failed`, `rejected`, or
a parked state, the operator posts a bot comment on every owned open issue
naming the reason - that is how your decision reaches a human if you had no
direct comment tool this turn.

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
X; proceeding") and record it via `task_note(kind=note)` for continuity.
Skip to Step 4.

If you cannot proceed without human input (two paths both carry real risk
of being wrong and the cost of the wrong one is high), continue to Step 2.

### Step 2 - Draft the message

Whichever tool carries it (a direct comment, or your outcome's `reason`
field), the message must contain:

1. **Context** (one to two sentences): what you were about to do and what
   stopped you.
2. **Options** (bullet list): each option labeled A, B, C. One sentence per
   option: what it is and its key tradeoff.
3. **Recommendation**: the option you would pick and why, in one sentence.
4. **Your default**: what you will do (or already did) if there is no reply.
   This prevents the task from stalling silently.

Keep it under 20 lines.

### Step 3 - Post it, if you can

If your profile owns `issue_write` (clarify, refine) or already has an open
MR to comment on via `mr_write` (implement, review, documentation), post the
message now. Otherwise skip straight to Step 4 - there is nothing to post to
yet, and there will not be until your outcome carries it.

### Step 4 - Continue with your stated default

Do not wait for a reply. Proceed immediately with the default you declared
in Step 2. A human who disagrees can steer the next turn - via a comment on
whatever thread you posted to, or via the issue thread once your outcome's
reason is posted there by the operator.

If the decision truly blocks all forward progress (no safe default exists),
go to Step 5 instead of proceeding.

### Step 5 - Declare a hard block via your kind's outcome shape

Use this only when:
- No option is safe to proceed with without human guidance, AND
- You have already posted a comment (Step 3) when your profile allowed one.

Each kind has exactly one blocked/discuss shape - see `tatara-mcp-outcome` for
the full schemas:

| Kind | Call |
|---|---|
| `implement`, `documentation` | `submit_outcome(action="declined", decline_reason="...")` |
| `brainstorm` | `submit_outcome(action="skip", reason="...")` |
| `incident` | `submit_outcome(action="false_positive", alert_rules=[...], reason="...")` |
| `clarify` | `submit_outcome(decision="discuss", reason="...")` - a genuine question for a human, not a platform defect |
| `refine` | `submit_outcome()` with no folds/closes/links - a safe no-op turn; explain why in `task_note` |
| `review` | there is no blocked shape - see the note below |

`review` has only `verdict="approve"|"request_changes"`; there is no third
option. If you cannot form a confident verdict, that is itself a finding:
submit `verdict="request_changes"` with a finding that states the ambiguity
and what a human needs to resolve it. If the blocker is a platform defect
(the MR is unreadable, CI tooling is broken) rather than a genuine review
question, use `report_internal_issue` instead and still submit the best
verdict you can form from what you did read.

A blocker caused by a broken tool, a contradictory directive, or unreachable
infrastructure is NEVER a `decline`/`skip`/`discuss` - that is
`report_internal_issue` territory (see `tatara-platform-contract`). Reserve
the outcome-shaped block for genuine human decisions.

This parks or declines the task and, for `failed`/`rejected`/parked
transitions, the operator posts your reason to the issue thread automatically.

---

## Decision table

| Situation | Action |
|-----------|--------|
| Clear enough to infer a default | Note assumption in `task_note`, proceed |
| Ambiguous, but one option is obviously safer | Pick it, post via your profile's channel if you have one, proceed |
| Two viable options with real risk on the wrong pick | Post if you have a channel (Step 3), proceed with stated default (Step 4) |
| Completely blocked, no safe default | Post if you have a channel, then use your kind's outcome shape (Step 5) |
| Blocked by a platform/tooling failure, not a human decision | `report_internal_issue`, not an outcome block |
| Tempted to call AskUserQuestion / ExitPlanMode / EnterPlanMode | Use this procedure instead; the interactive tools are denied |

---

## Worked example

Scenario: you are an `implement` pod working an issue that asks to "add
retries to the ingester". You are unsure whether the retry limit should be 3
(fast failure) or 10 (tolerant of slow Ceph). The issue does not say. Your
Task does not yet have an open MR - you have not pushed anything yet, so
`mr_write(comment)` has nothing to attach to.

**Bad (DO NOT DO):**
```
AskUserQuestion("Should I use 3 or 10 retries?")
```
This errors. The tool is denied.

**Correct:**

Record the assumption and proceed - you have no comment channel yet:
```
task_note(kind="note", body="Retry limit ambiguous (3 vs 10). Ceph latency
spikes are common in this cluster and the ingester is not latency-sensitive.
Proceeding with 10; will note in the PR body.")
```

Implement with 10 retries, push, `mr_write(action="open", ...)`. Once the MR
exists you have a channel - if a maintainer later comments disagreement,
answer via `mr_write(action="reply", in_reply_to=...)` in a later turn. If
you were instead blocked outright (say, the issue's requirement genuinely
contradicts another open MR in the same task), call
`submit_outcome(action="declined", decline_reason="...")` describing the
conflict and what a human needs to resolve before a new task can proceed.

---

## Source references

- Deny list: `tatara-claude-code-wrapper/internal/bootstrap/settings.go` (line 33)
- Headless directive text injected into every agent's `CLAUDE.md`:
  `tatara-claude-code-wrapper/internal/bootstrap/bootstrap.go` (const `headlessDirective`)
- `submit_outcome` schemas and profile gating: contract D.1, D.6; see `tatara-mcp-outcome`
- `issue_write` / `mr_write` schemas: contract D.2; see `tatara-mcp-scm`
- `report_internal_issue`: see `tatara-mcp-platform`
