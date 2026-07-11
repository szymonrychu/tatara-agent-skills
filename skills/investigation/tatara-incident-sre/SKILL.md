---
name: tatara-incident-sre
description: "TASK harness for the incident task kind: an eight-phase SRE workflow (branch gate, intake, runbook, ordered signal correlation, timeline, 5-Whys RCA, fix-target, file postmortem) layered above the tatara-incident-investigation REFERENCE skill. Invoke FIRST on every incident turn; consult tatara-incident-investigation for evidence-gathering judgment. Read-only: agents never remediate."
profiles: ["incident"]
---

# tatara incident SRE

The disciplined shell for an incident turn fired by a Grafana alert. It is READ-ONLY: you never take
remediation, write, or corrective action. Your only outputs are one evidence issue via
`propose_issue`, an evidence-backed false-positive note, or a `report_internal_issue` for a broken
tool. Consult `tatara-incident-investigation` for the evidence-gathering judgment layer. All Grafana
access is via the read-only `grafana` MCP server.

## Procedure (execute the numbered phases in order)

0. **Branch gate.** If the alert is `tatara_tier_quality == true`, follow the tier-revert template
   (propose reverting the regressed kind's model/effort tier via a single unmerged tatara-helmfile
   MR); skip the RCA phases. Otherwise run the full flow below.
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
6. **Fix-target identification.** Name the repo slug + file/config key precisely enough to seed an
   implement task. If you fanned out `explorer` subagents in phase 3/4, their file:line reports are
   exactly what phase 6 needs to name the fix target precisely.
7. **File exactly one output.** `propose_issue(repo, body)` with a postmortem body: exec summary,
   verbatim alert context, timeline, signal evidence (with snippets), contributing factors, root
   cause, immediate mitigation (as a human instruction), fix target, action items. OR an
   evidence-backed false-positive note with no issue. A BLOCKED Grafana tool is NOT a false positive
   -> `report_internal_issue`.

## Anti-patterns

- Any remediation / write / `kubectl` / corrective action - this turn is read-only.
- An RCA before the phase-3 signal correlation, or without a Loki snippet on the non-exempt path.
- Filing a false-positive note when a Grafana tool was actually blocked (that is a platform bug ->
  `report_internal_issue`).
- A generic diagnosis with no PromQL/LogQL result snippet, annotation, or `file:line` behind it.
- More than one terminal action per turn.
