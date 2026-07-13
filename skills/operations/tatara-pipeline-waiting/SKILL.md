---
name: tatara-pipeline-waiting
description: >
  Use whenever a tatara turn must WAIT for a CI/CD pipeline - a component CI
  build after a merge, a tatara-helmfile diff/apply run, or any forge CI check
  read via scm_read(kind=ci). Teaches the heartbeat-poll loop that survives the
  turn inactivity timeout, how to tell an infra flap (retrigger) from a real
  failure (fix), and when to stop waiting. Read before polling any pipeline.
profiles: ["implement", "review", "incident", "clarify"]
---

# tatara-pipeline-waiting

TASK content. Follow the wait loop exactly. Pipelines are slow (a component
build is 15-22 min; helmfile apply 4 min); waiting wrong gets your turn killed
or wastes it chasing a flap.

## The one fact that governs everything

`turnTimeoutSeconds` (the per-turn limit, live 2700s = 45 min) is an
**inactivity / stall** window, NOT a wall-clock cap. The wrapper resets it on
every chunk of agent transcript output, and fails the turn only after the
window elapses with NO activity.

So a single blocking call - a `sleep 1800`, a 20-minute `wait`, anything that
does not print - looks completely IDLE to the wrapper. It cannot see the
difference between "waiting on CI" and "hung". One long enough blocking call
trips the inactivity timer and your turn is failed TERMINALLY (reason
`TurnTimeout`, pod deleted, Task failed - not retried).

**Therefore: never wait in one long blocking call. Poll in short cycles, and
print a heartbeat line each cycle.** Each returned poll plus your next line is
fresh activity that resets the timer, so you can wait through a pipeline of ANY
length.

## The poll loop

Poll your own MR's CI state, never the repo's full run history and never a
blocking watch:

    while true:
        ci = scm_read(kind="ci", repo="<repo>", number=<mr>)

        print("heartbeat: ci=" + ci.status + " sha=" + ci.headSHA)   # <- this is what keeps your turn alive

        if ci.status in ("green", "red"):
            break
        if ci.status == "none" and elapsed > 3 minutes:
            break        # no pipeline registered; see below

        sleep 30

`scm_read(kind="ci")` is a POINT READ. It never blocks. The operator paces it
to one real forge fetch per 20 seconds per PR - poll faster than that and you
get the last result back with `"cached": true`, which costs the platform
nothing but also tells you nothing new. **30 seconds is the right interval.**
It is above the pacing window, and it is far below any plausible inactivity
timeout.

`status` is one of `none`, `pending`, `running`, `green`, `red`.

`checks[]` carries each check's name, status, conclusion and url. **For a
check that FAILED, and only for one that failed, it also carries `logTail`:
the last 4000 bytes of that job's log.** A green run's logs are never
fetched. You do not need to go and get them; you cannot, and you do not have
to.

- The `print(...)` heartbeat each cycle is what matters, not the exact shape
  of the loop: keep output flowing every cycle. Never replace the loop with
  one long blocking wait and no output in between.
- Poll cadence: 30s. Tighter just spams the pacing cache and comes back
  `"cached": true`; much slower risks a wider silent gap between heartbeats.
  Match the wait to the job: component build/image 15-22 min, wrapper build
  3-8 min, helmfile diff ~2 min, helmfile apply ~4 min.
- Idle polling costs ZERO model tokens (no LLM call happens inside the wait),
  so a long wait does not burn the token budget. It DOES hold a task lane, so
  do not wait on work you could have batched.

## There is no separate "pick the run" step

`scm_read(kind="ci", repo, number=<mr>)` always resolves to the CURRENT head
of that MR - there is no run-id lookup and no separate call for pre-merge PR
checks versus the post-merge publish run. Poll the same call before merge
(the PR's checks flip pass/fail) and after merge (the push-triggered publish
run); the tool tracks which SHA is current so you never have to hunt a run
list for it.

## Flap vs real failure - decide before reacting

A failed run is often INFRA, not your code. Only fix real failures - never
"fix" an infra flap by touching code. Read the failed check's `logTail` (it
is already in the `scm_read(kind="ci")` response above - nothing more to
fetch) and classify:

| Old CLI-shaped idea | Now |
|---|---|
| list the repo's recent runs and filter by your commit's SHA | `scm_read(kind="ci", repo="<repo>", number=<mr>)` - you are watching YOUR MR, not the repo's run list |
| list a PR's status checks | the `checks[]` array of the same response |
| view a failed run's log | the `logTail` field of the failed check |
| rerun a failed job | **NO EQUIVALENT. You cannot rerun a job - see below.** |

**Infra flap (retrigger, do NOT touch code - see "You cannot rerun a job"):**
- `Temporary failure in name resolution` / DNS / pip or npm or registry
  `Failed to establish a new connection` (egress flap).
- `502 Bad Gateway`, `503`, connection reset talking to the forge or a
  registry.
- `The operation was canceled` with a uniform ~18 min runtime across jobs =
  control-plane node eviction of the pinned CI runner (not a test failure).
- `dial tcp buildkitd:1234 i/o timeout` = stale kube-proxy route; a fresh run
  self-heals or lands on a good route.
- ARC runner died on job pickup / `_work` EACCES = runner infra, retrigger.

**Real failure -> fix the code, then push again (retriggering will NOT
help):**
- compile error, `go vet`, golangci-lint finding, a failing test assertion,
  `helm template` / chart-validate error, a genuine secret-scan hit.

## You cannot rerun a job

There is no rerun tool. If the failure is a genuine infra flap - a runner
that died, a registry timeout, a network blip, with the signatures above -
there are two options, and which ones are open to you depends on your
profile:

**implement / review only** - you hold `mr_write` and a git remote to push
to. Push an empty commit to retrigger the pipeline:
`git commit --allow-empty -m "chore: retrigger ci" && git push`

**incident / clarify - always this one, never the push above.** These
profiles are read/investigate-only (see `tatara-incident-investigation`
HARD RAIL: no pushes) with no `mr_write` and no forge write credential.
If you are running as incident or clarify and you hit an infra flap: say so
in your outcome / issue body and let a human (or the implement/review pod
that later owns this failure) push the retrigger. Never construct or run a
`git push` for this.

Both profiles: do NOT "fix" an infra flap by changing code. That is how a
green pipeline gets a spurious commit in it and how a real bug gets buried
under a workaround.

Cap retrigger attempts at 2 for the same failure (implement/review only). If
an infra flap persists past 2 retriggers, stop and report it (it is a
platform incident, not your task) rather than looping.

## Publish + partial-publish awareness

- A merge to a component `main` triggers the publish run. tatara-operator
  ships TWO charts (tatara-operator + tatara-project) plus its image; its
  `chart` job loops `charts/*/` and pushes each. Job `success` = all
  artifacts published; a green `image` + green `chart` job means the
  helmfile bump will find them.
- Do not bump a tatara-helmfile pin until the publish run is green, or
  `helmfile apply` fails chart-not-found and blocks every deploy.

## When to stop waiting

- Pipeline `status="green"` -> proceed.
- `status="red"` -> classify (flap vs real) and act per above.
- Still `pending`/`running` after the loop budget (~45 min) AND the checks
  show no progress -> the pipeline is genuinely stuck, not slow. Stop
  polling, report it (incident), do not silently wait forever.

## Red flags - STOP

- Any blocking call with no output - a bare `sleep 300`, a `wait` on a
  background job, a poll loop that prints nothing -> swap to the heartbeat
  poll loop; the silent block can trip the inactivity timeout.
- `sleep` longer than ~60s without a print in between -> shorten it; emit a
  heartbeat.
- Retriggering a pipeline for a failure that is a real compile/test error ->
  fix the code first; retriggering just repeats the failure and wastes ~20
  min.
- Bumping a helmfile pin before its publish run is green -> apply will fail.
