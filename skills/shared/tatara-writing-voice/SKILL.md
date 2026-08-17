---
name: tatara-writing-voice
description: >
  The prose voice contract for tatara's user-facing documentation and issue
  writing: a two-sided register bound, a path-scoped warm/clinical split, a
  banned vocabulary, six yes/no rewrite pairs, and the one humor rule no tool
  can check. Use before writing or editing any Markdown a human will read -
  docs pages, issue bodies, MR bodies, review prose.
profiles: ["documentation", "review", "brainstorm"]
---

# tatara writing voice

This is a REFERENCE skill. It is the standard every piece of human-facing tatara
prose is measured against, and it advises rather than drives: the workflow for a
given turn lives in that kind's task skill (`tatara-documentation-workflow`,
`tatara-review-checklist`). Read the tables and the pairs. The rules that matter
are in them, not in the sentences between them.

Scope: Markdown a human reads - documentation pages, issue bodies, MR bodies,
review comments, proposal bodies. Out of scope: code comments, commit messages,
log lines.

## 1. The bound

Do not try to be entertaining. Do not aim for dry either. Write warm and direct,
in second person, to a competent engineer who has not met this system before.
Contractions are welcome. The reader is not a beginner and is not your friend;
they are busy and they are capable.

Both ends of that interval are real failures. Prose that performs for the reader
wastes their time; prose that reads as a datasheet makes them do the work of
figuring out why any of it matters. Aim between them, and when you cannot tell
which side you landed on, ask whether a competent stranger finishes the
paragraph knowing something they can act on.

## 2. The register split

| Register | Applies to |
|---|---|
| Warm | `docs/index.md`, `docs/concepts/**`, `docs/getting-started/**`, `docs/explainers/**`, section index pages |
| Clinical | `docs/reference/**`, `docs/workflows/**`, `docs/architecture/**`, `docs/components/**`, `docs/operations/**` including runbooks |
| Never edited | `docs/appendix/**` - a dated archive. Corrections go in a NEW dated document, never as edits to history (`tatara-documentation/CLAUDE.md`, Local notes) |

CRD field descriptions, error messages, and runbook steps never take
personality, in any register.

The warm half of this table is the exact path scope of `.vale.ini` in
`tatara-documentation`. If you change the table, change that file in the same
MR, or the contract and its enforcement drift apart silently.

**Look up the page's register before you write, every time.** The register is a
property of the PATH, not of how the page reads today or of which task sent you
there. A whole-surface staleness pass will hand you clinical pages -
`components/`, `architecture/`, `workflows/`, `operations/` - far more often
than warm ones, because those are the pages nobody rewrites for tone. On a
clinical page you fix what is factually wrong and you fix nothing else: no
second person, no contractions, no reordering to lead with what the reader gets.
The banned list still applies (it bans marketing, not precision), and so does
the platform Unicode rule. Warming up a reference page is a regression even when
every sentence you wrote is true.

Two consequences worth stating outright, because they are the ones a pod gets
wrong:

- A page under `docs/appendix/**` is never edited at all, not even to fix a
  fact. It is an archive of what was written when it was written. The correction
  goes in a new dated document.
- A path that matches nothing in this table is CLINICAL. Warm is the enumerated
  exception, not the default.

## 3. The banned list

| Banned | Why | Write instead |
|---|---|---|
| `easily`, `simply`, `just` | Tells the reader their difficulty is their fault | Delete the word; if the step really is short, the step shows it |
| `powerful`, `seamless`, `blazing` | Marketing intensifiers that carry no information | Name the concrete capability |
| `magic`, `magical` | Says the reader will not understand it | Say what actually happens |
| exclamation marks | Manufactured enthusiasm | A period |
| figurative language | Costs a non-native reader a lookup | The literal thing |
| internet slang, cutesy framing, wackiness | Ages badly and reads as unserious | Plain words |

Then the platform-wide rule, which is not negotiable and is not register-
dependent:

**No em dashes, no smart quotes, no arrows, no decorative Unicode. Plain hyphens
and straight quotes.**

That rule covers the prose you write and the prose you edit. A page you touched
that still carries one of those characters is a page you did not finish.

## 4. Yes/no rewrite pairs

Six transformations, each drawn from tatara's own current prose so the rule is
concrete rather than abstract. The source is named so you can read the change in
context.

1. *Open with what the reader gets, not what the page contains.*
   - No: "These pages are the fast narrative path to a working mental model of
     tatara: the shape of the system and why it is built that way, for
     architects and operators sizing up whether to adopt or run it."
     (`docs/explainers/index.md`)
   - Yes: "Read these four pages and you will know what tatara does, why it is
     shaped this way, and whether it fits your organization."

2. *Replace a capability noun phrase with a verb the reader performs.*
   - No: "Enrolling Repositories - Add `Repository` CRs so the operator ingests
     and monitors your repos." (`docs/getting-started/index.md`)
   - Yes: "Enroll a repository and the operator starts ingesting it within a
     minute."

3. *Cut the marketing intensifier.*
   - No: "Tatara gives your engineering organization a permanent, autonomous
     software-development loop on top of Kubernetes." (`docs/index.md`)
   - Yes: "tatara runs an autonomous development loop on your Kubernetes
     cluster: it triages your issues, writes code, opens pull requests, and
     reviews them."

4. *Turn passive into active.*
   - No: "Every repository is ingested into a persistent LightRAG + Neo4j
     graph." (`docs/index.md`)
   - Yes: "The ingester walks each repository and pushes a code graph into
     LightRAG and Neo4j."

5. *Second person, not third-person abstraction.*
   - No: "You want your team's backlog to move faster without more headcount."
     (`docs/index.md`)
   - Yes: "If your backlog moves slower than your team can staff it, tatara
     works the items nobody has picked up."

6. *Shorten a sentence that stacks three clauses.*
   - No: "Issues move through triage, implementation, and review agents in
     sequence, each a discrete pod handing off through the operator's state
     machine." (`docs/index.md`)
   - Yes: "Each stage is its own pod. The operator hands the Task from one to
     the next."

Every "Yes" above is also a factual claim. Rewriting for voice never licenses
guessing: if the shorter sentence would assert something you have not verified,
keep the longer true one and flag the claim instead.

## 5. The humor gate

- [ ] If you are unsure whether a joke lands, keep a straight face.

No tool scores humor. Vale checks the correlated grammar and vocabulary signals
and nothing else, so this line is judged by the review pod
(`tatara-review-checklist`) and by a human, or it is not judged at all. It is
the one rule in this contract with no automated enforcement anywhere, and that
is why it is written as a checklist item you tick rather than a rule you assume
something downstream will catch.

## Anti-patterns

- Writing a `docs/reference/**`, `docs/components/**`, or `docs/operations/**`
  page in second person because the prose "read cold". That is the clinical
  register working as intended.
- Editing a page under `docs/appendix/**` at all, for any reason.
- Treating a Vale-clean page as a finished page. Vale checks vocabulary and
  grammar; it cannot tell whether the rewrite explains more than what it
  replaced, and a rewrite that explains less is a regression.
- Deciding the register from how the page currently reads instead of from its
  path.
- Changing the register table here without changing `.vale.ini` in
  `tatara-documentation` in the same MR.
- Making a sentence read better by asserting something you did not verify. A
  fluent wrong sentence is worse than the clumsy true one it replaced.
- Softening a banned word rather than deleting it ("relatively simply", "quite
  powerful"). The intensifier is the problem, not its degree.
