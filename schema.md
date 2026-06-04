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

## Event log (auditable history)

Every change goes through `events[]`:
```json
{
  "id": "evt_001",
  "date": "2026-06-04",
  "source": "mpr_2026_05" | "retro" | "manual" | "github" | "jira",
  "type": "skill" | "value_alignment" | "ts_value_alignment" | "core" | "passive_added",
  "target": "engineering-craft" | "extreme-ownership" | ...,
  "delta": "+1" | "-0.5" | "+5%",
  "note": "Refactored auth flow in DSA-1234, mentored Andreea through it",
  "ticket_ref": "DSA-1234",
  "instance_count": 1,
  "team_improvement_added": false
}
```

## MPR Score (top-line)

- `score_base = 2.5`
- `score_bonuses = business + personal + team` (per Boss's rubric)
- `score_final = 1-5` (3 = meets expectations, calibrated to seniority level)
- Tracked in `mpr_history[]` per month.

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
  "mpr_history": [{ "month": "2026-04", "score": 3.5, "self": 3.0 }],
  "events": [...],
  "notes": "Truth-seeker. Takes too much ownership, risks burnout."
}
```
