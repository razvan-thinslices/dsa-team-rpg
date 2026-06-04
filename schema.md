# Team RPG — Schema

## Universe: Volt

THG = energy domain. Team members are **Currents** flowing through the system.
The current's *form* (race) is determined by their dominant DISC traits.

## Race system (DISC-mapped, 4 base + hybrids)

| DISC | Race | Element | Vibe |
|------|------|---------|------|
| **D** | **Surge** | Lightning bolt | Direct, high-amperage, finishes fast, takes ownership |
| **I** | **Arc** | Electric arc | Connects people, bridges gaps, energizes the room |
| **S** | **Ground** | Earth wire | Steady, absorbs spikes, never panics, protects others |
| **C** | **Capacitor** | Stored charge | Precise, stores knowledge, releases on demand |

**Hybrids** = primary/secondary (e.g. `D/S` = Surge/Ground hybrid = "Storm-Anchor").

## Class (role overlay, MOBA-flavored)

| Class | What they do | Maps to |
|-------|--------------|---------|
| **Tank** | Soaks ownership weight, takes complex deliverables | Heavy D, owns many tickets |
| **Vanguard** | Drives process, enforces standards, front-line discipline | D/C, finishing |
| **Carry** | Big damage output (delivery), trusted on hard tasks | D-heavy seniors |
| **Mage** | Researches, deep system knowledge, "magic" solutions | C-heavy, system mastery |
| **Support** | Team glue, mentors, pair-programmer, unblocks others | S/I, team contribution |
| **Drill Sergeant** | Process enforcer, recipe-keeper, holds the line | D/S with process focus |

## Leadership boost system

Leadership members give passive boosts to team members who share their DISC primary or secondary.

**Leadership pool**: Răzvan (C/D), Anca (D/C), Denis (I/D), Dănuț (D/C).

**Boost mechanic**: trait match → passive `+0.5` modifier per match per leader on relevant skill paths. Surfaces as a `passive_boosts[]` array on each character card.

## Stat buckets (4 categories)

### 1. `skills` (numeric, cumulative, capped per MPR)
- Hashtag-tagged technical skills aggregated into **6 skill paths**:
  - `engineering-craft` — code quality, refactoring, testing
  - `system-mastery` — architecture, deep codebase knowledge, debugging
  - `problem-solving` — breaking down hard problems, research
  - `process-automation` — CI/CD, tooling, workflows
  - `user-impact` — UX-mindedness, feature framing
  - `leadership` — mentoring, decision-making, accountability
- Each path has `level` (1-100) + `progress` (0-100 toward next level).
- Each skill instance = `+X` event, cap `+1` per skill per MPR, cap `+1` per section per MPR.

### 2. `values` (alignment %, 0-100)
- 10 DSA Decalogue pillars (Extreme Ownership, Team Sport, Deliver Value, Craftsmanship, Leave Cleaner, Stop Starting Start Finishing, Seek Truth Speak Up, Learn Fast Teach Faster, Fix System Not Person, Marathon Not Sprint).
- Alignment is a `0-100%` per pillar, reflecting *how visibly* this person embodies it.

### 3. `ts-values` (alignment %, 0-100)
- 5 Thinslices values (Team Player, Diligence, Openness, Entrepreneurial Attitude, Engineering Mindset).

### 4. `core` (numeric, self-assigned)
- Player-chosen growth tracks (e.g. `#learning-plan`, `#discipline`, `#side-projects`).
- Open category — Boss/member can define new ones.

## MPR Entity (source of truth for history)

**Design principle**: MPRs are *rich entities*, not summary rows. Each MPR contains the parsed event stream from the Confluence markdown. Character-level `skills`, `values`, `ts_values`, `core` rollups are **derived** from the union of all `mpr_history[].events[]` (+ optional manual `events[]` for retros/GitHub/Jira).

This means: every number on a character card traces back to a specific bullet in a specific MPR on a specific Confluence page. No floating points.

### MPR object structure

```json
{
  "id": "mpr_andrei_clim_2026_04",
  "month": "2026-04",
  "page_id": "6039339009",
  "page_title": "Andrei Clim - MPR April 2026",
  "source_file": "team-mprs/andrei_clim/6039339009.md",
  "project": "THG Energy - DSA Portal",
  "sdl": "Razvan Onofrei",
  "level_at_time": "Competent L1",

  "score": {
    "base": 2.5,
    "bonuses": { "business": 0.0, "personal": 0.0, "team": 0.25 },
    "final": 2.75,
    "self_rating": 3.0
  },

  "events": [ /* see Event schema below */ ],
  "uncategorized_events": [ /* parser couldn't tag — needs human triage */ ],

  "summary": {
    "ticket_count": 7,
    "tickets_owned": ["DP-114", "DP-117"],
    "tickets_contributed": ["DP-158", "DP-196", "DP-214", "DP-160"],
    "themes": ["Ownership", "Stop Starting Start Finishing"]
  }
}
```

### Score breakdown (Thinslices additive form)

- `base = 2.5` (always — meets-expectations anchor)
- `bonuses.business` — `[Business] What did you solve?` section delta
- `bonuses.personal` — `[Personal] What did you improve on your work?` section delta
- `bonuses.team` — `[Team] What is your contribution to the team?` section delta
- `final = base + sum(bonuses)` — must equal the `Final score:` line in the source MD
- `self_rating` — member's own number (data, not authority)

### Event schema (per MPR)

```json
{
  "id": "evt_001",
  "section": "business" | "personal" | "team" | "topics" | "summary",
  "marker": "warning" | "growth" | "win" | "neutral",
  "raw_text": "Closed DP-114 with an open subtask which turned a blocker for Gather Place rollout",
  "ticket_refs": ["DP-114"],
  "tags": [
    {
      "category": "value" | "ts_value" | "skill" | "core",
      "name": "stop-starting-start-finishing",
      "delta": -0.25,
      "rationale": "open subtask on closed ticket → caused downstream blocker"
    }
  ],
  "delta_total": -0.25
}
```

**Marker semantics** (from emoji prefixes in the MD):
| Emoji | Marker | Meaning |
|---|---|---|
| ⚠️ | `warning` | Negative event — blocker caused, deadline slipped, value violated |
| 🌱 | `growth` | Missed opportunity / learning moment — "could've been more" |
| 🌟 / 💪 / ✅ | `win` | Positive delivery / ownership moment |
| (none) | `neutral` | Plain bullet — usually scope/contribution statement |

**Section semantics** map to MPR template headers:
- `business` — value delivered to client/product
- `personal` — self-improvement, learning
- `team` — contribution to teammates, mentorship, process
- `topics` — "Topics to keep track of" (forward-looking watchlist)
- `summary` — narrative paragraphs (not bulleted events)

### Mandatory tagging rule

Every event **MUST** have ≥1 tag from `{value, ts_value, skill, core}`. If the parser can't assign one with confidence, the event goes to `uncategorized_events[]` for human triage. **No silent untagged events** — that's how data rots.

Tag namespaces (closed sets except `core`):

| Category | Allowed names |
|---|---|
| `value` | The 10 Decalogue pillars (`extreme-ownership`, `team-sport`, `deliver-value`, `craftsmanship`, `leave-cleaner`, `stop-starting-start-finishing`, `seek-truth-speak-up`, `learn-fast-teach-faster`, `fix-system-not-person`, `marathon-not-sprint`) |
| `ts_value` | The 5 Thinslices values (`team-player`, `diligence`, `openness`, `entrepreneurial-attitude`, `engineering-mindset`) |
| `skill` | The 6 skill paths (`engineering-craft`, `system-mastery`, `problem-solving`, `process-automation`, `user-impact`, `leadership`) |
| `core` | **Open** — player-defined (`learning-plan`, `discipline`, `side-projects`, …) |

### Delta caps (enforced at aggregation, not source)

Boss's rule: *"each section in the category is limited to +1 max."*
At aggregation time (events → character skill paths):
- **Per MPR, per skill path: cap at `+1`** (excess truncated, surfaced in `summary.capped[]`).
- **Per MPR, per value alignment: cap at `+1`** (same).
- **Per MPR, per ts_value: cap at `+1`** (same).
- Negative deltas (`-X`) **not capped** — they accumulate.

### Derivation flow

```
Confluence MD (source)
    ↓ parser
mpr_history[].events[] (rich event stream, tagged)
    ↓ aggregator (with caps)
character.skills / values / ts_values / core (rollups)
```

The aggregator is **pure** — re-running it on the same MPR set always produces the same rollup. Manual `events[]` (retro adjustments, GitHub-derived signals) are a separate input alongside MPRs.

## Character-level events (non-MPR sources)

Reserved `events[]` array on the character card for inputs that aren't tied to a monthly MPR:
- `source: "retro" | "manual" | "github" | "jira"`
- Same `tags[]` shape as MPR events.
- Same mandatory-tag rule.
- Aggregator unions these with MPR events when computing rollups.

## Character card structure

```json
{
  "id": "andrei_clim",
  "name": "Andrei Clim",
  "nickname": "—",
  "role": "SDE",
  "level": "Competent",
  "race": { "primary": "Surge", "secondary": "Ground" },
  "disc": { "primary": "D", "secondary": "S" },
  "class": "Tank",
  "passive_boosts": [
    { "from": "Razvan", "trait": "D", "modifier": "+0.5", "applies_to": ["leadership"] }
  ],
  "skills": { "engineering-craft": {"level": 35, "progress": 60}, ... },
  "values": { "extreme-ownership": 85, ... },
  "ts_values": { "diligence": 90, ... },
  "core": { "learning-plan": 5 },
  "mpr_history": [
    {
      "id": "mpr_andrei_clim_2026_04",
      "month": "2026-04",
      "page_id": "6039339009",
      "score": { "base": 2.5, "bonuses": { "business": 0, "personal": 0, "team": 0.25 }, "final": 2.75, "self_rating": 3.0 },
      "level_at_time": "Competent L1",
      "events": [
        {
          "id": "evt_001",
          "section": "business",
          "marker": "warning",
          "raw_text": "Closed DP-114 with an open subtask which turned a blocker...",
          "ticket_refs": ["DP-114"],
          "tags": [{ "category": "value", "name": "stop-starting-start-finishing", "delta": -0.25, "rationale": "open subtask caused downstream blocker" }],
          "delta_total": -0.25
        }
      ],
      "uncategorized_events": [],
      "summary": { "tickets_owned": ["DP-114", "DP-117"], "tickets_contributed": ["DP-158", "DP-196"], "themes": ["Ownership"] }
    }
  ],
  "events": [],
  "notes": "Truth-seeker. Takes too much ownership, risks burnout."
}
```
