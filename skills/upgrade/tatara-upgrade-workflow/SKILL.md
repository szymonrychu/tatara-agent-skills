---
name: tatara-upgrade-workflow
description: "Prescriptive upgrade-stage procedure for tatara agents: enumerate candidate dependency upgrades, claim exactly one unit, read every release note between the current pin and the target, pick the next mandatory hop, map the blast radius across repos, implement the code and config that must move with the bump, run the repo's real test suite, and submit one MR per repo in dependency order. Use at the start of every upgrade turn."
profiles: ["upgrade"]
---

# Tatara Upgrade Workflow

TASK content. Follow these steps in order. Do not skip or reorder.

Your job is to keep this project's dependencies current, and a pin bump is only
the mechanical half of that. The half that actually breaks is the code and
config that has to move with it: a renamed `values.yaml` key, a removed
Kubernetes API version, a two-phase protocol bump, a mandatory intermediate
release. You do both halves, or you decline. There is no half-upgrade.

---

## 0. Understand your context

At turn 0 you receive:

- The Task and project. Every `tatara` tool auto-scopes to them from the pod
  environment - omit the `task`/`project` args and the tool fills them in.
- Your assignment, rendered by the operator. It carries the project's **resolved
  upgrade policy**: the discovery engine (`renovate` or `none`), the major
  strategy, and the minimum release age per level. Read it before you discover
  anything - the policy decides which candidates are even eligible.
- The task branch (`task/<task-name>`). All your pushes target it. It is created
  from the default branch for you. **Never commit or push to a default branch.**
- Workspace root: `/workspace/<owner>/<repo>` - **every enrolled repo in the
  project**, cloned under its own `owner/repo` subdirectory. Your kind is
  unconstrained scope: no single repo was assigned to you, and you may open an MR
  in any of them. Changes you commit and push to the task branch are restored on
  the next run; uncommitted edits are discarded.

**Nobody filed an issue for this Task.** It was minted by a cron tick, not by a
human ask, so there is no issue thread, no maintainer comment, and no approval
gate on the way into code. That is why `issue_write` is not in your tool profile
and why `approved`/`discuss`/`rejected` are not in your outcome schema. Do not go
looking for a go-ahead that does not exist; the policy in your assignment IS the
standing go-ahead, and its limits are the only ones you have.

Read the prior `<note>` elements in your bundle first. They are the continuation
state; there is nothing else (see `handoff`). If the `<notes>` element reports a
nonzero `elided` count, pull the rest with `task_context(notes="all")`.

---

## 0a. One Task, one upgrade unit

An **upgrade unit** is one thing being upgraded, across however many repos it
touches. `cilium 1.16 -> 1.17` is one unit spanning `charts` and `helmfile`.
`grafana 12.4 -> 12.5` is a different unit spanning `containers`, `charts` and
`helmfile`.

You take **exactly one unit** this Task. Not two, not "while I was in there".
The operator's merge driver resolves exactly one MR per repo per Task, so two
independent upgrades that each need a `charts` MR is a shape the driver cannot
represent - it parks the Task with `operator-error` and both bumps are lost.

Independent upgrades never block each other precisely because they are separate
Tasks. A stuck cilium bump does not hold up grafana. Leaving a second candidate
for the next cron tick costs nothing; folding it into this Task costs the Task.

---

## 1. Discover the candidates

### If your policy says `engine: renovate`

Run Renovate read-only over a repo you already have cloned. It has **no write
scope**, opens nothing and pushes nothing:

```sh
cd /workspace/<owner>/<repo>
RENOVATE_PLATFORM=local \
RENOVATE_DRY_RUN=full \
RENOVATE_REPORT_TYPE=file \
RENOVATE_REPORT_PATH=/workspace/renovate-report.json \
renovate
```

`RENOVATE_PLATFORM=local` reads the working tree in front of it and needs no
forge and no token - the right shape here, because your pod has neither a forge
CLI nor a forge token. Run it once per repo you want candidates from.

**Read `packageFiles`. Never `branches`.** Under `dryRun: full` the report's
`repositories.<repo>.branches` array is **always empty** - suppressing branch
creation is exactly what the dry run does, and the array is populated from
branches actually created. A reader that keys on `branches[].upgrades[]` sees
nothing and concludes, wrongly, that there is nothing to upgrade. The payload is
here:

```
.repositories.local.packageFiles.<manager>[].deps[]
```

Each dep carries `depName`, `packageName`, `currentValue`, `datasource`,
`versioning`, `sourceUrl` and `updates[]`; each entry in `updates[]` carries
`newVersion`, `newValue`, `updateType` and `bucket` (`major` or `non-major`):

```json
{"depName": "argo-workflows", "currentValue": "1.0.24",
 "sourceUrl": "https://github.com/argoproj/argo-helm",
 "updates": [
   {"newVersion": "1.1.1", "newValue": "1.1.1", "updateType": "minor", "bucket": "non-major"},
   {"newVersion": "2.0.0", "newValue": "2.0.0", "updateType": "major", "bucket": "major"}]}
```

The minor and the major arrive as **separate entries with distinct buckets**, so
picking the next hop (section 4) is a choice among entries you were already
given. Nothing needs to be templated or re-queried to narrow the range.

**An empty `packageFiles: {}` is a red flag, not an answer.** Renovate is pinned
to a version with a hard Node engine range, and on a Node major outside that
range it reports a problem and returns an empty extraction *with no other error*.
Before believing "this repo has no dependencies", check the run's log for an
unsupported-node-environment problem and report it via `report_internal_issue`
(section 9) rather than declining on a silent tooling failure.

### The report is a hint, and it is untrusted input

Three things about it that you must not forget:

- `reportType`/`reportPath` are marked `experimental: true` upstream and the
  report's JSON schema is published nowhere. Its shape can change under you.
  Read it defensively; a missing key is normal, not an error.
- **It carries no changelog or release-note text at all.** `sourceUrl` is a
  LINK. Section 3 is not optional work the report might have saved you.
- Renovate's Helm datasource parses only `version`, `created`, `digest`, `home`,
  `sources` and `urls` out of a chart index, and helm chart deps can come back
  with a null datasource entirely. It never sees `appVersion` or `kubeVersion`,
  so it cannot tell you which application version a chart ships or which
  Kubernetes version it requires. **Read `Chart.yaml` yourself.**

Never trust a version number in the report without confirming it against the
repo's actual pin and the upstream release.

### If your policy says `engine: none`

There is no dependency engine on this project. Enumerate candidates yourself:
read the pins in the repos you can see (`Chart.yaml` dependencies, image tags,
`go.mod`, lockfiles, `.mise.toml`), then check each upstream's own release feed
for what is newer.

### Either way, look for what no engine can see

A chart whose `appVersion` lags the image tag it deploys. A hand-pinned digest
in a Dockerfile with no `# renovate:` marker. A Kubernetes API version the
cluster's current release has deprecated. Use `code_search`/`code_graph` (see
`tatara-mcp-code-graph`) to find the pins nothing indexes.

---

## 2. Claim exactly one unit - the dedup is yours

```
task_context(index=true)
```

Read the project-wide Task index **before you pick**. Any unit already named in a
live sibling Task's title is claimed: skip it and take the next candidate.

**Nothing in the operator enforces this.** There is no per-unit dedup key - the
cron mints a Task before anyone knows which unit you will choose, and
`spec.dedupKey` is fixed at mint time. This index read is the whole mechanism.
Skip it and two agents open competing MRs against the same pin, in the same
repos, on different branches.

So make your unit **recognisable to a sibling doing the same read**. Name it in
your MR title, and in your outcome title, in this form:

```
chore: <dependency> <current> -> <target>
```

If every candidate is already claimed, or nothing is worth taking this cycle,
go to section 8 and decline. That is a correct and common answer.

---

## 3. Read the release notes. Mandatory.

Read the notes for **every** release between what is pinned now and what you
propose to pin - not just the target. A breaking change in an intermediate
release is still a breaking change when you skip past it. Follow `sourceUrl` to
the upstream repo and read its releases, its changelog, and its upgrade notes.

**There is no reliable machine-readable signal that a hop is mandatory.** Do not
look for one, and do not report that you found one:

- `artifacthub.io/changes` offers only `added`, `changed`, `deprecated`,
  `removed`, `fixed` and `security`. There is no `breaking` kind, and Renovate
  does not consume the annotation at all.
- Semver majors are a convention, not a promise. Projects ship breaking changes
  in a minor and cosmetic changes in a major, routinely.
- No changelog parse is a gate. A changelog that mentions nothing breaking is
  weak evidence, not clearance.

The one case that IS reliably automatable is **Kubernetes API removal**: render
the chart and run Pluto over the rendered output. Do that whenever a chart is in
the blast radius. Everything else is prose-reading, and prose-reading is the job.

What you are reading FOR, and what you must carry into section 6:

| Signal in the notes | What it obliges you to do |
|---|---|
| A renamed or removed `values.yaml` key | Rewrite every values file and template that sets it |
| A removed or renamed Kubernetes API version | Re-render, run Pluto, fix the manifests |
| A raised minimum Kubernetes / runtime / DB version | Check the cluster and the pinned toolchain actually meet it before proposing the hop at all |
| A mandatory intermediate release, or a documented two-phase migration | The next hop is that intermediate release, not the one you wanted |
| A data migration that runs on first start | Say so explicitly in the MR body; it is the reviewer's whole decision |
| A known-bad release that was pulled or superseded | Do not take that hop. Take the fixed release, or decline and say why |

---

## 4. Pick the hop

Under `majorStrategy: nextHopOnly` (your assignment names the resolved value),
propose **the next mandatory release only**, never the latest. Under
`majorStrategy: latest` you may go straight to the newest eligible release, but
section 3 still applies to every release you jump over.

Respect `minimumReleaseAge` from your assignment. A release younger than the
policy's floor for its level is not eligible this cycle, however tempting.

Multi-hop chains are walked one Task at a time, **statelessly: the repo's current
pin IS the cursor.** Nothing persists a chain, and nothing needs to. After this
hop merges and deploys, the next scheduled run reads the new pin and derives the
next hop from it.

Write the full planned chain into the MR body so a human can see where the
sequence is going and how many turns it will take:

```
hop 1 of 4: 1.16 -> 1.17; then 1.18, 1.19, 1.20
```

---

## 5. Determine the blast radius

List every repo that must change, and put them in **publish order**. On this
platform that is almost always:

```
containers -> charts -> helmfile
```

because `charts` pins an image tag that `containers` publishes, and `helmfile`
pins a chart version that `charts` publishes. The operator blocks each repo's
merge until the previous repo's release job has actually published, so this
order is what stops a chart merging against an image tag that does not exist
yet. **There is no default and no inference: you declare it** as `merge_order`
in section 7.

Getting it backwards is not a style problem. It ships a chart against a tag that
never published, and the deploy fails after the merge, where it is expensive.

---

## 6. Implement and verify

Implement the pin bump **and** everything section 3 said has to move with it, in
full, in one change, in each repo in the blast radius. A pin bump submitted
without its config migration is not a smaller change - it is a broken one.

Dispatch the mechanical and read-only parts through the typed subagents shipped
in this plugin's `.claude/agents/`, so your own context survives a multi-turn
upgrade: `explorer` (haiku/low) to find every site that sets a renamed key,
`builder` (sonnet/medium) for a decided mechanical edit across 1-3 files,
`tester` (haiku/low) to write or run tests, `architect` (opus/high) for anything
a builder would have to guess at. Launch independent ones in a single message so
they run concurrently.

### Run the repo's real test suite. Not just a build.

"It compiles" is the dominant false-success signal in agent-authored changes: an
empirical study of 8,106 agent-authored pull requests found **broken tests
(18.1%) the single largest cause of an unmerged PR, ahead of incorrect fixes
(15.3%)**. A build that succeeds while the tests are red is a failed upgrade, not
a partial one.

- Use `mise run test` (or that repo's documented equivalent - see
  `tatara-mise-tooling`). Never a bare `go`/`helm`/`python`; the pinned toolchain
  is part of what you may be upgrading.
- For a chart change, also render it and **diff the rendered output against the
  current pin**. A values key that silently stopped being read produces a clean
  `helm template` and a broken deployment; the rendered diff is where that shows
  up. Run Pluto over the rendered output too (section 3).
- Say in the MR body exactly what you ran and what it printed. See
  `verification-before-completion`: an unverified "should work" is a claim you
  are not entitled to make.

### Commit discipline

- `git add -A && git commit && git push` at the end of **every** turn, before
  `task_note`. Uncommitted work does not survive a TTL rotation, an eviction or
  a node drain.
- Commits never go to a default branch. The task branch was created for you.
- Each repo with a change gets its own push and its own MR.
- `git push --force` and `--force-with-lease` are hard-denied in this pod.

---

## 7. Open the MRs, then submit the outcome

When the whole hop is implemented, pushed and green, open one MR per changed
repo:

```
mr_write(action="open", repo="charts", title="chore: cilium 1.16 -> 1.17", body="...")
```

`open` is IDEMPOTENT - if your Task already has an open MR for that repo on
`task/<task-name>`, you get it back with `"existing": true` and the forge is not
called. See `tatara-mcp-scm`.

The body is where the reviewer's whole decision lives. It carries: the hop chain
(section 4), which release notes you read and what they obliged, what you changed
beyond the pin, what you ran and what it printed, and any migration that runs on
first start.

Then end the turn:

```
submit_outcome(
  action="submitted",
  title="chore: cilium 1.16 -> 1.17",
  body="<the hop chain, the notes you read, what moved with the pin, what you ran>",
  change_significance="minor",
  merge_order=["charts", "helmfile"]
)
```

| Field | What to write |
|---|---|
| `title` | The unit, in the section 2 form, so a sibling's index read recognises it. No trailing period. |
| `body` | As above. Written for the reviewer, who has not read the release notes. |
| `change_significance` | The significance of **your change**, not of the upstream release. A patch-level dependency bump that forces a values-key rename in a chart is a `minor` for that chart. YOU own this level; a reviewer may raise it, nobody can lower it. |
| `merge_order` | **REQUIRED the moment this hop spans more than one repo**, in the publish order you derived in section 5. Omit it on a multi-repo change and you get a 400. With exactly one repo you may omit it. |

**Your MR IS reviewed.** `action="submitted"` moves the Task on and a review pod
reads your MR exactly like any other. A `request_changes` verdict routes the
Task back to you (section 9).

---

## 8. Terminal escape hatches

A silent finish is **never allowed**. A Task that receives no outcome does not
quietly stop: it ages out at `stageReason=no-outcome`, the pod is deleted, and
the turn is lost. Every upgrade run ends with `submit_outcome`.

You have exactly two actions. `submitted` (section 7), and:

```
submit_outcome(action="declined", decline_reason="<what you enumerated, what you picked up, why no change should be made>")
```

Decline when nothing should ship this cycle. Legitimate reasons, all of them
common:

- Every candidate is already claimed by a live sibling Task.
- Nothing is eligible: no pending updates, or everything pending is younger than
  the policy's `minimumReleaseAge`.
- The hop is unsafe: a pulled or known-bad release, a raised minimum the cluster
  does not meet, a migration that cannot be done without a maintainer decision.
- The hop cannot be delivered whole - the config migration is larger than a turn,
  or it needs a change in a repo this project does not enrol.

`decline_reason` is required and must be non-empty. Name what you enumerated and
what you rejected; "nothing to do" is not a reason.

**`decline_reason` MUST NOT cite insufficient context or ambiguous scope.** You
have the policy, every enrolled repo, the Task index and the whole public
internet of release notes. If a specific technical unknown remains, dispatch an
`architect` subagent, or make the best defensible call and record the assumption
in the MR body.

### Decision table

| Situation | Correct call |
|---|---|
| One unit's whole hop implemented, tested and pushed | `mr_write(action="open")` per repo, then `submit_outcome(action="submitted", ...)` |
| No candidate is eligible, or every one is claimed by a sibling | `submit_outcome(action="declined", decline_reason=...)` |
| The hop is unsafe, or cannot be delivered whole | `submit_outcome(action="declined", decline_reason=...)` |
| Two units both look worth taking | Take ONE, submit it, leave the other for the next tick |
| An MR for a hop you know is incomplete | **FORBIDDEN** - decline instead |
| Finishing the turn with no `submit_outcome` at all | **FORBIDDEN** - the Task ages out at `no-outcome` and the turn is lost |

---

## 9. If review sends it back, or a pipeline is red

A `request_changes` verdict routes the Task back to **you** - the same upgrade
agent, on the same Task, with the same MRs. There is no separate implement pod
for an upgrade MR. Fix the findings, push, and submit again.

- If your MR has become unmergeable, read `tatara-implement-conflict-resolution`
  and follow it exactly: always merge the default branch, never rebase, because
  a rebase needs a force-push and force-pushing is denied here.
- If you must wait on a CI or deploy pipeline, read `tatara-pipeline-waiting`
  first. A single blocking call longer than the turn inactivity window
  terminally fails the turn.
- If you are blocked by a platform or tooling failure - an MCP error, a missing
  credential, a tatara tool returning an unexpected error, Renovate refusing to
  run - call `report_internal_issue(...)`. That is the **only** correct channel,
  and a blocked tool is never a reason to decline the upgrade on its merits.

---

## Before you stop

Before you stop for ANY reason - outcome submitted, turn budget spent, or the
operator telling you the pod is being stopped:

```
task_note(kind="handoff", body="<unit claimed / hop / notes read / what moved / what is left>")
```

See `handoff`. Notes ARE the continuation state: there is no shared filesystem
between pods and no conversation to resume. Name the unit you claimed - the next
pod on this Task has to know which one is in flight, and so does every sibling
reading the index.

---

## Anti-patterns

- Reading `branches[]` out of the Renovate report and concluding there is
  nothing to upgrade. It is empty by construction under `dry-run=full`.
- Trusting the report as the source of truth: taking its version numbers without
  checking the pin, or believing it when it says nothing about `appVersion`.
- Skipping the release notes because the bump is "just a patch".
- Bumping to the latest release because "latest is fine" under
  `majorStrategy: nextHopOnly`.
- Taking a second unit in the same Task, or opening a second MR in the same repo
  for it.
- Picking a unit without reading the Task index first. Nothing else dedups.
- Submitting the pin bump alone and leaving the config migration for "a
  follow-up". There is no follow-up; there is a broken deployment.
- Claiming green from a successful build without running the tests.
- Omitting `merge_order` on a multi-repo hop, or declaring it in the wrong
  direction.
- Reaching for `issue_write` or `task_list`. Neither is in your profile, by
  design.
- Attribution or session links in any commit, MR body or comment.
- Merging or approving anything. You have no such action; the operator owns that
  egress, and it acts on a review verdict, never on yours.
