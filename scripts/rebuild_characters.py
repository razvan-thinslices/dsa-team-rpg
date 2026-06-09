#!/usr/bin/env python3
"""Merge team.json + data/mpr_index.json + data/events.json -> data/characters.json.

Run after any change to team.json or after re-parsing MPRs.
Adds card_highlight (best recent event with note) and card_progress (trend) for the web card view.
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

ID_MAP = {
    "andreea_bejan": "andreea_bejan",
    "andrei_clim":   "andrei_clim",
    "demetriad":     "demetriad_sinzeanu",
    "ilie_lupu":     "ilie_lupu",
    "ivona":         "ivona_apostol",
    "mihai_bojescu": "mihai_bojescu",
    "razvan":        "razvan_onofrei",
}

def safe_month(x: dict) -> str:
    m = x.get("month") if isinstance(x, dict) else None
    return m or "0000-00"

def get_best_recent_event(char_events: list) -> dict | None:
    now = datetime.now(timezone.utc)
    cutoff_3m = (now - timedelta(days=90)).strftime("%Y-%m")
    cutoff_1m = (now - timedelta(days=31)).strftime("%Y-%m")

    with_note = [e for e in char_events if e.get("note")]
    recent_3m = [e for e in with_note if safe_month(e) >= cutoff_3m]

    scored_3m = [e for e in recent_3m if e.get("delta", 0) >= 0.25]
    if scored_3m:
        return max(scored_3m, key=lambda e: e.get("delta", 0))
    if recent_3m:
        return max(recent_3m, key=lambda e: e.get("delta", 0))

    recent_1m = [e for e in with_note if safe_month(e) >= cutoff_1m]
    if recent_1m:
        return max(recent_1m, key=lambda e: e.get("delta", 0))

    if with_note:
        return max(with_note, key=lambda e: e.get("delta", 0))
    return None

def main():
    team    = json.loads((ROOT / "team.json").read_text())
    mpr_idx = json.loads((DATA / "mpr_index.json").read_text())
    events  = json.loads((DATA / "events.json").read_text())
    tags    = json.loads((DATA / "tags.json").read_text())

    for ch in team["characters"]:
        short_id = next((s for s, f in ID_MAP.items() if f == ch["id"]), None)
        if not short_id:
            continue

        ch_mpr       = mpr_idx.get("characters", {}).get(short_id, [])
        ch_events_raw = [e for e in events.get("events", []) if e.get("character_id") == short_id]

        ch["mpr_history"] = sorted(ch_mpr, key=safe_month, reverse=True)

        scores = [m["score"] for m in ch["mpr_history"] if m.get("score") is not None]

        by_month: dict = {}
        for e in ch_events_raw:
            m = safe_month(e)
            by_month.setdefault(m, {"count": 0, "delta": 0.0})
            by_month[m]["count"] += 1
            by_month[m]["delta"] = round(by_month[m]["delta"] + e.get("delta", 0), 2)

        ch["events_aggregate"] = {
            "event_count": len(ch_events_raw),
            "total_delta": round(sum(e.get("delta", 0) for e in ch_events_raw), 2),
            "by_month": dict(sorted(by_month.items(), reverse=True)),
        }

        ch["mpr_stats"] = {
            "total_mprs":        len(ch["mpr_history"]),
            "scored_mprs":       len(scores),
            "latest_score":      scores[0] if scores else None,
            "latest_score_month": ch["mpr_history"][0]["month"] if ch["mpr_history"] else None,
            "avg_score":         round(sum(scores) / len(scores), 2) if scores else None,
            "first_month":       ch["mpr_history"][-1]["month"] if ch["mpr_history"] else None,
            "last_month":        ch["mpr_history"][0]["month"] if ch["mpr_history"] else None,
        }

        best = get_best_recent_event(ch_events_raw)
        if best:
            all_cats: list[str] = []
            for cat, items in best.get("tag_categories", {}).items():
                all_cats.extend(items)
            ch["card_highlight"] = {
                "text":    best.get("note", ""),
                "tags":    all_cats[:3],
                "delta":   best.get("delta", 0),
                "month":   safe_month(best),
                "section": best.get("section", ""),
            }
        else:
            ch["card_highlight"] = None

        sorted_months = sorted(by_month.keys(), reverse=True)
        recent_delta = sum(by_month[m]["delta"] for m in sorted_months[:2]) if sorted_months else 0
        prev_delta   = sum(by_month[m]["delta"] for m in sorted_months[2:4]) if len(sorted_months) >= 3 else 0
        ch["card_progress"] = {
            "recent_2m_delta": round(recent_delta, 2),
            "prev_2m_delta":   round(prev_delta, 2),
            "trend":           "up" if recent_delta > prev_delta else ("down" if recent_delta < prev_delta else "flat"),
            "recent_months":   sorted_months[:2],
        }

    (DATA / "characters.json").write_text(json.dumps(team, indent=2, ensure_ascii=False))
    print(f"[rebuild] characters.json written — {len(team['characters'])} characters")

    events_full = {
        "events": {
            short_id: [e for e in events.get("events", []) if e.get("character_id") == short_id]
            for short_id in ID_MAP
        },
        "tags": tags,
    }
    (DATA / "events_full.json").write_text(json.dumps(events_full, indent=2, ensure_ascii=False))
    print(f"[rebuild] events_full.json written")

    print("\nHighlight samples:")
    for ch in team["characters"]:
        h = ch.get("card_highlight")
        p = ch.get("card_progress")
        disc = ch.get("disc", {})
        disc_str = f"{disc.get('primary','?')}/{disc.get('secondary','?')}"
        if h:
            print(f"  {ch['name']:20s} | {disc_str} | {h['month']} | d={h['delta']:+.2f} | trend={p['trend'] if p else '?'} | {h['text'][:70]}")
        else:
            print(f"  {ch['name']:20s} | {disc_str} | no highlight")

if __name__ == "__main__":
    main()
