---
name: tatara-incident-investigation
description: Use on a tatara incident task (kind=incident, fired by a Grafana alert) to gather read-only evidence from Grafana, form a diagnosis, and file exactly one well-evidenced issue via propose_issue - or declare a false positive and stop.
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
externalURL) as your turn-0 goal. Your job: investigate live via the
`grafana` MCP server (read-only), form a diagnosis, and hand one
evidence-backed issue to the team. Nothing else.

Tool surface available in the incident profile:
- Grafana MCP server: query Prometheus/Loki, read alert rules and
  dashboards, follow generatorURL - all read-only.
- tatara operator tools: `propose_issue`, `comment_on_issue`,
  `change_summary`, `decline_implementation`, `submit_handover`,
  `task_list`, `task_update`, `subtask_list`, `subtask_create`,
  `subtask_update`.
- Always-on: `report_internal_issue`, `project_get`, `repo_list`,
  `task_get`.
- Memory and code-graph tools (groupMemory, groupCodeGraph) for
  cross-referencing platform context.
- Chat tools (groupChat) available if coordination is needed.

## Hard rails

**[HARD RAIL]** `propose_issue` is called EXACTLY ONCE, or not at all
(false positive). Two calls is a bug. The issue body MUST contain all
four of: the alert summary, the queries/tools you ran with their actual
results, your diagnosis, and the Grafana links (generatorURL and
externalURL from the alert context). A proposal missing any of these
will fail triage.

**[HARD RAIL]** This is a READ-ONLY investigation. Take no remediation,
write, or corrective action on any system. Your only output is the issue
(or a false-positive note). No `kubectl`, no helm, no config changes.

**[HARD RAIL]** Platform/tooling failures (Grafana 401, MCP server
unreachable, missing credentials) are reported via `report_internal_issue`
with the concrete tool name, exact error, and what you were attempting.
That is the ONLY correct channel. Do NOT open a tracker issue asking a
human to fix the platform. Do NOT treat a blocked tool as a reason to
file your normal incident output.

**[HARD RAIL]** The `repo` argument to `propose_issue` must be one of
the repos listed in your task goal (the project's enrolled repositories).
Pick the one the evidence implicates most directly. If evidence is
cross-repo, pick the service that owns the failing component.

**[HARD RAIL]** False positives do not get an issue. If after
investigation you can confirm the alert condition no longer holds and
there is no real underlying problem, finish with a one-line note and
stop.

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

The memory graph (`query`, `search_entities`) and code graph
(`code_search`, `code_entity`) are available for cross-referencing
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
- Opening an issue for a false positive because you are uncertain. If
  the firing condition has already resolved and you cannot find a root
  cause, that is a false positive note, not an issue. The triage flow
  is for real problems.
- Proposing remediation in the issue body. Diagnosis and evidence only;
  the implementing agent that picks up the issue decides how to fix it.

## Filing the issue

`propose_issue(repo, title, body, kind)`:
- `repo`: the project repo most implicated by evidence.
- `title`: one line, concrete - name the alert and the apparent cause.
  Example: "TataraMemoryIngestErrors: 502s from /delete endpoint under
  concurrent load (lightrag busy-retry gap)".
- `kind`: almost always "bug" for an incident. "improvement" only if
  investigation reveals a design gap rather than a defect.
- `body` must contain (in any order):
  1. Alert summary - name, status, labels, firing condition verbatim
     from the injected alert context.
  2. Queries run - the exact PromQL or LogQL, the datasource, and the
     salient result (the value or the log line that matters).
  3. Diagnosis - your conclusion: what is failing, why, blast radius.
     Hedge where uncertain.
  4. Grafana links - the `generatorURL` (alert rule) and `externalURL`
     (dashboard/explore) from the alert context.

Do not embed `<!-- tatara-authored -->` in an incident issue body. That
marker is for brainstorm/discovery issues that need human approval
before the bot pursues them. Incident issues route through triage
directly.

Do not set a `systemicId` unless the alert is clearly one instance of a
cross-repo pattern you have confirmed with evidence. If in doubt, leave
it unset.
