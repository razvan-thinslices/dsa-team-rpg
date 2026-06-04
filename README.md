# DSA Team RPG

> Volt Universe — RPG-flavored character system for the DSA Portal team.
> Derived from MPRs, DISC profiles, and observed delivery behavior.

**Live viewer:** https://razvan-thinslices.github.io/dsa-team-rpg/

---

## What this is

A structured representation of the DSA Portal team as RPG characters. Each character has:

- **Race** (DISC-driven): Surge (D), Arc (I), Ground (S), Capacitor (C) — with primary/secondary hybrid.
- **Class** (observed role behavior): Architect, Tank, Vanguard, Carry, Loremaster, Inquisitor, etc.
- **Stats** in 4 buckets:
  - `skills` — technical paths (tagged like `#support`, `#domain-knowledge`), numeric/cumulative
  - `values` — DSA Decalogue 10 pillars, alignment %
  - `ts-values` — 5 Thinslices values, alignment %
  - `core` — self-assigned (e.g. `#learning-plan`, `#discipline`), numeric
- **MPR history** — score trajectory, base 2.5 + Business/Personal/Team bonuses → 1-5
- **Event log** — every `+X / -X` adjustment with note, ticket ref, date, source
- **Passive boosts** — DISC trait overlaps with leadership grant +0.5 stat modifiers

---

## Why

MPR capture is supposed to be continuous, not end-of-month panic. This is the
substrate: every observation becomes an event in `team.json`, totals roll up,
the viewer makes it explorable. Eventually feeds the monthly MPR draft.

---

## Files

| File | Purpose |
|---|---|
| `team.json` | Single source of truth — meta, races, skill paths, decalogue, all character data |
| `schema.md` | Schema reference: race/class system, DISC mapping, scoring rules, hybrid notation |
| `index.html` | Static viewer — character cards + radar charts (Chart.js via CDN, no build) |
| `README.md` | This file |

---

## Adding an event (the operational loop)

1. Open `team.json`, find the character by `id`.
2. Append to `events[]`:
   ```json
   {
     "date": "2026-06-04",
     "type": "skill_progress | value_alignment | ts_value | core | mpr_bonus | mpr_penalty",
     "target": "skills.domain-knowledge | values.extreme-ownership | ts_values.engineering-mindset | core.discipline",
     "delta": 1,
     "note": "Owned the DSA-642 migration end-to-end, no escalations.",
     "ticket_ref": "DSA-642",
     "source": "razvan_observation | mpr_<month> | retro_<sprint>"
   }
   ```
3. Update the corresponding stat in `skills` / `values` / `ts_values` / `core` (running total).
4. Commit + push. GitHub Pages auto-rebuilds the viewer.

**Caps** (enforced by convention):
- +1 max per skill per MPR
- +1 max per section per MPR
- "Checking" a skill = 5 instances + 1 team improvement contribution
- Skill events need `instance_count` + `team_improvement_added: bool`

---

## Roster (11 characters)

**Leadership (4):** Răzvan (The Boss / Architect), Dănuț (CTO), Anca (PM), Jordan (PO)
**Team (6):** Andrei Clim, Ilie Lupu (Pipeline), Mihai Bojescu, Demetriad (Gandacus), Ivona, Andreea Bejan (Sparkles)
**NPC (1):** Benjammin Frankly (Familiar / Loremaster — Boss's AI extension)

> Robert Ieremciuc is NOT on this team. Robert Pascu is.

---

## Stack

- Pure HTML + Chart.js 4.4.1 (CDN) — no build step
- GitHub Pages serves direct from `main` branch root
- `team.json` is hand-edited (for now) — fetch-driven viewer

## Next

- [ ] Wire `FAL_KEY` → generate character art for all 11
- [ ] Auto-MPR draft generator (script reads events, drafts monthly MPR per person)
- [ ] Sprint retro hook: post-retro, append events from delivery data
- [ ] Optional: migrate `team.json` → SQLite for richer queries
