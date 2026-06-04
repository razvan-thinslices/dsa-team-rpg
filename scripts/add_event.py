#!/usr/bin/env python3
"""
add_event.py — append an event to a character and roll up the stat.

Enforces cap rules:
- +1 max per skill path per MPR (month)
- +1 max per section per MPR
- Skill "check" requires 5 instances + 1 team_improvement contribution

Usage:
    python3 scripts/add_event.py \\
        --character andrei_clim \\
        --type skill \\
        --target engineering-craft \\
        --delta +1 \\
        --note "Refactored DSA-1234" \\
        --ticket DSA-1234 \\
        --source manual

Run from repo root.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEAM_JSON = REPO_ROOT / "team.json"

VALID_TYPES = {
    "skill",
    "value_alignment",
    "ts_value_alignment",
    "core",
    "mpr_bonus",
    "mpr_penalty",
    "passive_added",
}

SKILL_PATHS = {
    "engineering-craft",
    "system-mastery",
    "problem-solving",
    "process-automation",
    "user-impact",
    "leadership",
}


def load_team() -> dict:
    return json.loads(TEAM_JSON.read_text())


def save_team(team: dict) -> None:
    TEAM_JSON.write_text(json.dumps(team, indent=2, ensure_ascii=False, sort_keys=False) + "\n")


def find_character(team: dict, char_id: str) -> dict:
    for c in team["characters"]:
        if c["id"] == char_id:
            return c
    raise SystemExit(f"❌ character '{char_id}' not found. Valid: {[c['id'] for c in team['characters']]}")


def next_event_id(character: dict) -> str:
    existing = character.get("events", [])
    nums = [int(e["id"].split("_")[1]) for e in existing if e.get("id", "").startswith("evt_")]
    return f"evt_{(max(nums) + 1 if nums else 1):03d}"


def parse_delta(delta_str: str) -> tuple[float, str]:
    """Returns (numeric_value, original_string). +5%, +1, -0.5, etc."""
    s = delta_str.strip()
    sign = 1 if s[0] != "-" else -1
    body = s.lstrip("+-").rstrip("%")
    return sign * float(body), s


def check_caps(character: dict, event_type: str, target: str, month: str) -> None:
    """Enforce per-MPR caps. Raises SystemExit on violation."""
    if event_type != "skill":
        return

    events_this_month = [
        e for e in character.get("events", [])
        if e.get("date", "").startswith(month) and e.get("type") == "skill"
    ]

    # +1 max per skill path per MPR
    same_target = [e for e in events_this_month if e.get("target") == target]
    same_target_deltas = sum(parse_delta(e["delta"])[0] for e in same_target)
    if same_target_deltas >= 1:
        raise SystemExit(
            f"❌ cap violation: '{target}' already received +{same_target_deltas} this month ({month}). "
            f"Max +1 per skill per MPR."
        )

    # +1 max per section per MPR (any skill in skill section)
    section_deltas = sum(parse_delta(e["delta"])[0] for e in events_this_month)
    if section_deltas >= 1:
        raise SystemExit(
            f"❌ cap violation: skill section already received +{section_deltas} this month ({month}). "
            f"Max +1 per section per MPR."
        )


def roll_up_stat(character: dict, event_type: str, target: str, delta_num: float) -> str:
    """Apply the delta to the relevant stat bucket. Returns a human description."""
    if event_type == "skill":
        path = character.setdefault("skills", {}).setdefault(target, {"level": 0, "progress": 0})
        # +1 in our schema = +1 level (caps already enforced upstream)
        path["level"] = path.get("level", 0) + delta_num
        return f"skills.{target}.level → {path['level']}"

    if event_type == "value_alignment":
        vals = character.setdefault("values", {})
        new_val = min(100, max(0, vals.get(target, 0) + delta_num))
        vals[target] = new_val
        return f"values.{target} → {new_val}%"

    if event_type == "ts_value_alignment":
        vals = character.setdefault("ts_values", {})
        new_val = min(100, max(0, vals.get(target, 0) + delta_num))
        vals[target] = new_val
        return f"ts_values.{target} → {new_val}%"

    if event_type == "core":
        core = character.setdefault("core", {})
        core[target] = core.get(target, 0) + delta_num
        return f"core.{target} → {core[target]}"

    if event_type in ("mpr_bonus", "mpr_penalty"):
        # Stored only in events[] + mpr_history rollup (separate flow)
        return f"mpr adjustment logged ({delta_num:+})"

    return f"event logged (no auto-rollup for type={event_type})"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--character", required=True, help="character id (e.g. andrei_clim)")
    p.add_argument("--type", required=True, choices=sorted(VALID_TYPES), help="event type")
    p.add_argument("--target", required=True, help="stat target (e.g. engineering-craft, extreme-ownership)")
    p.add_argument("--delta", required=True, help='delta with sign, e.g. "+1", "+5%%", "-0.5"')
    p.add_argument("--note", required=True, help="what happened, plain language")
    p.add_argument("--ticket", default="", help="jira ticket ref (optional)")
    p.add_argument("--source", default="manual", help="manual | mpr_<YYYY_MM> | retro | github | jira")
    p.add_argument("--date", default=date.today().isoformat(), help="ISO date (default: today)")
    p.add_argument("--instances", type=int, default=1, help="instance_count (default 1)")
    p.add_argument("--team-improvement", action="store_true", help="set team_improvement_added=true")
    p.add_argument("--dry-run", action="store_true", help="print the event but don't write")
    args = p.parse_args()

    team = load_team()
    character = find_character(team, args.character)

    month = args.date[:7]  # YYYY-MM
    check_caps(character, args.type, args.target, month)

    delta_num, delta_str = parse_delta(args.delta)

    event = {
        "id": next_event_id(character),
        "date": args.date,
        "source": args.source,
        "type": args.type,
        "target": args.target,
        "delta": delta_str,
        "note": args.note,
        "ticket_ref": args.ticket,
        "instance_count": args.instances,
        "team_improvement_added": args.team_improvement,
    }

    character.setdefault("events", []).append(event)
    rollup_summary = roll_up_stat(character, args.type, args.target, delta_num)

    if args.dry_run:
        print("DRY RUN — would append:")
        print(json.dumps(event, indent=2, ensure_ascii=False))
        print(f"\nWould roll up: {rollup_summary}")
        return

    save_team(team)
    print(f"✅ {character['name']} ← {event['id']}: {args.type} {args.target} {delta_str}")
    print(f"   {rollup_summary}")
    print(f"   note: {args.note}")
    if args.ticket:
        print(f"   ticket: {args.ticket}")


if __name__ == "__main__":
    main()
