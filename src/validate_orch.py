import argparse
from typing import Dict, List, Tuple, Optional
from music21 import converter, note, chord

from rules_strings import (
    PART_ORDER, RANGES, CONGESTION_DENSITY, CONGESTION_SPAN_MAX, DUPLICATION_INTERVALS
)
from report import Issue, render_markdown

def part_key_from_name(name: str) -> Optional[str]:
    if not name:
        return None
    s = name.lower().strip()
    if "violin" in s or "vln" in s:
        if "ii" in s or "2" in s:
            return "vln2"
        return "vln1"
    if "viola" in s or "vla" in s:
        return "vla"
    if "violoncello" in s or "cello" in s or "vc" in s:
        return "vc"
    if "contrabass" in s or "double bass" in s or "contrabajo" in s or "cb" in s:
        return "cb"
    return None

def identify_parts(score) -> Dict[str, any]:
    """
    MusicXML (Sibelius) friendly:
    - Uses partName / instrument names.
    - Filters parts without notes.
    """
    found: Dict[str, any] = {}
    parts_all = list(score.parts)

    parts = []
    for p in parts_all:
        try:
            if len(list(p.recurse().notes)) > 0:
                parts.append(p)
        except Exception:
            pass

    for p in parts:
        pname = (p.partName or "").strip()
        inst = p.getInstrument(returnDefault=False)
        iname = ""
        if inst:
            iname = inst.instrumentName or inst.bestName() or ""
        key = part_key_from_name(pname) or part_key_from_name(iname)
        if key and key not in found:
            found[key] = p

    # fallback by score order (only if something is missing)
    remaining = [k for k in PART_ORDER if k not in found]
    if remaining:
        unused = [p for p in parts if p not in found.values()]
        for k, p in zip(remaining, unused):
            found[k] = p

    return found

def extract_events(p) -> List[Tuple[float, float, int]]:
    events = []
    for el in p.recurse().notes:
        start = float(el.offset)
        dur = float(el.quarterLength)
        end = start + dur
        if isinstance(el, note.Note):
            events.append((start, end, int(el.pitch.midi)))
        elif isinstance(el, chord.Chord):
            for pit in el.pitches:
                events.append((start, end, int(pit.midi)))
    return events

def active_pitches(events, t: float) -> List[int]:
    return [m for (s, e, m) in events if s <= t < e]

def time_points(all_events: Dict[str, List[Tuple[float,float,int]]]) -> List[float]:
    pts = set()
    for evs in all_events.values():
        for s, e, _ in evs:
            pts.add(s); pts.add(e)
    return sorted(p for p in pts if p >= 0)

def offset_to_when(p, offset: float) -> str:
    try:
        els = list(p.recurse().getElementsByOffset(offset, mustBeginInSpan=False).notesAndRests)
        if els:
            el = els[0]
            m = el.getContextByClass('Measure')
            if m is not None:
                meas = getattr(m, "number", "?")
                beat = getattr(el, "beat", None)
                if beat is not None:
                    return f"m.{meas} beat {beat:.2f}"
                return f"m.{meas}"
    except Exception:
        pass
    return f"offset {offset:.2f} ql"

def check_ranges(parts: Dict[str, any], events_by_part: Dict[str, list]) -> List[Issue]:
    issues: List[Issue] = []
    for k, evs in events_by_part.items():
        lo, hi = RANGES[k]
        p = parts[k]
        for s, _, midi in evs:
            if midi < lo or midi > hi:
                issues.append(Issue(
                    kind="Range",
                    when=offset_to_when(p, s),
                    details=f"{k} pitch {midi} outside [{lo},{hi}] (written)"
                ))
    return issues

def check_vertical(parts: Dict[str, any], events_by_part: Dict[str, list]) -> List[Issue]:
    issues: List[Issue] = []
    pts = time_points(events_by_part)

    for t in pts:
        sounding = {}
        for k in PART_ORDER:
            pitches = active_pitches(events_by_part.get(k, []), t)
            if pitches:
                sounding[k] = {"min": min(pitches), "max": max(pitches), "pitches": pitches}

        # congestion: many parts in narrow span
        density = len(sounding)
        if density >= CONGESTION_DENSITY:
            all_p = [p for d in sounding.values() for p in d["pitches"]]
            span = max(all_p) - min(all_p) if all_p else 0
            if span <= CONGESTION_SPAN_MAX:
                any_part = parts[next(iter(sounding.keys()))]
                issues.append(Issue(
                    kind="Congestion",
                    when=offset_to_when(any_part, t),
                    details=f"density={density}, span={span} semitones"
                ))

        # crossing/overlap between adjacent parts
        pairs = [("vln1","vln2"), ("vln2","vla"), ("vla","vc"), ("vc","cb")]
        for up, low in pairs:
            if up in sounding and low in sounding:
                up_min, up_max = sounding[up]["min"], sounding[up]["max"]
                low_min, low_max = sounding[low]["min"], sounding[low]["max"]

                if low_max > up_max:
                    issues.append(Issue(
                        kind="Crossing",
                        when=offset_to_when(parts[up], t),
                        details=f"{low} max({low_max}) > {up} max({up_max})"
                    ))
                elif low_max > up_min:
                    issues.append(Issue(
                        kind="Overlap",
                        when=offset_to_when(parts[up], t),
                        details=f"{low} max({low_max}) overlaps {up} [{up_min},{up_max}]"
                    ))

        # dupl
