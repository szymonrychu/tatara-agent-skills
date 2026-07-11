---
name: tatara-pipeline-waiting
description: >
  Use whenever a tatara turn must WAIT for a CI/CD pipeline - a component CI
  build after a merge, a tatara-helmfile diff/apply run, or any `gh run` /
  `gh pr checks`. Teaches the heartbeat-poll loop that survives the turn
  inactivity timeout, how to tell an infra flap (re-run) from a real failure
  (fix), and when to stop waiting. Read before watching any pipeline.
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

While a single bash tool call is BLOCKING, you emit zero transcript activity.
So `gh run watch <id>` left to block for 20 minutes looks completely idle to the
wrapper for those 20 minutes. One long enough blocking watch (or a bare
`sleep 1800`) trips the inactivity timer and your turn is failed terminally
(reason `TurnTimeout`, pod deleted, task Failed - not retried).

**Therefore: never wait in one long blocking call. Poll in short cycles, and
emit a heartbeat line each cycle.** Each returned poll + your next line is fresh
activity that resets the timer, so you can wait through a pipeline of ANY length.

## The wait loop (use this)

```bash
RUN=<run-id>           # the run to wait on (see "pick the run" below)
REPO=szymonrychu/<component>
for i in $(seq 1 60); do            # ~60 cycles * 45s = up to 45 min
  read -r ST CC < <(gh run view "$RUN" -R "$REPO" --json status,conclusion \
                    -q '.status+" "+(.conclusion//"-")')
  echo "[wait $i] $RUN $ST/$CC $(date -u +%H:%M:%S)"   # heartbeat -> resets timer
  [ "$ST" = "completed" ] && break
  sleep 45
done
echo "FINAL $RUN $ST/$CC"
```

- Run this as ONE bash call per cycle is fine too, but the in-loop `echo`
  heartbeat is what matters: keep output flowing. Do NOT replace the loop with a
  bare `gh run watch` left to block silently, and never `sleep` more than ~60s
  without printing.
- Poll cadence: 30-60s. Tighter than ~15s just spams; slower than ~90s risks a
  silent gap. Match the wait to the job: component build/image 15-22 min,
  wrapper build 3-8 min, helmfile diff ~2 min, helmfile apply ~4 min.
- Idle polling costs ZERO model tokens (no LLM call happens inside the bash
  wait), so a long wait does not burn the token budget. It DOES hold a task
  lane, so do not wait on work you could have batched.

## Pick the run

The run you want is the one for YOUR commit, triggered by the merge:

```bash
gh run list -R szymonrychu/<repo> --branch main -L 5 \
  --json databaseId,headSha,event,status \
  -q '.[]|select(.headSha[0:7]=="<merge-sha>" and .event=="push")|.databaseId'
```

Watch the PR checks before merge with the same loop over
`gh pr checks <num> -R <repo>` (jobs flip pass/fail); watch the post-merge
`push` run for the image/chart publish.

## Flap vs real failure - decide before reacting

A failed run is often INFRA, not your code. Re-run infra flaps; only fix real
failures. Read the failed job log (`gh run view <id> -R <repo> --log-failed`)
and classify:

**Infra flap -> `gh run rerun <id> -R <repo> --failed` (do NOT touch code):**
- `Temporary failure in name resolution` / DNS / pip or npm or registry
  `Failed to establish a new connection` (egress flap).
- `502 Bad Gateway`, `503`, connection reset talking to GitHub or a registry.
- `The operation was canceled` with a uniform ~18 min runtime across jobs =
  control-plane node eviction of the pinned CI runner (not a test failure).
- `dial tcp buildkitd:1234 i/o timeout` = stale kube-proxy route; the build host
  self-heals or a re-run lands on a good route.
- ARC runner died on job pickup / `_work` EACCES = runner infra, re-run.

**Real failure -> fix the code, then push again (re-run will NOT help):**
- compile error, `go vet`, golangci-lint finding, a failing test assertion,
  `helm template` / chart-validate error, a genuine secret-scan hit.

Cap re-runs at 2 for the same run. If an infra flap persists past 2 re-runs,
stop and report it (it is a platform incident, not your task) rather than
looping.

## Publish + partial-publish awareness

- A merge to a component `main` triggers the publish run. tatara-operator ships
  TWO charts (tatara-operator + tatara-project) plus its image; its `chart` job
  loops `charts/*/` and pushes each. Job `success` = all artifacts published; a
  green `image` + green `chart` job means the helmfile bump will find them.
- Do not bump a tatara-helmfile pin until the publish run is green, or
  `helmfile apply` fails chart-not-found and blocks every deploy.

## When to stop waiting

- Pipeline `completed/success` -> proceed.
- `completed/failure` -> classify (flap vs real) and act per above.
- Still `in_progress` after the loop budget (~45 min) AND the job logs show no
  progress -> the pipeline is genuinely stuck, not slow. Stop polling, report it
  (incident), do not silently wait forever.

## Red flags - STOP

- A bare `gh run watch <id>` or `gh pr checks --watch` left to block with no
  heartbeat -> swap to the poll loop; the silent block can trip the inactivity
  timeout.
- `sleep` longer than ~60s without an echo -> shorten it; emit a heartbeat.
- Re-running a run that failed on a real compile/test error -> fix the code; a
  re-run repeats the failure and wastes ~20 min.
- Bumping a helmfile pin before its publish run is green -> apply will fail.
