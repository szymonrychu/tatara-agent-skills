---
name: tatara-mcp-chat
description: >
  Drive the 10 tatara-chat MCP tools (groupChat) to create rooms, manage
  participants, send messages, and poll or page through message history.
  Use in brainstorm, lifecycle, and incident agent kinds where chat is
  enabled; these tools are absent from implement, review, triage, refine,
  and selfImprove profiles.
profiles: ["brainstorm", "lifecycle", "incident"]
---

# tatara-mcp-chat

The 10 tools in `groupChat` hit the tatara-chat backend (Target=TargetChat).
They are available only when the agent's `TATARA_TOOL_PROFILE` is one of
`brainstorm`, `lifecycle`, or `incident`. In all other profiles the tools
are not registered and must not be called.

Tool names and argument names are exact; use them verbatim.

## Tool index

| Tool | Required args | Optional args | Purpose |
|------|--------------|---------------|---------|
| `chat_create_room` | `name` | `created_by` | Create a new room; returns the room object with its `id` |
| `chat_list_rooms` | - | `status` | List rooms; filter by `active` or `archived` |
| `chat_get_room` | `room_id` | - | Fetch one room and its participant list |
| `chat_close_room` | `room_id` | - | Archive a room; no further messages can be posted |
| `chat_add_participant` | `room_id`, `name` | `role` | Join a room; returns the participant with its `id` |
| `chat_list_participants` | `room_id` | - | List all participants of a room |
| `chat_remove_participant` | `room_id`, `participant_id` | - | Remove a participant from a room |
| `chat_send_message` | `room_id`, `participant_id`, `body` | `target`, `kind` | Post a message; `target` = direct-message recipient's participant id; `kind` defaults to `message` |
| `chat_poll_messages` | `room_id`, `participant_id` | - | Fetch messages addressed to a participant since its last poll; advances the cursor |
| `chat_get_log` | `room_id` | `after`, `limit` | Page through the room's full message log by sequence |

`role` enum: `orchestrator`, `implementer`, `reviewer`, `human`.
`kind` enum: `message`, `system`.

## When to use chat

Use chat when you need structured, turn-based coordination between agent
personas or between an agent and a human observer. Concrete triggers:

- **brainstorm**: open a room to draft proposals collaboratively across
  conceptual "roles" (researcher, critic, synthesiser) before calling
  `propose_issue`.
- **lifecycle**: open a room when the task spans multiple phases (Triage
  -> Implement -> Review) and you want a persistent shared log visible to
  all stages.
- **incident**: open a room immediately on task start so investigation
  steps, hypotheses, and findings are recorded in one thread.

Do not open a room for one-off lookups or tool calls; the overhead is only
justified when you need a persistent multi-turn record or multi-participant
coordination.

## Workflow 1: Open a room and join it

Run this once at task start when chat coordination is needed.

```
1. chat_create_room(name="<descriptive-name>", created_by="<agent-name>")
   -> Returns {"id": "<room_id>", "name": "...", ...}
   Record room_id; every subsequent call needs it.

2. chat_add_participant(room_id=<room_id>, name="<your-agent-name>", role="orchestrator")
   -> Returns {"id": "<participant_id>", ...}
   Record participant_id; you need it to send and poll.
```

Name the room after the task or issue so it is findable later (e.g.
`"brainstorm-123"`, `"incident-pg-wedge-2026-06-25"`).

Name the participant after your functional role, not a generic label (e.g.
`"researcher"`, `"critic"`, `"incident-lead"`).

## Workflow 2: Add another participant

Run when a second persona or role needs to join an existing room.

```
1. chat_add_participant(room_id=<room_id>, name="<name>", role="<role>")
   -> Returns {"id": "<participant_id>"}
   Record the new participant_id.
```

Each persona gets its own `participant_id`. A single agent simulating
multiple personas must call `chat_add_participant` once per persona and
keep the IDs separate.

## Workflow 3: Send a message

```
chat_send_message(
  room_id=<room_id>,
  participant_id=<sender_participant_id>,
  body="<message text>",
  target=<recipient_participant_id>   # omit for broadcast
)
```

Omit `target` for a broadcast visible to all participants. Set `target` to
a specific `participant_id` for a directed message. Set `kind="system"` for
automated status notifications (e.g. task phase transitions); leave it
unset (defaults to `"message"`) for conversational turns.

## Workflow 4: Poll for new messages (conversation loop)

Use `chat_poll_messages` inside a reasoning loop to check for replies.
Each call advances the participant's cursor; only messages posted since
the last poll are returned.

```
LOOP until done:
  1. <do reasoning or tool work>
  2. chat_poll_messages(room_id=<room_id>, participant_id=<my_participant_id>)
     -> Returns {"messages": [...], "room_status": "<active|archived>", "has_more": <bool>}
  3. If has_more=true: call chat_poll_messages again immediately (backlog).
  4. If room_status="archived": stop; the room is closed.
  5. Process messages, update reasoning, continue loop.
```

Do not sleep between polls in tight agent loops; call as soon as prior
reasoning is complete. Polling is cursor-based and cheap for empty batches.

## Workflow 5: Read the full log

Use `chat_get_log` to reconstruct the full history (e.g. at the start of a
resumed task or handover).

```
1. chat_get_log(room_id=<room_id>)
   -> Returns {"messages": [...], "next": <seq|null>}

2. If next is non-null, there are more pages:
   chat_get_log(room_id=<room_id>, after=<next>)
   Repeat until next=null.
```

`limit` caps the page size (default is backend-determined). Set it to a
small number (e.g. 50) when you want bounded pages.

`chat_get_log` returns ALL messages regardless of which participant you
are; it is for full replay, not for incremental polling. Use
`chat_poll_messages` for incremental delivery during an active session.

## Workflow 6: Close a room

Run when coordination is complete and no further messages will be posted.

```
chat_close_room(room_id=<room_id>)
```

After this, `chat_send_message` calls on the room will fail. Close the
room before the task exits to keep the platform state clean.

## Decision table: which tool to call

```
Goal                                          -> Tool
---------------------------------------------------------------------
Start a new coordination thread               -> chat_create_room
                                                 then chat_add_participant
Resume an existing thread (known room_id)     -> chat_get_log (full replay)
                                                 then chat_add_participant (re-join)
Check for new replies since last turn         -> chat_poll_messages
Post my turn in a conversation                -> chat_send_message (no target)
Send a direct message to one participant      -> chat_send_message (target=<id>)
List all rooms to find one by name            -> chat_list_rooms
Inspect participants of a room                -> chat_get_room (includes participants)
Remove a participant who has left             -> chat_remove_participant
Signal the room is finished                   -> chat_close_room
```

## Anti-patterns

- Do NOT use `chat_get_log` for incremental delivery during an active
  session. It replays the full log; use `chat_poll_messages` instead.
- Do NOT omit `participant_id` when sending or polling; both fields are
  required and the call will fail without them.
- Do NOT share one `participant_id` across multiple logical roles. Each
  persona needs its own `chat_add_participant` call.
- Do NOT call chat tools from implement, review, triage, refine, or
  selfImprove profiles. They are not registered and the call will fail.
- Do NOT leave rooms open indefinitely. Call `chat_close_room` when the
  task exits so room state reflects actual task lifecycle.
- Do NOT construct `participant_id` from names. Always use the `id`
  returned by `chat_add_participant` or `chat_list_participants`.
