---
name: tatara-incident-investigation
description: Use on a tatara incident task (kind=incident, fired by a Grafana alert) to gather read-only evidence from Grafana, form a diagnosis, and file exactly one well-evidenced issue via submit_outcome(action=file_issue) - or declare a false positive with submit_outcome(action=false_positive) and stop.
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

**You have NO `issue_write` and NO `mr_write`.** You cannot comment on an issue,
you cannot open an MR, and you cannot edit or close anything. Your only voice on
the forge is the issue the OPERATOR creates from your accepted
`submit_outcome(action="file_issue")`.

## Hard rails

**[HARD RAIL]** `submit_outcome` is called EXACTLY ONCE, and it is not optional.
Two calls is a bug; zero calls ages the Task out at `stageReason=no-outcome`,
deletes the pod, and loses the work. The two shapes:

```
submit_outcome(action="file_issue",
               alert_rules=["<rule name>", ...],   # >=1, required
               reason="<why this is real, in one or two lines>",
               issue={"repo": "...", "title": "...", "body": "..."})

submit_outcome(action="false_positive",
               alert_rules=["<rule name>", ...],   # >=1, required
               reason="<the evidence that says the alert is not real>")
```

`alert_rules` is REQUIRED on BOTH and needs at least one entry: the alert rule(s)
your verdict covers, from the alert context.

**[HARD RAIL]** The issue body MUST contain all four of: the alert summary, the
queries/tools you ran with their actual results, your diagnosis, and the Grafana
links (generatorURL and externalURL from the alert context). A proposal missing
any of these will fail downstream.

**[HARD RAIL]** This is a READ-ONLY investigation. Take no remediation,
write, or corrective action on any system. Your only output is the issue
(or a false-positive verdict). No `kubectl`, no helm, no config changes, no
pushes.

**[HARD RAIL]** Platform/tooling failures (Grafana 401, MCP server
unreachable, missing credentials) are reported via `report_internal_issue`
with the concrete tool name, exact error, and what you were attempting.
That is the ONLY correct channel. Do NOT open a tracker issue asking a
human to fix the platform. Do NOT treat a blocked tool as a reason to
file your normal incident output.

**[HARD RAIL]** The `repo` in your `issue` must be a Repository CR name from
`repo_list` - the project's enrolled repos. Pick the one the evidence implicates
most directly. If the evidence is cross-repo, pick the service that owns the
failing component.

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

## Filing the issue

Before filing, read the open backlog in the implicated repo(s) with
`scm_read(kind="issues", repo=..., state="open")`, and the open incident Tasks
with `task_list` - see `tatara-incident-sre`'s survey phase.

**You cannot add evidence to an existing tracker.** incident has no
`issue_write`, so there is no comment path. If this alert is already tracked,
still submit `action="file_issue"` with your fresh evidence, and say so in the
first line of both `reason` and the issue body - name the existing
`<repo>#<number>`. The operator dedups proposals against the open backlog, and a
human reading either issue can see the connection. Do not go silent, and do not
call it a false positive: an already-tracked real problem is not a false positive.

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

Before you stop, write `task_note(kind="handoff", body=...)` - see `handoff`. The
clarify pod that picks up your filed issue reads it.
