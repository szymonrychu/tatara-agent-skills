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
