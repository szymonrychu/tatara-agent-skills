---
name: tatara-incident-investigation
description: Use on a tatara incident task (kind=incident, fired by a Grafana alert) to gather read-only evidence from Grafana, form a diagnosis, then finish with submit_outcome exactly once - file a new issue (action=file_issue, optionally linked under a related open tracker), comment fresh evidence onto an existing tracker for the SAME incident (action=comment_issue), or declare a false positive (action=false_positive) - and stop.
profiles: ["incident"]
---

# tatara incident investigation

This is **reference content**: heuristics and hard rails that run inline
alongside your judgment. It does not script ideation or drive the
investigation mechanically. Where a rule is a hard rail, it is marked
**[HARD RAIL]**. Everything else is advice - apply it, override it
when the evidence demands, but note why.

## Context

You are running as an incident task agent. The operator injected an alert
context block (group key, status, labels, annotations, generatorURL,
externalURL) as your assignment. Your job: investigate live via the
`grafana` MCP server (read-only), form a diagnosis, and hand one
evidence-backed issue to the team. Nothing else.

Tool surface available in the incident profile:

- Grafana MCP server: query Prometheus/Loki, read alert rules and
  dashboards, follow generatorURL - all read-only.
- `submit_outcome` - your ONE terminal tool, in the incident shape
  (`tatara-mcp-outcome`).
- `task_get`, `task_context`, `task_note`, `task_list`, `project_get`,
  `repo_list`, `report_internal_issue`.
- `scm_read` - read issues, MRs, comments, commits and CI
  (`tatara-mcp-scm`).
- The four code-graph tools and all five memory tools, for cross-referencing
  platform context (`tatara-mcp-code-graph`, `tatara-mcp-memory`).

**You have NO `issue_write` and NO `mr_write`.** You cannot open an MR, and you
cannot edit or close anything directly, or comment via a general-purpose comment
tool - none exists in this profile. Your voice on the forge is entirely mediated
by `submit_outcome`: the OPERATOR files a new issue from an accepted
`action="file_issue"`, or posts your evidence as a COMMENT on an existing open
incident tracker issue from an accepted `action="comment_issue"`. The comment
path is gated server-side to incident tracker issues only - you can never
comment on an arbitrary human issue, only on a tracker your own survey found.

## Hard rails

**[HARD RAIL]** `submit_outcome` is called EXACTLY ONCE, and it is not optional.
Two calls is a bug; zero calls ages the Task out at `stageReason=no-outcome`,
deletes the pod, and loses the work. The three shapes:

```
submit_outcome(action="file_issue",
               alert_rules=["<rule name>", ...],   # >=1, required
               reason="<why this is real, in one or two lines>",
               issue={"repo": "...", "title": "...", "body": "...",
                      "parent": {"repo": "...", "number": ...}})  # optional

submit_outcome(action="comment_issue",
               alert_rules=["<rule name>", ...],   # >=1, required
               reason="<why this is the SAME incident as the tracker below>",
               comment={"repo": "...", "number": ..., "body": "..."})

submit_outcome(action="false_positive",
               alert_rules=["<rule name>", ...],   # >=1, required
               reason="<the evidence that says the alert is not real>")
```

`alert_rules` and `reason` are REQUIRED on ALL THREE: the alert rule(s) your
verdict covers, from the alert context, and why you decided what you decided.

`issue.parent` is OPTIONAL on `file_issue` - set it to `{repo, number}` when
your finding is genuinely-new-but-RELATED to an open tracker you found in your
survey (a distinct problem sharing context or root cause). The operator links
your new issue as a GitHub sub-issue under `issue.parent` and cross-references
both.

Use `action="comment_issue"` instead of `file_issue` when your fresh evidence
is about the SAME incident (the same underlying root problem, not merely the
same alert firing) as an open tracker you found in your survey. It appends
your evidence to that tracker as a comment; no new issue is filed. This is the
tool for "I re-investigated and it's still the thing #<n> already tracks" -
use it instead of filing a near-duplicate.

**[HARD RAIL]** The issue body MUST contain all four of: the alert summary, the
queries/tools you ran with their actual results, your diagnosis, and the Grafana
links (generatorURL and externalURL from the alert context). A proposal missing
any of these will fail downstream.

**[HARD RAIL]** The `comment.body` on `comment_issue` carries the same evidence
bar as a fresh issue: the queries you ran, their results, your (possibly
updated) diagnosis, and the Grafana links. It is a comment, not a stub - the
tracker's next reader must be able to see what changed since the last update
without re-running your queries.

**[HARD RAIL]** This is a READ-ONLY investigation. Take no remediation,
write, or corrective action on any system. Your only output is the filed
issue, the tracker comment, or a false-positive verdict. No `kubectl`, no
helm, no config changes, no pushes.

**[HARD RAIL]** Platform/tooling failures (Grafana 401, MCP server
unreachable, missing credentials) are reported via `report_internal_issue`
with the concrete tool name, exact error, and what you were attempting.
That is the ONLY correct channel. Do NOT open a tracker issue asking a
human to fix the platform. Do NOT treat a blocked tool as a reason to
file your normal incident output.

**[HARD RAIL]** The `repo` in your `issue` must be a Repository CR name from
`repo_list` - the project's enrolled repos. Pick the one the evidence implicates
most directly. If the evidence is cross-repo, pick the service that owns the
failing component. The `comment.repo`/`comment.number` on `comment_issue` are
the tracker issue's OWN repo and number, exactly as your survey read them back
- not a repo you are choosing, a tracker you found. The operator gates the
call server-side to incident tracker issues only; a `comment_issue` aimed at
anything else is refused.

**[HARD RAIL]** False positives do not get an issue. If after investigation you
can confirm the alert condition no longer holds and there is no real underlying
problem, submit `action="false_positive"` with the evidence in `reason`. Do not
just stop - a silent finish is not a false-positive verdict, it is a lost Task.

## Evidence gathering - heuristics, not a script

Start from the alert's `generatorURL`. That URL points directly to the
firing alert rule in Grafana; reading it first tells you the exact
PromQL expression, threshold, and evaluation window - the canonical
definition of what the system thinks is wrong. Do this before querying
anything else.

After reading the rule, the natural evidence path branches by alert type:

- Saturation/resource (CPU, memory, disk, file descriptors): query the
  current value and recent trend in Prometheus. Compare against limits
  and historical baseline. Check pod restarts and OOMKilled events in
  Loki.
- Latency/error-rate (p99, 5xx rate, timeout rate): query both the
  golden-signal metric and the corresponding Loki logs for the same
  time window. Log lines often reveal the root cause that metrics
  obscure (specific error message, affected endpoint, offending
  caller).
- Availability (missing series, pod down, unhealthy endpoint): check
  Prometheus `up` metric and related service metrics. Cross-reference
  with Loki for crash logs or eviction events.
- Data-plane issues (queue depth, replication lag, ingest failures):
  query both the data-plane metric and the app-level success/failure
  counters. One tells you the symptom; the other tells you the blast
  radius.

Use the `externalURL` and related dashboards for timeline context:
when did the condition start, is it trending, is it correlated with a
recent deploy or cron job? The deploy timestamp is often in Prometheus
deployment metrics or Loki structured logs - look for it.

The memory graph (`memory_query`, `memory_entity(op="search")`) and code graph
(`code_search`, `code_context(rel="entity")`) are available for cross-referencing
platform context - e.g. which component owns a metric namespace, or
what code path emits a specific log field. Use them when the Grafana
evidence alone does not point clearly at a repo or cause.

How much evidence is enough: stop gathering when you can write a
specific, falsifiable diagnosis. "The tatara-memory ingest worker is
returning 502 from the `/delete` endpoint under concurrent load" is
specific enough. "Something is wrong with memory" is not.

## Hypothesis formation - judgment, not a rule tree

The investigation is creative work. The heuristics below sharpen your
judgment; they are not a decision tree.

Prefer the simplest explanation consistent with all evidence. A single
root cause that explains all symptoms is more likely than N independent
failures arriving simultaneously. When the evidence fits multiple
hypotheses, note which is primary and which are alternates.

Common first-order causes worth checking early because they are quick
to rule out: a recent deploy (image tag bump, config change), a
scheduled job that ran, a Ceph/storage event (EIO, stale caps, OSD
crash), a cold-start burst (new pod, fresh Project). These account for
a disproportionate share of real incidents on this platform.

High-confidence signals: a specific error message repeated in Loki
correlated with a metric spike at the same timestamp; a metric that
started degrading at a deploy boundary; a resource that is at or near
its configured limit. Low-confidence signals: a single anomalous data
point; a metric that is elevated but not crossing a threshold;
correlation without a mechanism.

When you are genuinely uncertain, say so in the issue body. "Evidence
suggests X; Y is also possible if the OSD was recovering" is honest and
useful. A confident-sounding wrong diagnosis is worse than a hedged
right one.

Anti-patterns that produce bad incident issues:

- Reporting the alert label verbatim as the diagnosis. The alert tells
  you what fired; the issue needs to explain why.
- Including raw metric dumps without interpretation. Paste the query and
  the salient value; not 200 lines of time-series output.
- Blaming infrastructure generically ("Ceph is slow", "the node was
  under load") without evidence of a specific failure mode or impact on
  the service.
- Filing an issue for a false positive because you are uncertain. If
  the firing condition has already resolved and you cannot find a root
  cause, that is `action="false_positive"`, not an issue.
- Proposing remediation in the issue body. Diagnosis and evidence only;
  the implementing agent that picks up the issue decides how to fix it.
- Filing a near-duplicate new issue when the survey already found an open
  tracker for the SAME root problem. Use `action="comment_issue"` on that
  tracker instead.
- Using `action="comment_issue"` on a tracker whose root problem your evidence
  shows is actually DIFFERENT from what you are investigating now. Comment
  only onto the SAME incident; file (optionally `issue.parent`-linked) for
  anything genuinely distinct, even under the same alert rule or workload.

## Filing or commenting

Before deciding, SURVEY: read the open backlog in the implicated repo(s) with
`scm_read(kind="issues", repo=..., state="open")`, and the open incident Tasks
with `task_list` - see `tatara-incident-sre`'s survey phase. A same-rule
duplicate of THIS alert never reaches you (admission dedup suppresses it
before a Task is even created), so anything your survey turns up is a
RELATED or CORRELATED tracker, not a mechanical repeat - decide what it
actually is:

- **SAME incident** (your fresh evidence is about the same underlying root
  problem as an open tracker you found): `action="comment_issue"`, with
  `comment={repo, number, body}` naming that tracker. No new issue is filed;
  the tracker gains your evidence as a comment.
- **Genuinely-new-but-RELATED** to an open tracker (a distinct problem that
  shares context or root cause): `action="file_issue"` with
  `issue.parent={repo, number}` set to that tracker. The operator links your
  new issue as a GitHub sub-issue and cross-references both.
- **Genuinely-new-and-UNRELATED**: `action="file_issue"` with no `parent`.

Do not go silent, and do not call an already-tracked real problem a
`false_positive` just because it is not new - that verdict is reserved for
alerts whose firing condition you can show no longer holds.

**Re-fire / persistence escalation.** If the operator escalated a
persistent or repeatedly-firing incident to you - the goal names the tracker
it re-fired against (e.g. "re-fired N times against tracker #M" or "has
persisted") - your job is specifically to RE-EXAMINE whether the root cause
is still the one that tracker names, not to assume it is. Run the evidence
fresh:
- Root cause unchanged from the tracker: `comment_issue` with your fresh
  evidence (the queries you re-ran, current values, confirmation it is the
  same failure mode).
- Root cause has CHANGED under the same alert (a different failure now
  triggers the same rule - e.g. the tracker documents a password-drift and
  your evidence now shows resource exhaustion instead): `file_issue` for the
  new problem, optionally `issue.parent`-linked to the tracker for context.
  Do not comment a different root cause onto a tracker that describes another
  one - that buries the new failure mode inside the old thread.

The `issue` object:

- `repo`: the Repository CR name most implicated by the evidence.
- `title`: one line, concrete - name the alert and the apparent cause.
  Example: "TataraMemoryIngestErrors: 502s from /delete endpoint under
  concurrent load (lightrag busy-retry gap)".
- `body` must contain (in any order):
  1. Alert summary - name, status, labels, firing condition verbatim
     from the injected alert context.
  2. Queries run - the exact PromQL or LogQL, the datasource, and the
     salient result (the value or the log line that matters).
  3. Diagnosis - your conclusion: what is failing, why, blast radius.
     Hedge where uncertain.
  4. Grafana links - the `generatorURL` (alert rule) and `externalURL`
     (dashboard/explore) from the alert context.

The `comment` object (only for `action="comment_issue"`):

- `repo`, `number`: the tracker issue you found in your survey - exactly as
  read back, not re-derived.
- `body`: your fresh evidence only - queries run and their results, the
  updated diagnosis (confirm-same or note-what-changed), and the Grafana
  links. Not a full postmortem restate; the tracker already has one.

Before you stop, write `task_note(kind="handoff", body=...)` - see `handoff`. The
clarify pod that picks up your filed issue or tracker comment reads it.
