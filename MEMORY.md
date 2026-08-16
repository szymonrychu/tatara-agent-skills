2026-07-05: push-CD live - agents must not self-merge; release.yml + cd-release cut tags and propagate pins; deploys land via tatara-helmfile deploy-train.
2026-07-11: task-kind redesign (see docs/superpowers/specs/2026-07-10-task-kind-redesign.md) - dropped Workflow/ultracode for Agent-tool subagent dispatch; retired triage/lifecycle/selfImprove profiles into a new clarify profile; retired tatara-health-check and tatara-deploy-harness wholesale (both described behavior no kind performs post-redesign, deploy-harness additionally self-merged PRs directly via gh, violating the platform's no-self-merge rule); shipped typed .claude/agents/{explorer,tester,builder,architect}.md; fixed a pre-existing mistag on tatara-research-followup (described the issueLifecycle Triage/Conversation turn but never carried that profile tag). Also fixed a plan-authoring inconsistency: validate_profiles.py's clarify lock (added in this same change) initially omitted tatara-research-followup even though the plan's own Phase 4 explicitly adds the clarify tag to it; added it to the lock (8 skills) as the root-cause fix rather than dropping the tag, since tatara-clarify-conversation's Branch B genuinely delegates to it. Beyond the plan's literal per-file diffs, also swept and fixed several still-stale retired-kind references (Triage/Conversation/MRCI/issueLifecycle/selfImprove prose, a dead pr_outcome recipe) in tatara-writeback-discipline, tatara-platform-contract, and tatara-documentation-workflow that the plan's narrow diffs left behind in the same files it touched.
2026-07-12: locked/fan-out guidance removed from skills - implementation-lock/fan-out state is DEFERRED (three adversarial review rounds in the operator repo found the lock-clear path unreachable and the close-directive net uncovered for cross-repo refs); sibling-reminder duty in clarify skill retained.
2026-07-12: every skill rewritten onto the 20-tool MCP surface (contract D). The 7 outcome tools are one `submit_outcome` whose schema is shaped from the agent kind; 8 SCM tools are `scm_read`/`issue_write`/`mr_write`; 19 code tools are 4; 13 memory tools are 5.
2026-07-12: `gh` and `glab` are banned IN-CLUSTER (contract L.10) - agent pods have no forge token. The violations were exactly two `["*"]` skills (finishing-a-development-branch:129, receiving-code-review:206) plus tatara-pipeline-waiting. The design doc named `writing-plans` as a third; it was WRONG - that file contains no gh. `git push` SURVIVES: it is raw git, not a forge API call.
2026-07-12: `tatara-pipeline-waiting` was rewritten, NOT reaped, despite being 90% `gh run`. It is the ONLY place in the spec documenting that turnTimeoutSeconds is an INACTIVITY window, so any single blocking call longer than it terminally fails the turn. That is why scm_read(kind=ci) is a polled point read and not a blocking watch. Transport rewritten; physics kept. A `grep -n inactivity` on it is a real regression test.
2026-07-12: `handoff` was rewritten, NOT reaped. Its four tools died with tatara-chat, but the DUTY hardened: the operator now submits a turn to an expiring pod asking for a `task_note(kind=handoff)` (contract G.7), so something must define a good one. Re-profiled to ["*"] (D-S2): a review or documentation pod that never read it writes a useless note.
2026-07-12: `validate_profiles.py:25-42` hard-locks the clarify and refine skill sets. Reaping tatara-mcp-chat and re-profiling handoff had to land in the SAME commit as the validator edit or CI goes red (contract L.7). Only those two profiles are machine-checked; the other five are checked by nothing.
2026-07-12: README claimed 29 skills; disk had 42. 13 were unlisted, including all 6 of skills/mcp/ and skills/review/. validate_profiles.py - which CI runs and which will fail your PR - was missing from the layout tree entirely.
2026-07-12: validate_skills.py gained a forge-CLI ban and a no-merge-instruction check. The forge-CLI regex matches COMMAND INVOCATIONS, not the substring `gh `: a naive one flags "enough", "through", and the five "You never use git or gh" lines that ARE the ban.
2026-07-13: `.pre-commit-config.yaml` was never created. Plan Task 9's file list names it as a CREATE target but no task body specifies its contents, and it is absent from the worktree and from git history. Task 10 (this task) does not own it either - not added to the README layout tree, flagged here instead of inventing one. `pre-commit run --all-files` cannot run in this repo until it exists; ran the two validators directly instead.
2026-07-13: dropped two resolved ROADMAP items on this pass: the "confirm the clarify->implement outcome tool name" item is moot now that all outcome tools are one `submit_outcome` and `tatara-mcp-scm-lifecycle` is renamed `tatara-mcp-scm` (no more `issue_outcome` placeholder anywhere); the "tatara-deep-research incident-tag mismatch" item is moot now that tatara-deep-research is re-profiled `["brainstorm"]` only (D-S list), so it no longer carries the `incident` tag tatara-incident-sre never invoked.
2026-07-13: `.claude-plugin/plugin.json`'s `version` field is pipeline-owned (prior commits are CI-generated "chore: pin plugin.json to X.Y.Z"), so it was left at 0.4.0 here per the platform's never-hand-edit-a-deploy-pin rule. Only its stale "20 absorbed process skills" description and its "triage" keyword (retired profile) were fixed. The release pipeline cuts the actual version from this PR's `change_significance: major`.
2026-07-13: audited the review head-moved self-heal spec's Part 2 (agent-reportable stale loops). Found `report_internal_issue` -> operator log -> Grafana alert -> incident Task -> issue chain fully intact post the 74->20 tool cut and post the task-kind redesign; only gap was skill guidance - every existing `report_internal_issue` example was single-turn framing, nothing told agents that the SAME failure recurring across turns (not just retries within one turn) is the same systematic-problem signal. Added a cross-turn recognition + worked example to `tatara-platform-contract` (not the review checklist, which Part 1 owns) rather than duplicating into every profile-specific skill, since this is a `profiles: ["*"]` shared file every kind already loads.
2026-07-19: added `.github/scripts/validate_tool_calls.py` (issue #28) - lints literal `tool_name(field="value")` tokens in SKILL.md/agent files against a JSON tool-manifest tatara-cli now publishes as a release asset (`tatara tool-manifest`, sibling change on that repo generating it from `internal/mcp/*.go`'s own schema consts, so there is one source of truth instead of a second hand-copy). Reuses validate_skills.py's negation heuristic so "Do NOT attempt `mr_write(action=\"approve\"|...)`" prohibition lines - which name values that do NOT exist, on purpose - are not flagged. First rollout: `.github/tool-manifest-version` pins "latest"; no tatara-cli release carries the asset yet, so the fetch 404s and the script SOFT-WARNS and exits 0 rather than blocking every unrelated skill PR (pre-mortem #3). It starts hard-enforcing once a tatara-cli release publishes `tool-manifest.json`.
2026-07-19: MR-ownership: added review-takeover (commit 1111735) + implement-takeover skills; both registered in EXPECTED_PROFILE_SKILLS (validate_profiles.py); merge/approve prose kept negated for validate_skills.py check. semver:minor.

2026-07-26: MEMORY_DEGRADED carve-out (tatara-operator#469/#470 + the paired tatara-cli change). The operator now spawns agents and runs turns while tatara-memory is unhealthy, and the nine memory-backed tools return a structured `MEMORY_DEGRADED: ...` result instead of a dial error - so every memory-first HARD GATE in this repo was an override waiting to happen. Canonical contract lives in ONE place, `tatara-mcp-memory` ("When memory is degraded"); the other 11 sites carry a short near-identical carve-out that cross-references it, because an agent that loaded only one skill must still get the message. Two non-obvious calls: (a) `severity="warn"`, not `error` - degraded is explicitly NOT blocked, and the mcp-platform worked example (which was already literally a memory outage at severity=error) was corrected to match, otherwise the one worked example in the repo teaches the opposite of the new contract; (b) the code-graph tools count as memory-backed - `tatara-mcp-code-graph`'s "run orientation before reading any files" gate and its matching anti-pattern were blockers nobody had flagged. Brainstorm kinds run degraded like every other kind but bias toward `action="skip"` (they cannot dedup without recall); the refine groomer's phase-1 "stop, do not groom on partial data" was scoped to mean issues-unreadable, not memory-degraded, since its backlog comes from `scm_read`. No `profiles:` frontmatter and no tool allow-list was touched.

2026-07-27: handoff scope inheritance (paired with tatara-operator's brainstorm-goal rewrite). The operator's goal used to open with "HANDOFF CONTINUATION (do this FIRST): call `list_handoffs` ... `get_handoff`" - two tools that never existed - and reading a prior handoff BEFORE deriving scope let one cycle's narrowing bind the next. Project mtg inherited a single-deck scope through four consecutive cycles, each of which re-derived it correctly and skipped. This repo owns the WRITE side of that contract, and it needed both halves: `handoff` (profiles ["*"]) already said notes are "read, not obeyed", but only about bypassing a GATE, so scope narrowing was never covered - it now has an explicit "a note may not narrow the next cycle's scope" bullet. `tatara-council-brainstorm` phase 7 gained a may/must-not list plus the one instruction the operator's new WIDEN ON REPEAT rule depends on: NAME the target you examined and say when the prior cycle examined the same one, because the reader cannot widen away from a repeat it cannot see. Deliberately no `profiles:` change and no new tool call, so validate_profiles.py's clarify/refine hard-lock and validate_tool_calls.py are both untouched. semver:minor.

2026-07-28 (reachability fix): the operator's new `exhausted` brainstorm action (replaces the deleted consecutive-skip breaker with an explicit agent-asserted pause) was correct server-side but unreachable - nothing here taught it. Fixed all FOUR sites an agent actually reads the two-shape claim from, not just the one the review flagged: `tatara-brainstorm-guardrails` rail 2 (named site) and rail 5, `tatara-council-brainstorm` phase 6 (the actual harness terminal-action step - this one matters most, since it "owns the whole turn" and phase 6 is what an agent literally executes), `tatara-mcp-outcome`'s brainstorm shape block (the cross-profile schema mirror, now back in sync with tatara-cli's schema), and `tatara-writeback-discipline`'s per-kind table + bullet (one-line correctness, boy-scouted). Left `tatara-deep-research`/`tatara-deep-architectural-research` (referenced only from guardrails' relationship table, not invoked by council-brainstorm's own procedure - likely a dead/legacy path, same shape as the documentationGoal dead-path noted in tatara-operator's MEMORY.md) and `tatara-headless-decisions`' hard-block table (semantically `skip` already covers "punt to a human/next cycle"; `exhausted` is a stronger, non-blocked decision, not obviously a fit for that table) unfixed - flagged for the maintainer, not silently dropped. `validate_tool_calls.py` now hard-fails locally on all three `action="exhausted"` mentions because it fetches tatara-cli's currently-RELEASED manifest ("latest" pin) which predates this fix; expected and self-resolving once tatara-cli's paired change ships a release - see the 2026-07-19 entry above for why this check exists and behaves this way on a first mention of a new enum value. `validate_skills.py` and `validate_profiles.py` both pass.

2026-07-28 (reachability fix follow-up, M8): the prior entry's call to leave
`tatara-deep-research`/`tatara-deep-architectural-research` unfixed as a
"likely dead/legacy path" was WRONG - a code review (finding M8) caught both
still asserting an exclusive propose-or-skip framing (frontmatter
description, body intro, and the hard-constraints bullet in each), and being
unreached by council-brainstorm's own procedure does not matter when an agent
can still invoke or read either directly. Both now teach all three actions
with the skip-vs-exhausted distinction. The same review caught a FIFTH site
the reachability-fix pass missed entirely: `tatara-code-quality-proposal`,
the one skill the operator's brainstorm goal-prompt names EXPLICITLY
("grounded per the tatara-code-quality-proposal skill") - its "How to
propose" section still only taught `propose`/`skip`, arguably the most
load-bearing gap of the five since it is the named site the prompt string
points an agent at directly. Fixed here. `tatara-headless-decisions`' hard-
block table is still deliberately left `skip`-only; that reasoning is
unchanged (it is a safe-default table, not an outcome-shape teaching site,
and `exhausted` is a stronger claim than a safe default should assert). A
repo-wide grep confirms no other exclusive two-action framing remains.
`validate_tool_calls.py` now hard-fails on 7 `action="exhausted"` mentions
(up from 3) for the same reason as the entry above - expected and
self-resolving on tatara-cli's next release. `validate_skills.py` and
`validate_profiles.py` both still pass.

2026-07-28 (approval is judged, not matched): the operator's `approvalPhrases`
wordlist is gone (paired tatara-operator change). The clarify agent now READS a
maintainer's comment, judges whether it approves, and CITES it back as
`approval_citations=[{id, quote}]` - `id` copied off the `external_id` attribute
the turn-0 bundle already renders on every `<comment>`, `quote` a verbatim
substring of the body. The operator re-verifies four STRUCTURAL facts only (the
comment is on that issue, its author is a verified non-bot maintainer, the quote
occurs verbatim in the body it holds, that comment has not already been consumed
as evidence); a failed citation is an HTTP 200 that parks the Task at
`identity-unverified`, not an error. Two non-obvious calls: (a) the
"do not re-crawl the forge" anti-pattern was KEPT and the fix was to SAY the id
is already in the bundle - licensing a re-crawl would have traded one bug for a
worse one; (b) added the repo's FIRST `decision="implement"` worked example
(`tatara-writeback-discipline`), modelled on the `reviewed_shas` idiom in
`tatara-mcp-outcome`, because a required server-re-verified field with no worked
example is the shape of a field agents omit. `approval_citations` is not an enum
value, so `validate_tool_calls.py` cannot see it in either direction - the
operator-side parity test is the only mechanical guard. No `profiles:` change and
no new skill, so `validate_profiles.py`'s clarify hard-lock is untouched.
`.claude-plugin/plugin.json` left alone (CI-owned).

2026-07-28 (approval gate, review round 2 - NO recency check): the first pass of
the entry above taught "the cited comment must be the MOST RECENT maintainer
comment" and the operator briefly enforced it. That rule DEADLOCKS an ordinary
thread and the owner removed it: given "go ahead, I approve!" followed by
"thanks - ping me when the PR is up", consent is unambiguous but the newest
maintainer comment is not itself a go-ahead, so the agent could never cite
anything, would submit `discuss` every turn, and the Task would park at
`awaiting-human` forever with no signal why. The operator now verifies four
structural facts and NOT recency, which moves the withdrawal veto entirely onto
the AGENT - it must read every maintainer comment newer than the one it cites and
submit `discuss` if any takes the go-ahead back. Because nothing downstream
backstops that any more, every site now states it explicitly and gives both
signs: benign follow-up ("ping me when the PR is up") keeps the approval,
withdrawal ("actually hold off") kills it. The `tatara-writeback-discipline`
worked example was rebuilt around exactly the deadlock thread - two comments,
cite the EARLIER one - since a single-comment example cannot teach a rule about
what comes after. Also corrected there: bundle timestamps are MINUTE precision
(`at="2026-07-12T10:02Z"`, see tatara-operator internal/prompt/testdata/full.golden:8),
not seconds. Separately, an earlier concern that `external_id` was missing from
ISSUE comments was WRONG and is recorded here so nobody re-derives it: issues and
MRs share one comments template at internal/prompt/bundle.go:259 fed by one
buildComments builder; bundle.go:222 is the `proposal_history` element, a
different block entirely, and full.golden:8 shows an issue comment carrying
`external_id`.

2026-07-28 (approval gate, review round 3 - the veto belongs in the PROCEDURE):
the round-2 fix taught the withdrawal check well in prose but left both
PROCEDURAL touchpoints in `tatara-clarify-conversation` bare - Branch B step 3's
decision list and the "walk every `<issue>`" pre-submit checklist. The veto sat
~60 lines below them, so an agent executing the numbered procedure never met the
clause at the moment it decided. Since the withdrawal check is now the ONLY
enforcement anywhere in the system, the checklist has to carry it, not just the
essay: step 3 gained "and nothing later in the thread took it back", and the
pre-submit walk is now an explicit three-item check. Also balanced
`tatara-research-followup`'s hard constraint, which gave only the withdrawal sign
and so tilted a solo reader of that file toward over-caution; it now carries the
benign sign too. Established and worth not re-deriving: bundle elision does NOT
endanger the veto - internal/prompt/bundle_test.go:669-677 asserts elision drops
the OLDEST comments and always keeps the newest, so the "comments newer than the
one you cite" window is exactly the retained region, and an elided approval fails
the agent toward `discuss`. Deferred, not dropped: later comments that RE-SCOPE
("actually do the CLI instead") or ask a question fall outside both sign lists;
no site says what to do when a later comment is genuinely ambiguous;
`tatara-mcp-outcome`'s carve-out is stated per-issue at :118 but the entry rule
is per-live-issue at :98, so a Task owning one commented and one uncommented
issue is not cleanly covered (pre-existing).

2026-07-29 (approval gate: a refusal is SILENT): three sites promised "the Task
parks at identity-unverified and a human is told what was missing"
(`tatara-clarify-conversation`, `tatara-triage-judgment`, `tatara-mcp-outcome`).
Nothing has ever delivered that. On a failed citation the operator parks at
`parked(identity-unverified)`, writes an agentNote, increments
`operator_approval_refused_total{reason}` and logs `action=approval_refused` at
WARN - all operator-side. Nothing is posted to the forge thread, so the
maintainer just sees the Task stop. `ApprovalRefusedComment`, the only thing that
ever rendered a refusal into human-readable text, had NO production caller even
before the operator branch deleted it. All three sentences now say what actually
happens, and carry the behavioural consequence rather than just the correction:
a refusal is silent, not self-correcting, so a citation the agent doubts is not a
cheap thing to try and `discuss` (which DOES reach a human) is the honest move.
Deliberately NOT written: any claim that the operator will post a refusal
comment. It will not today; whether it should is an open owner decision, and the
skills get updated if it lands. `tatara-writeback-discipline:140` needed no edit
- it states the park without claiming a notification.

2026-07-29 (approval gate: no re-gate on adopted issues): `tatara-clarify-
conversation` claimed that acquiring a NEW issue after approval "resets the Task
out of `approved` and back to `clarifying`" and that "you cannot widen your own
mandate by adopting work after the gate". Both false. The only implementer of
that reset is `applyApprovalStage` (internal/controller/approval_grammar.go:525-554),
whose sole caller is `VerifyApprovalDetailed`, which the operator's own comment
at :418 says has no production caller either (tests only). The REST clarify path
calls `stage.Enter(StageApproved)` directly (internal/restapi/outcome.go:1351) and
never reaches it; `appendTaskRef` (internal/restapi/handlers_v2.go:1171-1182)
appends an IssueRef with no re-gate. The stage edge exists at
internal/stage/stage.go:330 and nothing triggers it. This is the dangerous shape:
an agent told it CANNOT widen its own mandate stops guarding against doing so.
Rewritten to put the duty where it actually sits - adopting does not re-run the
gate, the scope you leave behind is the scope that ships, and if you are adopting
because you expect a second check there is none, so submit `discuss` first. No
invented mechanism and no claim the operator re-gates.

Also this pass: matched `tatara-mcp-outcome` and `tatara-triage-judgment` to
`tatara-clarify-conversation`'s stricter "not confident in a citation" bar (both
said "a citation you doubt", a lower bar satisfiable almost every turn, which
over-steers toward `discuss`). And softened the round-3 absolute: "nothing is
posted back to the issue thread" was slightly overstated - a Task parked at
identity-unverified DOES draw a forge notice from the reaper
(internal/controller/reaper.go:864-880), but only after ParkRetention = 7 days,
only if no un-park fires first, and its body names only the Stage and StageReason
enums, never what was missing. All three sites now say "nothing USEFUL reaches
the issue thread" with that qualifier; the behavioural conclusion is unchanged.

Standing note after two rounds of this: every "the operator will ..." sentence in
this skill set should be treated as unverified until someone reads the operator
for it. Three such claims have now been found false (the recency check, the
refusal notification, this re-gate). The audit that found this one also flagged
five more in OTHER skills - tatara-headless-decisions' bot-comment-on-park
promise, and tatara-writeback-discipline's claims about a comment on clarify
discuss, a comment on implement declined, clarify close being refused with an
unmerged MR, and brainstorm propose enforcing title dedup. All pre-existing, all
out of scope here, all the owner's call as separate work. Recorded so they are
not lost.

2026-07-29 (approval gate, final cross-repo review - I4 + I5): two more of the
class named in the entry above, both found by cross-repo audit.

I4, the mixed-Task deadlock: the no-human-comment carve-out was stated in PROSE
but every procedural checkpoint stated the strict per-Task rule, and the
carve-outs landed 37-115 lines later. A Task owning issue A (human commented) and
issue B (bot-authored, no human comment, autoApproveTataraProposals on) would be
GRANTED by the operator - A on its citation, B on the carve-out - but the
checklist tells the agent it needs an entry for B, and inventing one is
explicitly forbidden, so it submits `discuss` every turn forever. Exact same
shape as the withdrawal-veto gap: the procedure disagreed with the prose and the
procedure is what gets followed under pressure. Fixed AT the checkpoints (not by
moving the carve-out closer): the requirement is one entry per live Issue THAT
HAS A MAINTAINER COMMENT. Seven sites, three more than the review listed - a
sweep for "per live Issue / every live Issue / every live one" caught the same
strict phrasing at `tatara-triage-judgment:46` and `tatara-research-followup:81`
and `:93`, which would have recreated the deadlock through a different file. Also
added the MIRROR-IMAGE anti-pattern, which nothing covered: submitting `discuss`
because an uncommented issue has no citation.

I5, the surviving counter-claim to the not-sticky fix: `tatara-implement-workflow`
told the implement agent "The operator ran the approval gate on EVERY live Issue
this Task owns before your pod was admitted; if it is your Task, it is approved",
and its section 3 opener said the Issues "were approved together". The gate runs
at submit_outcome time only; an Issue adopted afterwards is never re-gated
(applyApprovalStage had no production caller). This was the same false guarantee
as D1, sitting in the one skill whose agent would ACT on it. Rewritten to say the
gate ran on what the Task owned when the clarify agent submitted, and a late
arrival did not pass it. Deliberate framing choice: an implement agent has no
tool to re-check consent, so this cannot be a verification duty - it is stated as
a reason to stay inside the briefed scope, with a concrete action (an owned Issue
that no note, goal or thread mentions is out of scope; say so in the outcome body
rather than shipping it). Inventing a check the agent cannot perform would have
been the same defect pointing the other way.

Confirmed clean by the reviewer, recorded so it is not re-audited:
`approval_citations` is snake_case in all 20 occurrences with zero
`approvalCitations`, the `{id, quote}` item shape is consistent everywhere, zero
recency claims survive, and the withdrawal veto is attributed to the agent at
every touchpoint including the enumerated pre-submit walk.

2026-08-07: ROADMAP's "only clarify and refine are hard-locked" item (2026-07-12) was stale - EXPECTED_PROFILE_SKILLS has had all seven keys populated for some time and validate_profiles.py's own docstring says so. Dropped the item rather than inheriting the contradiction. Verify with an ast literal_eval of EXPECTED_PROFILE_SKILLS, do not trust either doc. Consequence for #521: folding clarify's members into `implement` is NOT a net loss of CI coverage, and there was no separate "add the implement and review hard-locks" work to do - both sets already existed and simply had to be updated in the same commit that moved the skills.

2026-08-07: clarify skill set deleted (#521). tatara-triage-judgment moved to skills/implement/ and retagged ["implement","refine"]; tatara-research-followup retagged ["implement"] because its silence-over-noise discipline matters MORE under a long-lived pod, not less - a live pod that posts on every wake is the forty-comment loop. New tatara-implement-gate absorbs Branch A (the code-grounded targeted brainstorm) of the dead tatara-clarify-conversation and carries the withdrawal-veto paragraph verbatim from the operator's assignment.go so the two cannot drift. The sweep was WIDER than the plan's file list: `clarify` was also a live profile tag on tatara-mcp-code-graph, tatara-mcp-scm and tatara-pipeline-waiting, and a live factual claim ("becomes its own clarify Task") in five brainstorming skills plus tatara-backlog-groomer, tatara-incident-investigation, tatara-headless-decisions, tatara-platform-contract, tatara-writeback-discipline and tatara-evidence-and-citation. Leaving those would have left CI green and the prose wrong, since validate_profiles.py only checks profiles it has a key for - a dropped key silently stops checking the tags that still name it.

2026-08-07 (contract, #521): the MCP-facing `submit_outcome` argument names are snake_case - `approving_maintainer`, `plan_note_id`, `approval_citations`. The camelCase forms `approvingMaintainer`/`planNoteId`/`approvalCitations` are the operator WIRE field names produced by tatara-cli's outcomeArgMap, and an agent never types them. Every skill in this repo documents the snake_case form. Do not "fix" one to the other.

2026-08-07 (ordering, #521): this MR could not merge until tatara-cli published a RELEASE carrying the new action enum - validate_tool_calls.py fetches the "latest" tatara-cli release manifest and HARD-fails on an unknown enum literal, exactly as recorded for action="exhausted" on 2026-07-28. The design doc had MR3 (skills) before MR4 (cli); that order fails CI. Swapped: MR4 releases first. While the cli release is pending, validate_tool_calls.py failing on approved/discuss/rejected is EXPECTED and is the validator working - do not weaken it, do not remove the literals, do not pin an older manifest.

2026-08-08 (#46): tightened `tool not in index` from `continue` to a hard error, scoped to calls written as markdown code (fenced ``` block, 4-space indented block, or inline `backtick` span) rather than the issue's narrower "backticks only" framing (A2). Verified empirically before choosing: every one of the 315 `tool_name(field="value")`-shaped matches across all 44 skills/**/SKILL.md + template/SKILL.md + .claude/agents/*.md files lives in one of those three forms (indented blocks are real and common - tatara-mcp-scm, tatara-implement-gate - and backtick-only scoping would have left them exactly as unchecked as before), zero in bare prose. So the wider "markdown code" criterion has the same zero-false-positive property A2 was chosen for, without leaving a whole documented-call shape unchecked.

2026-08-08 (#46): scope was deliberately narrower than the issue's full decomposition. Implemented only A (unknown-tool-name hard fail, code-scoped) and D1-shaped fail-closed fetch (fetch_manifest() failure now makes main() return 1, with no vendored-manifest offline copy). Did NOT implement C2 (delete NEGATION_RE, replace with an explicit `<!-- validator: allow-invalid -->` marker) or B1 (manifest gains a `schema` field for param-name checking, cross-repo with tatara-cli) or D2 (vendor tool-manifest.json as an offline source of truth with a separate network-tolerant staleness step) - the issue comment's proposed A2+C2+D2-now/B1-follow-on stands as the fuller fix; this change covers only the two structural defects that were explicitly in scope. A+D1 do not need C2 as a co-requisite: the unknown-tool-name check never consults NEGATION_RE (that heuristic only gates the pre-existing enum-literal check), so hardening A alone does not reintroduce the pre-mortem's "first prohibition line reds the build" risk.

2026-08-08 (#46): ran the hardened validator against the real fetched tatara-cli manifest (21 tools) and all 49 real doc files (44 SKILL.md + template + 4 agent files): zero drift found, all 15 distinct tool names used in the corpus (submit_outcome, code_context, code_graph, task_note, mr_write, scm_read, issue_write, memory_entity, memory_edges, task_context, code_search, memory_query, memory_describe, code_explain, report_internal_issue) are live in the manifest, and `action="comment_issue"` is a valid submit_outcome enum value, not drift. No SKILL.md edits were needed. The two reaped names from the issue (decline_implementation, comment_on_issue) have zero hits in this repo - they were only ever live in the sibling tatara-claude-code-wrapper#136, not here.

2026-08-08 (#46): no test infra existed for `.github/scripts/*.py` before this change (no tests/, no pytest wiring in lint.yml). Added `.github/scripts/tests/` with a `conftest.py` sys.path shim (these scripts are invoked directly by lint.yml, not imported as a package, so no `__init__.py`) and wired `python3 -m pytest .github/scripts/tests/` into lint.yml ahead of the live validate_tool_calls.py run, so the regression tests actually execute in CI rather than living only on disk.

2026-08-13 (upgrade kind, Phase 2): added the 7th skill profile `upgrade` and
`skills/upgrade/tatara-upgrade-workflow`. Three corrections to the plan's own
draft, all verified before writing. (1) The draft documented
`submit_outcome(kind=upgrade, action=...)`; `kind` is NOT an agent-supplied
argument - tatara-cli's published tool manifest lists submit_outcome's enum
fields as `action`/`change_significance`/`verdict` only, and the cli's own
Task 1.2 test builds the call with no `kind` key (the wire envelope's `kind` is
added server-side from the pod profile). The skill documents
`submit_outcome(action="submitted"|"declined", ...)`, matching every other
kind's skill and snake_case per the 2026-08-07 contract entry. Writing `kind=`
would also have been the first unknown-field literal in the corpus.
(2) The plan said to delete the `engine: none` discovery block once Phase 0
decided `renovate-full`; that decision only says the `renovate` enum value is
buildable, and the design still enrols project-mtg with `engine: none`, so BOTH
branches ship, selected by the resolved policy in the assignment. (3) The
documented Renovate invocation is `RENOVATE_PLATFORM=local` against the
already-cloned `/workspace/<owner>/<repo>`, not the design's
`--platform=gitlab --autodiscover=false` flag form: agent pods have no forge
token (contract L.10, the same fact that bans gh/glab), and local mode is
exactly what the Phase 0 spike actually verified. The forge-backed form is
mentioned as needing a `read_api` token, not prescribed.

Beyond the plan's file list, three adjacent-correctness fixes the tag change
made necessary: `tatara-mcp-outcome` (`profiles: ["*"]`, so the upgrade agent
loads it) enumerated per-kind outcome shapes for six kinds and would have shown
an upgrade pod a "Your shape" section with no shape - added the upgrade block;
`tatara-implement-conflict-resolution`, newly tagged `upgrade`, pointed twice at
`tatara-implement-workflow` sections an upgrade pod does not have installed -
both now name the `tatara-upgrade-workflow` equivalent too; and README's profile
table, layout tree, skill count (44 -> 45) and inventory gained the new kind, the
same staleness recorded on 2026-07-12. `.pre-commit-config.yaml` still does not
exist here (2026-07-13 entry), so `pre-commit run --all-files` was not runnable;
ran lint.yml's four checks directly instead - validate_skills, validate_profiles,
the .github/scripts pytest suite and validate_tool_calls against the live
tatara-cli manifest - all green.

2026-08-13 (upgrade kind, review pass): applied a cross-check of every
behavioural claim in `tatara-upgrade-workflow` against live tatara-cli and
tatara-operator source. Four claims were WRONG, not merely thin, and each would
have made an autonomous pod act confidently on a mechanism that does not exist.
(1) The dedup section told the agent to make its unit visible "in your MR title
and in your outcome title". The index renders `<title>`/`<body>` from
`splitGoal(t.Spec.Goal)` (operator internal/prompt/bundle.go:459, template
:274-290), the goal is frozen at mint time, and `/outcome` only appends an
agentNote (internal/restapi/outcome.go) - so an outcome title is visible to
nobody. Rewritten to dedup off the index's `<mrs>` refs plus a
`scm_read(kind="mr")` per sibling, with the residual collision (a sibling that
has not opened its MR yet is invisible) stated as unclosable rather than papered
over, and the index's 100-Task cap + budget trim named. (2) "Two units in one
Task parks at `operator-error`" was fabricated: `mrForRepo`
(internal/controller/merge.go:152) takes the first non-closed MR and never
errors, and mrOpen is idempotent per repo/Task (handlers_v2.go:1486-1516), so
the real consequence is one branch, one MR, one `change_significance`, one tag -
which reads as PERMISSION to fold a second unit in if you reason from the stated
mechanism. Now states the real damage. (3) "Check the cluster" is not executable
from an agent pod: no kubectl, no kubeconfig, no cluster tool in any profile, and
the managed-pod NetworkPolicy egresses only to the operator, tatara-memory and
:443 - so the instruction reliably produces a fabricated "I checked". Replaced
with the in-repo sources of truth (deploy repo's k8s pin, `Chart.yaml`
`kubeVersion`, `.mise.toml`/`go.mod`) and a decline when the minimum is genuinely
unknowable. (4) The `renovate` binary is not in the wrapper image (Dockerfile
installs git/curl/build-essential/node+claude/mise+python+pre-commit and nothing
else), so the primary discovery path would have burned a turn every cycle;
documented as expected-baked, with binary-absent falling through to the
`engine: none` path rather than a decline or a per-tick internal issue. Same
class for `pluto`/`helm`, which get the `mise use -g` acquisition path.

Also: "the next MANDATORY release only" contradicted section 3's table (a
mandatory intermediate TRUNCATES a hop) and was undefined when nothing in the
range is mandatory - 1.16 with 1.17-1.20 available read as either 1.17 or 1.20.
Redefined as ceiling-then-truncate with a worked strategy/mandatory matrix.
First-party pins are now excluded from the unit definition outright (`repo_list`
is the test): section 1 previously sent the agent hunting a lagging `appVersion`
and section 5 had it editing deploy pins, i.e. exactly what CD propagates and
what the platform contract forbids hand-editing. `git add -A` is banned in a
tree Renovate ran in (`platform=local` writes into the working tree whenever the
dry run does not take). Dropped the uncited 8,106-PR statistic - no other skill
in the corpus cites an external study and the agent cannot verify it.
`tatara-implement-conflict-resolution`, newly tagged `upgrade`, still told the
resolver to be faithful to "the originating issue"; an upgrade Task owns none, so
it now branches on kind and points at the hop + release notes, including
re-deriving the hop when the default branch moved the pin under the merge.

2026-08-15 (the adopted merge request - a third shape, and the review agent meets
it FIRST): a third-party dependency bot's merge request is now adopted into an
`upgrade` Task that enters at `awaiting-review`, so the shipped review skills were
the dangerous half of this change, not the upgrade one.
`tatara-review-checklist`'s verdict-consequence table had exactly TWO rows and an
adopted merge request matches NEITHER. The old shape invites "not the platform's
own MR, therefore the human row, therefore both verdicts just park" - and an
approve reasoned that way MERGES a third party's merge request. The adopted row
goes in the MIDDLE, above the human row, so the human row is the residual rather
than the default, and the row states both consequences outright (approve ->
operator merges; request_changes -> the UPGRADE agent, onto that same branch).
Step 3 gained a `3e` for the merge request DESCRIPTION: on a dependency bump the
one-line diff is not the change, the changelog in the body is, and nothing in a
diff-shaped dimension list told the reviewer to read it.
`tatara-review-takeover` opened by calling another bot's merge request, "like
Renovate", one "the operator never merges" - false for exactly the case it named.
Corrected, plus an anti-pattern for the real trap: `mr_takeover_request` on an
adopted Task is NOT refused. Controller-owning the merge request is `mrTakeover`'s
PRECONDITION (`internal/restapi/takeover.go`, the ownership gate ahead of the
mint), which an adopted Task satisfies. Verified against the operator: when the
mirror is already classified `tatara` the call is an idempotent no-op that costs a
turn (`takeover.go:130`), and when it is not - a merge request authored by an
allowlisted `upgradeEngineLogins` account rather than `botLogin`, since
`ownershipForAuthor` (`ownership.go:33-38`) only returns `tatara` for the bot -
the mint runs for real and hands the merge request to a `takeover` Task minted at
`refined`, whose only forward edge needs an `approved` outcome that
`verifyApprovalScope` refuses for a Task owning zero Issue CRs.
`tatara-upgrade-workflow` gained 0b (which shape of Task) and 2a (the adopted
path). 2a is deliberately SMALL: the upgrade agent only ever reaches an adopted
merge request a review round already bounced, so it acts on findings rather than
deciding whether the bump is trivial. "An unchanged bump is the common case" lives
on the review side now, where the decision is. TASK_BRANCH is the bot's branch
(one repo per adopted Task, deliberately - the same branch NAME in a second repo
is a different unit), `mr_write(action="open")` is never called on that path, and
never force-push or rebase: the bot's freeze is what protects the agent's commits.
Boy-scouted `tatara-mcp-scm`, which also named Renovate as review-only and is the
file the upgrade skill's own anti-pattern points at.
No new skill and no profile change: all four touched files are already in their
profiles' exact sets, so `README.md`'s and `plugin.json`'s counts do not move.

2026-08-15 (two plan claims that did not survive verification): the plan asserted
the context bundle's last-resort body drop "leaves no `truncated=\"true\"`
marker". It does leave one - `truncBody(s, 0)` returns `("", true)`
(`internal/prompt/bundle.go:855-864`) and the template renders
`<body truncated="true">` - so both new sites say an empty body is USUALLY elided
and to re-read it with `scm_read(kind="mr", ...)`, rather than asserting a marker
that is absent. The plan also said `mr_takeover_request` on an adopted Task "would
mint a `takeover` Task into `refined`" unconditionally; on the configuration this
change actually ships (`upgradeEngineLogins: []`, Renovate authoring as the bot)
the mirror is `tatara`-owned and the call is a no-op instead. The mint is the
worse, narrower case, and the skills say so in that order.

2026-08-16 (tatara-helmfile#397): release.yml gained a SECOND cd-release bump
hop, `Bump tatara-helmfile skillsRef`, placed BEFORE the wrapper hop. Read this
before touching either. Until now this repo's only CD target was the wrapper's
`ARG TATARA_SKILLS_REF`, and that pin reaches no agent pod: the wrapper bakes
it as a runtime ENV default, and `tatara-operator internal/agent/pod.go`
appends `TATARA_SKILLS_REF` from `Project.spec.agent.skillsRef`
unconditionally, so the Project pin always wins. That Project pin was written
by nobody. Consequence measured, not inferred: a 72h Loki query over the
wrapper's boot-clone line showed every pod cloning v2.1.1 or v2.0.0 while this
repo was on v2.4.0 - v2.2.0/v2.3.0/v2.4.0 (including #56's 24 corrections to
Procedure 1, the orient sequence every agent runs) had shipped to nobody. The
new hop writes all three `values/project-*/common.yaml`, mtg included. It is
FIRST because steps are sequential and fail-fast and it is the one that reaches
production; a wrapper-hop failure must not starve it. `parent_repo ==
tatara-helmfile` takes cd-release's terminal-hop path, so it coalesces onto
`cd/deploy-train` - which also means a red pin-coverage check in that repo now
blocks the whole train, not just this commit. The pin pattern
`^(\s*skillsRef: ).*$` is duplicated as SKILLS_PIN_PATTERN in tatara-helmfile's
check_pin_coverage.py and exercised there against the real values files, so a
pin-site reformat reds that repo's lint instead of hard-erroring apply-pins.py
with count==0 mid-release here.

2026-08-16 (tatara-helmfile#397, review round 1): release.yml's `concurrency:`
blocks are per-JOB and both placements are load-bearing. `release` needs one
because it now pushes to the shared cd/deploy-train branch, where cd-release's
terminal hop answers a losing push by re-fetching and RE-APPLYING its pins - so
two overlapping releases let the older rewrite the newer's skillsRef and land
the fleet at lag 1, which check_skills_currency.py scores green. It must NOT be
at workflow level: this workflow fires on every `lint` completion including PR
runs, a run joins its group BEFORE the job `if:` that discards it is evaluated,
and GitHub cancels the previously PENDING member when a newer one queues - so a
no-op PR run could cancel a queued real release, silently, because a cancelled
run is not a failure. Job level NARROWS that (a skipped job never takes the
slot); it does not eliminate it, since the pending-cancel rule applies to
job-level groups too. GitHub has no queue-all mode. `sync-contract` then needs
its OWN group (`contract-sync`) because it was silently inheriting the old
workflow-level one: it rebuilds cd/claude-contract-sync with `checkout -B` off a
depth-1 clone and force-pushes per consumer repo, and with `continue-on-error`
plus `set -uo pipefail` (no -e) it cannot even red while clobbering a newer
fragment. Not `group: release` - that would deadlock it against its own
`needs:`.

2026-08-16 (tatara-operator#609 fan-out, the skill promised a log the fix cannot deliver) **`tatara-pipeline-waiting` told agents "read the failed check's `logTail` - nothing more to fetch" as an unconditional guarantee, and tatara-operator#609's fix made it false for the exact rows it added.** GitLab's `/pipelines/{id}/jobs` omits bridge (`trigger:`) jobs, so a failed child pipeline was invisible to `checks[]` and `scm_read(kind="ci")` answered `green` on a red MR; the fix reports the pipeline's own aggregate as `status` and enumerates bridges as drill-down rows. A bridge row carries **`JobID: ""` deliberately** - a bridge id is not a job id and `/jobs/{id}/trace` 404s on it - so the one row an agent must read is the one row that structurally cannot carry a log. Before the fix the promise was vacuously true (a failed bridge never appeared at all); after it, an agent following this skill sees a red it cannot explain, and the skill's own flap-vs-real table pushes it toward "infra flap, retrigger" on a real downstream failure. Corrected here rather than in the operator, because enumerating the child pipeline's jobs is #609's rejected option A3 (unbounded fan-out; nested bridges are legal) on an endpoint already paced at 1/20s per PR. **The generalisable rule for this repo: a skill sentence of the form "X is always present" is a CONTRACT on another repo's code, and it ages the moment that code grows a new row type.** Two other guarantees were corrected in the same pass: `status` is NOT a fold over `checks[]` (it is the forge's aggregate, so believe `status` when they appear to disagree), and `status == "none"` no longer means "no pipeline registered" but "no CI observation at all" - an MR with no pipeline but an external commit-status reporter now answers that reporter's verdict, which silently voids the 3-minute `none` bail-out for those repos.

2026-08-16 (#609 fan-out, review round 1): the `none` correction in the entry above is GITLAB-ONLY and the skill now says so. `GitHub.PRChecks` still reads `/commits/{sha}/check-runs` only (#609 pre-mortem 6, deliberately out of scope), so on GitHub `none` can still appear with a legacy commit-status reporter present and the 3-minute `none` bail-out CAN still fire - and every tatara repo an agent runs this loop against is on GitHub, so the unqualified sentence was wrong on 100% of its real readers. Generalisation of the entry above: a skill sentence that is a contract on another repo's code needs the PROVIDER scope as well as the tense, because the operator's two providers are not one implementation.
