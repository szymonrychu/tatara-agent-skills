---
name: tatara-incident-sre
description: "TASK harness for the incident task kind: an eight-phase SRE workflow (branch gate, intake, runbook, ordered signal correlation, timeline, 5-Whys RCA, fix-target, survey plus file-or-comment outcome) layered above the tatara-incident-investigation REFERENCE skill. Invoke FIRST on every incident turn; consult tatara-incident-investigation for evidence-gathering judgment. Read-only: agents never remediate."
profiles: ["incident"]
---

# tatara incident SRE

The disciplined shell for an incident turn fired by a Grafana alert. It is READ-ONLY: you never take
remediation, write, or corrective action. Your only outputs are one evidence issue via
`submit_outcome(action="file_issue")`, fresh evidence appended to an existing tracker for the
SAME incident via `submit_outcome(action="comment_issue")`, an evidence-backed
`submit_outcome(action="false_positive")`, or a `report_internal_issue` for a broken
tool. Consult `tatara-incident-investigation` for the evidence-gathering judgment layer. All Grafana
access is via the read-only `grafana` MCP server.

You have NO `issue_write` and NO `mr_write` TOOL. Every issue you want to exist, and every
comment you want posted, the OPERATOR creates or posts from your accepted `submit_outcome`.
`comment_issue` is gated server-side to incident tracker issues only - you can never use it to
comment on an arbitrary human issue.

## Procedure (execute the numbered phases in order)

0. **Branch gate.** If the alert is `tatara_tier_quality == true`, follow the tier-revert template:
   file ONE issue against `tatara-helmfile` proposing the revert of the regressed kind's
   model/effort tier, with the regression evidence; skip the RCA phases. You cannot open the MR
   yourself - incident has no `mr_write` - so the issue is the deliverable, and a human or an
   implement Task cuts the change. Otherwise run the full flow below.
1. **Alert intake + severity classification (HARD GATE).** Classify P1/P2/P3 and commit the
   classification to your scratchpad BEFORE running any query.
2. **Runbook check.** Follow the alert `generatorURL` to the Grafana rule and its `runbookURL`.
   Surface any immediate mitigation as a HUMAN instruction in the issue - you are read-only.

Grafana queries are not repo-scoped - run them directly on the main thread,
in order, as below. If the RCA implicates or must rule out more than one
repo (e.g. a shared library used by two services, or you need to check
recent commits/config across several implicated repos), dispatch one
`explorer` subagent per implicated repo (via the `Agent` tool, `model:
haiku`, `effort: low`) to gather that repo's code-level evidence (recent
commits, the failing code path, config) in parallel, keeping your own RCA
thread lean. Do this once you know WHICH repos are implicated (after phase 3
or 4), not speculatively before you have Grafana evidence pointing anywhere.

3. **Ordered signal correlation (step-gate).** In order: PromQL current + baseline -> related
   dashboard panels -> LogQL within the incident window -> deploy/config annotations. Attach a
   result snippet for each. Do NOT form an RCA without Loki evidence unless this is the
   `InfraIncidentExempt` Prometheus-only path.
4. **Timeline construction.** Record T_onset, T_alert, T_deploy, T_config.
5. **Structured 5-Whys RCA.** Each Why is evidence-cited; label each factor contributing vs
   root-cause; stop at the first code/config change that breaks the failure class.
6. **Fix-target identification.** Name the repo (a Repository CR name from `repo_list`) plus the
   file or config key, precisely enough to seed an implement Task. If you fanned out `explorer`
   subagents in phase 3/4, their `file:line` reports are exactly what phase 6 needs.
7. **Survey for a SAME or RELATED tracker.** A same-rule duplicate of THIS alert never reaches
   you - the operator suppresses it at admission before a Task is even created - so your survey is
   never a mechanical repeat-check; it finds SAME-incident or RELATED/CORRELATED trackers. Before
   deciding your outcome: list open incident Tasks (`task_list`) and the open backlog in the
   implicated repo(s) with `scm_read(kind="issues", repo=..., state="open")`. If the operator
   escalated a persistent or repeatedly-firing incident to you (the goal names the tracker it
   re-fired against, e.g. "re-fired N times against tracker #M" or "has persisted"), treat that
   tracker as the starting point of the survey and specifically RE-EXAMINE whether the root cause
   you find now is still the one it names, or has changed under the same alert. Going silent is not
   an option: a Task with no outcome ages out at `no-outcome` and the work is lost.
8. **File exactly one outcome.**

   - **SAME incident** as an open tracker you found (your fresh evidence is about the same
     underlying root problem, not merely the same alert rule) - append it as a comment instead of a
     near-duplicate issue:

     ```
     submit_outcome(action="comment_issue",
                    alert_rules=["<rule>", ...],       # >=1, required
                    reason="<why this is the same incident as <repo>#<number>>",
                    comment={"repo": ..., "number": ..., "body": ...})
     ```

     `comment.body` is fresh evidence only - queries re-run, current results, confirmation the
     failure mode is unchanged (or, on a re-fire escalation, that you checked and it is still the
     same root cause). No new issue is filed. This is the re-fire-escalation default outcome when
     the root cause has not changed.

   - **Genuinely-new-but-RELATED** to an open tracker you found (a distinct problem, or the SAME
     alert now firing for a DIFFERENT root cause - e.g. the tracker documents a password-drift and
     your evidence now shows resource exhaustion instead):

     ```
     submit_outcome(action="file_issue",
                    alert_rules=["<rule>", ...],       # >=1, required
                    reason="<why it is real, and why it relates to <repo>#<number>>",
                    issue={"repo": ..., "title": ..., "body": ...,
                           "parent": {"repo": ..., "number": ...}})
     ```

     The operator links your new issue as a GitHub sub-issue under `issue.parent` and
     cross-references both. Name the existing `<repo>#<number>` in the first line of your `reason`.
     Do NOT comment a changed root cause onto the old tracker - that buries the new failure mode
     inside a thread about a different one.

   - **Genuinely-new-and-UNRELATED**: the same `file_issue` call, with no `parent` key.

   In both `file_issue` cases the body is a postmortem: exec summary, verbatim alert context,
   timeline, signal evidence (with snippets), contributing factors, root cause, immediate
   mitigation (as a human instruction), fix target, action items.

   OR, when the alert is not real:

   ```
   submit_outcome(action="false_positive",
                  alert_rules=["<rule>", ...],
                  reason="<the evidence that says so>")
   ```

   A BLOCKED Grafana tool is NOT a false positive -> `report_internal_issue`.

   Then `task_note(kind="handoff", body=...)` and stop. See `handoff`.

## Anti-patterns

- Any remediation / write / `kubectl` / corrective action - this turn is read-only.
- An RCA before the phase-3 signal correlation, or without a Loki snippet on the non-exempt path.
- Submitting `false_positive` when a Grafana tool was actually blocked (that is a platform bug ->
  `report_internal_issue`), or when the problem is real but already tracked (that is `comment_issue`
  on a SAME-incident tracker, or `file_issue` with `issue.parent` on a RELATED one - never a silent
  false-positive verdict).
- A generic diagnosis with no PromQL/LogQL result snippet, annotation, or `file:line` behind it.
- More than one `submit_outcome` per turn - or none at all.
- Trying to open an MR, or trying to comment on / edit an issue through anything other than
  `submit_outcome(action="comment_issue")` - no general-purpose `issue_write`/`mr_write` exists in
  this profile.
- Filing a near-duplicate new issue when `comment_issue` on the tracker you found in the survey is
  the right move - burns a new issue number and splits the evidence trail.
- Using `comment_issue` on a tracker whose root cause your evidence shows is actually a DIFFERENT
  problem from what you are investigating now (most likely on a re-fire escalation) - file instead,
  optionally `issue.parent`-linked for context.
