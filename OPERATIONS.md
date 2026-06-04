# Operations — How to use this system

> The practical guide. Schema is in `schema.md`. This file is "how do I actually do X."

---

## Daily / weekly: capture an event

You see something worth noting → it becomes an event. Don't wait for end-of-month.

### Pattern 1 — quick CLI helper (recommended)

```bash
cd ~/work/dsa-team-rpg
python3 scripts/add_event.py \
  --character andrei_clim \
  --type skill \
  --target engineering-craft \
  --delta +1 \
  --note "Refactored auth flow in DSA-1234, dropped 200 LOC, all tests green" \
  --ticket DSA-1234 \
  --source manual
```

The helper:
- Validates the character exists.
- Enforces cap rules (+1 max per skill per MPR, +1 max per section per MPR).
- Updates `events[]` AND rolls up the running total in the relevant stat bucket.
- Writes back to `team.json` with a stable diff (sorted keys, 2-space indent).

### Pattern 2 — manual JSON edit

Open `team.json`, find character by `id`, append to their `events[]`:

```json
{
  "id": "evt_042",
  "date": "2026-06-04",
  "source": "manual",
  "type": "value_alignment",
  "target": "extreme-ownership",
  "delta": "+5%",
  "note": "Stayed late to unblock prod incident on DSA-789, owned the comms",
  "ticket_ref": "DSA-789",
  "instance_count": 1,
  "team_improvement_added": false
}
```

Then update the corresponding stat field. Commit + push. Pages rebuilds.

---

## Monthly: MPR rollup

End of month, generate the draft per person from accumulated events.

```bash
python3 scripts/mpr_draft.py --month 2026-06 --character andrei_clim
```

(Script TBD — drafts the MPR text from event log, ready for Boss to review/edit/finalize.)

Until that script exists: read each character's `events[]` for the month, group by `type`/`target`, fold into MPR template.

---

## Event types — when to use which

| `type` | When | `target` examples | `delta` format |
|---|---|---|---|
| `skill` | Technical skill demonstrated (5 instances + team contribution = level up) | `engineering-craft`, `system-mastery`, `problem-solving`, `process-automation`, `user-impact`, `leadership` | `+1` (max per MPR) |
| `value_alignment` | DSA Decalogue pillar visibly embodied | `extreme-ownership`, `team-sport`, `deliver-value`, `craftsmanship`, `leave-cleaner`, `stop-starting-start-finishing`, `seek-truth-speak-up`, `learn-fast-teach-faster`, `fix-system-not-person`, `marathon-not-sprint` | `+5%` to `+10%` |
| `ts_value_alignment` | Thinslices value embodied | `team-player`, `diligence`, `openness`, `entrepreneurial-attitude`, `engineering-mindset` | `+5%` to `+10%` |
| `core` | Self-assigned growth track | `learning-plan`, `discipline`, `side-projects`, anything | `+1` |
| `mpr_bonus` | End-of-MPR additive bonus (Business / Personal / Team impact) | `business`, `personal`, `team` | `+0.5` |
| `mpr_penalty` | End-of-MPR deduction | `missed-deadline`, `quality-issue`, `escalation` | `-0.5` |
| `passive_added` | DISC overlap recomputed when leadership changes | `engineering-craft`, `leadership` | `+0.5` |

---

## Cap rules (enforced by helper, by convention if manual)

- **+1 max per skill path per MPR** (one skill levels by +1 even if 5 instances happen)
- **+1 max per category section per MPR** (only one skill in a section can level)
- **"Checking" a skill** = 5 instances + 1 team_improvement_added = unlocks +1 level
- Value/ts-value alignment is a percentage, can move by larger steps but cap at 100

---

## When NOT to log an event

- Day-to-day "did their job" stuff → that's the baseline 2.5 MPR score
- Single anecdotes without delivery evidence → wait for pattern
- Anything you'd be uncomfortable defending in a 1:1 → don't log it

The event log IS the audit trail. If you ever need a hard conversation, this is what you cite. Be precise.

---

## When something changes (leadership shuffle, new hire, role change)

1. Update `team.json` → meta or character block.
2. Re-run boost matrix: `python3 scripts/recompute_boosts.py` (TBD).
3. Commit + push.

For a new team member: clone an existing character's structure, zero out stats, set race/class based on DISC + observed behavior, add initial baseline events from their first MPR.

---

## Backup / restore

`team.json` is git-tracked. Every commit = backup. To restore:

```bash
git log --oneline team.json    # find the version
git checkout <sha> -- team.json
```

---

## Built / TBD

**Built:**
- ✅ `scripts/add_event.py` — validates + enforces caps + rolls up stats. Verified end-to-end (dry-run + real append + cap-violation rejection).

**TBD:**
- `scripts/mpr_draft.py` — generates MPR draft from event log
- `scripts/recompute_boosts.py` — re-runs DISC overlap matrix
- `scripts/sync_jira.py` — pulls ticket ownership/PR data → auto-events
- Viewer: filter by month, character compare view, leaderboard per category
- FAL_KEY wired → character art per person
