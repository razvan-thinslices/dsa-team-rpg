#!/usr/bin/env python3
"""Parse cached MPR markdown files into a flat event stream + character aggregates.

Inputs:
  - $MPR_CACHE/<person>/<page_id>.md  (78 files, 2 formats)
  - data/tags.json                     (aliases + categories + section_defaults + ignore_tags)
  - data/roster.json                   (canon levels + sketches)

Outputs:
  - data/events.json   (flat event log + orphans)
  - data/mpr_index.json (per-MPR metadata)

Format A: tracker style. Pattern: 'Final score: 2.5 + X = Y', sections [Business]/[Personal]/[Team],
          inline events ending in '+0.25 #tag' or '-0.5 #tag'.
Format B: long rubric (Andreea Bejan). Per-dimension 1-5 team_rating + sdl_rating tables.

Key parser rules:
  - Score-summary lines ("Final score:", "Self rating:", "Self score:") never produce events.
  - Ticket refs (PROJ-123, CVE-YYYY-N) and URLs are stripped before delta regex.
  - Tags matching ignore_tags prefixes (issuecomment-, diff-, etc.) are filtered out.
  - Paragraph with delta + section but no usable hashtag → categorized by section_defaults
    (NOT an orphan — section IS the category signal in this MPR culture).
  - Truly orphaned = delta with no section context AND no tag.
"""
from __future__ import annotations
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

MPR_CACHE = Path("/home/benjammin/.hermes/profiles/benjammin-thinslices/skills/work/thinslices-company-canon/references/team-mprs")
ROOT = Path("/home/benjammin/work/dsa-team-rpg")
DATA = ROOT / "data"

# --- Tag/category resolution ---

def load_tags():
    return json.loads((DATA / "tags.json").read_text())

def resolve_tag(raw: str, tagmap: dict) -> tuple[str, str] | None:
    """Return (category, slug) or None."""
    if not raw:
        return None
    s = raw.strip().lstrip("#").lower()
    s = re.sub(r"[^a-z0-9-]", "-", s).strip("-")
    if not s:
        return None
    # ignore URL-fragment style tags
    for prefix in tagmap.get("ignore_tags", []):
        if s.startswith(prefix.rstrip("-")):
            return None
    aliases = tagmap.get("aliases", {})
    cats = tagmap.get("categories", {})
    if s in aliases:
        cat, slug = aliases[s].split(":", 1)
        return (cat, slug)
    for cat, slugs in cats.items():
        if s in slugs:
            return (cat, s)
    # fuzzy: contains
    for cat, slugs in cats.items():
        for slug in slugs:
            if slug in s or s in slug:
                return (cat, slug)
    return None

# --- Month parsing (RO + EN) ---

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4, "mai": 5, "iunie": 6,
    "iulie": 7, "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
}

def parse_month_year(title: str) -> str | None:
    t = title.lower()
    m = re.search(r"(january|february|march|april|may|june|july|august|september|october|november|december|"
                  r"ianuarie|februarie|martie|aprilie|mai|iunie|iulie|septembrie|octombrie|noiembrie|decembrie)\s+(\d{4})", t)
    if m:
        return f"{m.group(2)}-{MONTHS[m.group(1)]:02d}"
    return None

# --- Score parsing ---

SCORE_RE = re.compile(r"(?:final|initial)\s+score\s*:\s*([\d.]+)\s*\+\s*([\d.x]+)\s*=\s*([\d.xy]+)", re.IGNORECASE)
SELF_RE = re.compile(r"self\s+(?:rating|score)\s*:?\s*([\d.]+)", re.IGNORECASE)
LEVEL_RE = re.compile(r"level\s*:\s*([^\n]+)", re.IGNORECASE)

def parse_score_block(text: str) -> dict:
    out = {"score": None, "self_score": None, "level": None}
    m = SCORE_RE.search(text)
    if m:
        try:
            base = float(m.group(1))
            bonus_s = m.group(2)
            final_s = m.group(3)
            if "x" not in bonus_s.lower():
                bonus = float(bonus_s)
            else:
                bonus = None
            if "y" not in final_s.lower() and "x" not in final_s.lower():
                out["score"] = float(final_s)
            elif bonus is not None:
                out["score"] = base + bonus
        except ValueError:
            pass
    m = SELF_RE.search(text)
    if m:
        try:
            out["self_score"] = float(m.group(1))
        except ValueError:
            pass
    m = LEVEL_RE.search(text)
    if m:
        out["level"] = m.group(1).strip()
    return out

# --- Event extraction (Format A) ---

SECTION_RE = re.compile(r"^\s*\[(Business|Personal|Team|Manager|TS-values|TS Values|Side[- ]quests?)\]", re.IGNORECASE | re.MULTILINE)

# Pre-strip patterns: remove BEFORE running DELTA_RE
URL_RE = re.compile(r"https?://\S+")
TICKET_RE = re.compile(r"\b([A-Z]{2,6})-(\d{1,5})\b")
CVE_RE = re.compile(r"\bCVE-\d{4}-\d+\b", re.IGNORECASE)
# Markdown link [text](url) — strip the parenthesized URL part too
MD_LINK_URL_RE = re.compile(r"\]\([^)]+\)")

# Delta: must be preceded by start of string, whitespace, opening paren/bracket, or pipe
# AND followed by space/end/tag/punctuation. NOT a digit (so we don't catch tail of a number).
# CRITICAL: NO internal space between sign and digits — real MPR deltas are "+0.25"/"-0.25" never "+ 0.25".
# Allowing "\s*" between sign and digit caused false positives like "- 1 person", "- 5 extra people".
# Match: " +0.25", "+0.5 #tag", "(+0.25)", "| +0.25 |"
DELTA_RE = re.compile(r"(?:^|(?<=[\s\(\[\|]))([+\-]\d+(?:\.\d+)?)(?=[\s\)\]#a-zA-Z(,;:|.\-]|$)")

# Tag: standard hashtag (no slashes, dots, equals — those are URL fragments handled by ignore_tags)
TAG_RE = re.compile(r"#([a-zA-Z][a-zA-Z0-9_\-]*)")

# Score-summary lines — these are NEVER events
# Accepts both "Final Score: X" and "Self score = X" (Mihai uses = form)
SCORE_LINE_PATTERNS = [
    re.compile(r"final\s+score\s*[:=]", re.IGNORECASE),
    re.compile(r"initial\s+score\s*[:=]", re.IGNORECASE),
    re.compile(r"self\s+(?:rating|score)\s*[:=]", re.IGNORECASE),
    re.compile(r"^\s*score\s*[:=]", re.IGNORECASE | re.MULTILINE),
    re.compile(r"sdl\s+(?:rating|score)\s*[:=]", re.IGNORECASE),
    re.compile(r"manager\s+(?:rating|score)\s*[:=]", re.IGNORECASE),
]

# Section-rollup lines — skip these (they're the section header/prompt)
ROLLUP_RE = re.compile(
    r"what\s+did\s+you\s+(solve|improve|contribute|do)|"
    r"what\s+is\s+your\s+contribution|"
    r"what\s+have\s+you\s+done",
    re.IGNORECASE,
)

def is_score_summary(para: str) -> bool:
    """True if this paragraph is a score summary line (skip entirely)."""
    return any(p.search(para) for p in SCORE_LINE_PATTERNS)

def strip_noise(para: str) -> str:
    """Remove URLs, markdown link URL parts, ticket refs, CVE refs BEFORE delta extraction.

    Returns a sanitized copy of the paragraph used ONLY for delta scanning.
    Tags and notes are extracted from the original.
    """
    s = URL_RE.sub(" ", para)
    s = MD_LINK_URL_RE.sub("] ", s)  # keep "[text]" visible, drop "(url)"
    s = CVE_RE.sub(" ", s)
    s = TICKET_RE.sub(" ", s)
    return s

def extract_events_format_a(text: str, character_id: str, page_id: str, month: str | None, tagmap: dict) -> tuple[list, list]:
    """Return (events, orphans).
    Strategy: split into paragraphs; track current section; for each paragraph with delta emit event.
    Categorization priority: explicit tag → section default → orphan.
    """
    events = []
    orphans = []
    current_section = "Unknown"
    section_defaults = tagmap.get("section_defaults", {})
    paragraphs = re.split(r"\n\s*\n", text)
    seq = 0

    for para in paragraphs:
        # Update section if header in paragraph
        sec_match = SECTION_RE.search(para)
        if sec_match:
            current_section = sec_match.group(1).title()

        # Skip score-summary paragraphs ENTIRELY (no events come from them)
        if is_score_summary(para):
            continue

        # Skip pure section-rollup prompts (no event, just the question prompt)
        if ROLLUP_RE.search(para) and not TAG_RE.search(para):
            # could still contain inline deltas, but those are aggregates — skip
            continue

        # Pre-strip noise (URLs, tickets, CVEs) for delta scanning
        scan_text = strip_noise(para)
        deltas = DELTA_RE.findall(scan_text)
        if not deltas:
            continue

        # Tags + tickets from ORIGINAL paragraph (not stripped)
        raw_tags = TAG_RE.findall(para)
        # Filter out ignore-pattern tags before resolving
        ignore_prefixes = [p.rstrip("-") for p in tagmap.get("ignore_tags", [])]
        tags = [t for t in raw_tags if not any(t.lower().startswith(p) for p in ignore_prefixes)]
        tickets = [f"{p}-{n}" for p, n in TICKET_RE.findall(para)]

        # One event per delta — pair with shared tag list (best-effort)
        for d in deltas:
            try:
                delta_val = float(d.replace(" ", ""))
            except ValueError:
                continue
            # Sanity bound: real MPR deltas are ±0.25/±0.5/±1.0; reject |delta|>5
            if abs(delta_val) > 5 or delta_val == 0:
                continue
            seq += 1
            ev_id = f"{character_id}__{page_id}__{seq:03d}"
            tag_cats = categorize_tags(tags, tagmap)

            # Categorization fallback: if no tag resolved, use section default
            has_resolved = any(tag_cats[k] for k in ("skills", "values", "ts-values", "core"))
            categorized_by = "explicit_tag"
            if not has_resolved:
                default = section_defaults.get(current_section)
                if default:
                    cat, slug = default.split(":", 1)
                    tag_cats[cat].append(slug)
                    categorized_by = f"section_default:{current_section}"
                else:
                    categorized_by = "orphan"

            ev = {
                "id": ev_id,
                "character_id": character_id,
                "mpr_page_id": page_id,
                "month": month,
                "section": current_section,
                "delta": delta_val,
                "tags": [f"#{t}" for t in tags],
                "tag_categories": tag_cats,
                "ticket_refs": tickets,
                "categorized_by": categorized_by,
                "note": clean_note(para),
                "source_excerpt": para.strip()[:500],
            }
            if categorized_by == "orphan":
                ev["orphan_reason"] = "no_tag_no_section"
                orphans.append(ev)
            else:
                events.append(ev)
    return events, orphans

def clean_note(para: str) -> str:
    s = URL_RE.sub("", para)
    s = MD_LINK_URL_RE.sub("]", s)
    s = re.sub(r"#[a-zA-Z][a-zA-Z0-9_\-]*", "", s)
    s = re.sub(r"[+\-]\s*\d+(?:\.\d+)?", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.strip("→-•* ")
    return s[:280]

def categorize_tags(tags: list[str], tagmap: dict) -> dict:
    out: dict[str, list[str]] = {"skills": [], "values": [], "ts-values": [], "core": [], "unresolved": []}
    for t in tags:
        resolved = resolve_tag(t, tagmap)
        if resolved:
            cat, slug = resolved
            if slug not in out[cat]:
                out[cat].append(slug)
        else:
            if t not in out["unresolved"]:
                out["unresolved"].append(t)
    return out

# --- Format B (Andreea Bejan, long rubric) ---

DIMENSION_PATTERNS = [
    ("understanding requirements", "domain-knowledge", "skills"),
    ("planning", "planning", "core"),
    ("tsdd", "tsdd", "skills"),
    ("reviewing", "code-review", "skills"),
    ("proactivity", "proactivity", "core"),
    ("team player", "team-player", "ts-values"),
    ("ownership", "extreme-ownership", "values"),
    ("communication", "communication", "core"),
]

RATING_LINE_RE = re.compile(r"^\s*\|?\s*([1-5])\s*\|?\s*$", re.MULTILINE)

def extract_events_format_b(text: str, character_id: str, page_id: str, month: str | None, tagmap: dict) -> tuple[list, list]:
    events = []
    orphans = []
    chunks = re.split(r"How well do you think you[’']ve performed.*?when it comes to\s+", text, flags=re.IGNORECASE)
    seq = 0
    for chunk in chunks[1:]:
        first_line = chunk.split("\n", 1)[0].strip().rstrip("?").lower()
        slug = None
        category = None
        for pat, s, c in DIMENSION_PATTERNS:
            if pat in first_line:
                slug = s
                category = c
                break
        ratings = [int(m.group(1)) for m in RATING_LINE_RE.finditer(chunk[:2000])]
        team_rating = ratings[0] if len(ratings) >= 1 else None
        sdl_rating = ratings[1] if len(ratings) >= 2 else None
        effective = sdl_rating if sdl_rating is not None else team_rating
        if effective is None:
            continue
        delta = (effective - 3) * 0.25
        seq += 1
        ev_id = f"{character_id}__{page_id}__b{seq:03d}"
        if slug and category:
            tag_cats: dict[str, list[str]] = {"skills": [], "values": [], "ts-values": [], "core": [], "unresolved": []}
            tag_cats[category].append(slug)
            ev = {
                "id": ev_id,
                "character_id": character_id,
                "mpr_page_id": page_id,
                "month": month,
                "section": "Rubric",
                "delta": delta,
                "tags": [f"#{slug}"],
                "tag_categories": tag_cats,
                "ticket_refs": [],
                "categorized_by": "rubric_dimension",
                "note": f"Dimension: {first_line[:80]} — team:{team_rating} sdl:{sdl_rating}",
                "source_excerpt": chunk.strip()[:500],
            }
            events.append(ev)
        else:
            ev = {
                "id": ev_id,
                "character_id": character_id,
                "mpr_page_id": page_id,
                "month": month,
                "section": "Rubric",
                "delta": delta,
                "tags": [],
                "tag_categories": {"skills": [], "values": [], "ts-values": [], "core": [], "unresolved": [first_line[:60]]},
                "ticket_refs": [],
                "categorized_by": "orphan",
                "note": f"Unmapped dimension: {first_line[:80]} — team:{team_rating} sdl:{sdl_rating}",
                "source_excerpt": chunk.strip()[:500],
                "orphan_reason": "unmapped_dimension",
            }
            orphans.append(ev)
    return events, orphans

# --- Format detection ---

def detect_format(text: str) -> str:
    if SCORE_RE.search(text):
        return "A"
    if re.search(r"how well do you think you[’']ve performed", text, re.IGNORECASE):
        return "B"
    return "unknown"

# --- Main parse loop ---

def parse_all():
    tagmap = load_tags()
    all_events = []
    all_orphans = []
    mpr_index: dict[str, list] = {}
    for person_dir in sorted(MPR_CACHE.iterdir()):
        if not person_dir.is_dir():
            continue
        character_id = person_dir.name
        mpr_index.setdefault(character_id, [])
        for md_file in sorted(person_dir.glob("*.md")):
            page_id = md_file.stem
            text = md_file.read_text(errors="replace")
            title = next((l.strip("# ").strip() for l in text.splitlines() if l.strip()), "")
            month = parse_month_year(title) or parse_month_year(text[:500])
            score_info = parse_score_block(text[:1500])
            fmt = detect_format(text)
            if fmt == "A":
                evs, orphs = extract_events_format_a(text, character_id, page_id, month, tagmap)
            elif fmt == "B":
                evs, orphs = extract_events_format_b(text, character_id, page_id, month, tagmap)
            else:
                evs, orphs = [], []
            all_events.extend(evs)
            all_orphans.extend(orphs)
            mpr_index[character_id].append({
                "page_id": page_id,
                "month": month,
                "format": fmt,
                "score": score_info["score"],
                "self_score": score_info["self_score"],
                "level_at_time": score_info["level"],
                "event_count": len(evs),
                "orphan_count": len(orphs),
                "title": title,
            })
    return all_events, all_orphans, mpr_index

def write_events(events, orphans):
    out: dict = {
        "version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "total_events": len(events),
            "total_orphans": len(orphans),
            "by_character": {},
            "by_categorization": {},
        },
        "events": events,
        "orphans": orphans,
    }
    for ev in events:
        cid = ev["character_id"]
        out["stats"]["by_character"].setdefault(cid, {"events": 0, "orphans": 0})
        out["stats"]["by_character"][cid]["events"] += 1
        cb = ev.get("categorized_by", "?")
        out["stats"]["by_categorization"][cb] = out["stats"]["by_categorization"].get(cb, 0) + 1
    for ev in orphans:
        cid = ev["character_id"]
        out["stats"]["by_character"].setdefault(cid, {"events": 0, "orphans": 0})
        out["stats"]["by_character"][cid]["orphans"] += 1
    (DATA / "events.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"[events] {len(events)} events, {len(orphans)} orphans -> data/events.json")

def write_mpr_index(mpr_index):
    (DATA / "mpr_index.json").write_text(json.dumps({
        "version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "characters": mpr_index,
    }, indent=2, ensure_ascii=False))
    print(f"[mpr_index] {sum(len(v) for v in mpr_index.values())} MPRs -> data/mpr_index.json")

if __name__ == "__main__":
    events, orphans, mpr_index = parse_all()
    write_events(events, orphans)
    write_mpr_index(mpr_index)
    print("\n--- Per-character event count ---")
    by_char: dict[str, int] = {}
    for ev in events:
        by_char[ev["character_id"]] = by_char.get(ev["character_id"], 0) + 1
    for cid, n in sorted(by_char.items(), key=lambda x: -x[1]):
        print(f"  {cid:20s} {n:4d} events")
    print(f"\n--- Orphans by character ---")
    by_orph: dict[str, int] = {}
    for ev in orphans:
        by_orph[ev["character_id"]] = by_orph.get(ev["character_id"], 0) + 1
    for cid, n in sorted(by_orph.items(), key=lambda x: -x[1]):
        print(f"  {cid:20s} {n:4d} orphans")
    print(f"\n--- Categorization mode ---")
    by_cat: dict[str, int] = {}
    for ev in events:
        cb = ev.get("categorized_by", "?")
        by_cat[cb] = by_cat.get(cb, 0) + 1
    for cb, n in sorted(by_cat.items(), key=lambda x: -x[1]):
        print(f"  {cb:30s} {n:4d}")
