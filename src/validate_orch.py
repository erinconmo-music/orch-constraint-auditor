import argparse
from typing import Dict, List, Tuple, Optional
from music21 import converter, note, chord, pitch

from rules_strings import (
    PART_ORDER, RANGES, CONGESTION_DENSITY, CONGESTION_SPAN_MAX, DUPLICATION_INTERVALS
)
from report import Issue, render_markdown

PART_LABEL = {
    "vln1": "Vln1",
    "vln2": "Vln2",
    "vla": "Vla",
    "vc": "Vc",
    "cb": "Cb",
}

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

def label(k: str) -> str:
    return PART_LABEL.get(k, k)

def note_name(m: int) -> str:
    return pitch.Pitch(m).nameWithOctave

def max_register_str(k: str) -> str:
    lo, hi = RANGES[k]
    return f"{note_name(lo)}-{note_name(hi)}"

def adler_tag_for(*parts: str) -> str:
    regs = "; ".join([f"Maximum register {label(p)} {max_register_str(p)}" for p in parts])
    return f"({regs}; Adler, 2016)"

def identify_parts(score) -> Dict[str, any]:
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

    remaining = [k for k in PART_ORDER if k not in found]
    if remaining:
        unused = [p for p in parts if p not in found.values()]
        for k, p in zip(remaining, unused):
            found[k] = p

    return found

def extract_events(p) -> List[Tuple[float, float, int]]:
    events = []

    # If the instrument transposes (e.g., Contrabass sounds 8vb),
    # convert to WRITTEN pitch before validation.
    trans_semi = 0
    try:
        inst = p.getInstrument(returnDefault=False)
        if inst and getattr(inst, "transposition", None):
            trans_semi = int(inst.transposition.semitones)  # written -> sounding
    except Exception:
        trans_semi = 0

    def to_written(midi: int) -> int:
        # If midi is sounding, revert to written by subtracting the transposition.
        # Example: contrabass transposition = -12 => written = sounding - (-12) = sounding + 12
        return int(midi - trans_semi)

    for el in p.recurse().notes:
        start = float(el.offset)
        dur = float(el.quarterLength)
        end = start + dur
        if isinstance(el, note.Note):
            events.append((start, end, to_written(int(el.pitch.midi))))
        elif isinstance(el, chord.Chord):
            for pit in el.pitches:
                events.append((start, end, to_written(int(pit.midi))))
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
                if midi < lo:
                    rec = lo
                    direction = "below minimum"
                else:
                    rec = hi
                    direction = "above maximum"

                issues.append(Issue(
                    kind="Out of range (warning)",
                    when=offset_to_when(p, s),
                    details=(
                        f"{label(k)} pitch {note_name(midi)} is {direction} for {label(k)}. "
                        f"Recommended: {note_name(rec)}. "
                        f"If this is intended as a harmonic, verify playability/notation. "
                        f"{adler_tag_for(k)}"
                    )
                ))
    return issues


def duplication_label(interval: int) -> str:
    if interval == 0:
        return "unison"
    if interval == 12:
        return "octave"
    if interval == 24:
        return "two octaves"
    return f"{interval} semitones"

def check_vertical(parts: Dict[str, any], events_by_part: Dict[str, list]) -> List[Issue]:
    issues: List[Issue] = []
    pts = time_points(events_by_part)

    for t in pts:
        sounding = {}
        for k in PART_ORDER:
            pitches_here = active_pitches(events_by_part.get(k, []), t)
            if pitches_here:
                sounding[k] = {
                    "min": min(pitches_here),
                    "max": max(pitches_here),
                    "pitches": pitches_here
                }

        # congestion: many parts in narrow span
        density = len(sounding)
        if density >= CONGESTION_DENSITY:
            all_p = [pp for d in sounding.values() for pp in d["pitches"]]
            if all_p:
                span = max(all_p) - min(all_p)
                if span <= CONGESTION_SPAN_MAX:
                    any_key = next(iter(sounding.keys()))
                    issues.append(Issue(
                        kind="Congestion",
                        when=offset_to_when(parts[any_key], t),
                        details=f"density={density}, span {note_name(min(all_p))}-{note_name(max(all_p))} (<= {CONGESTION_SPAN_MAX} semitones)"
                    ))

        # crossing/overlap between adjacent parts
        pairs = [("vln1", "vln2"), ("vln2", "vla"), ("vla", "vc"), ("vc", "cb")]
        for up, low in pairs:
            if up in sounding and low in sounding:
                up_min, up_max = sounding[up]["min"], sounding[up]["max"]
                low_max = sounding[low]["max"]

                if low_max > up_max:
                    issues.append(Issue(
                        kind="Crossing",
                        when=offset_to_when(parts[up], t),
                        details=f"{label(low)} top {note_name(low_max)} crosses above {label(up)} top {note_name(up_max)} {adler_tag_for(low, up)}"
                    ))
                elif low_max > up_min:
                    issues.append(Issue(
                        kind="Overlap (warning)",
                        when=offset_to_when(parts[up], t),
                        details=f"{label(low)} top {note_name(low_max)} overlaps {label(up)} range {note_name(up_min)}-{note_name(up_max)} {adler_tag_for(low, up)}"
                    ))

        # duplications (unison/octaves) using top note per part
        keys = list(sounding.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, b = keys[i], keys[j]
                pa = sounding[a]["max"]
                pb = sounding[b]["max"]
                interval = abs(pa - pb)
                if interval in DUPLICATION_INTERVALS:
                    issues.append(Issue(
                        kind="Duplication",
                        when=offset_to_when(parts[a], t),
                        details=f"{label(a)} {note_name(pa)} ~ {label(b)} {note_name(pb)} ({duplication_label(interval)}) {adler_tag_for(a, b)}"
                    ))

        # triplication+ (top note only, to reduce noise)
        pitch_map: Dict[int, List[str]] = {}
        for pk, d in sounding.items():
            m = d["max"]  # top note per part
            pitch_map.setdefault(m, []).append(pk)

        for m, ks in pitch_map.items():
            if len(ks) >= 3:
                ks_sorted = sorted(ks, key=lambda x: PART_ORDER.index(x) if x in PART_ORDER else 999)
                any_part = parts[ks_sorted[0]]
                issues.append(Issue(
                    kind="Triplication+",
                    when=offset_to_when(any_part, t),
                    details=(
                        f"Top pitch {note_name(m)} duplicated {len(ks_sorted)}x across parts: "
                        f"{', '.join(label(x) for x in ks_sorted)}. "
                        f"Consider reducing to <=2 or redistributing. (Adler, 2016)"
                    )
                ))

    return issues


def summarize(parts: Dict[str, any], events_by_part: Dict[str, list], issues: List[Issue]) -> Dict[str, str]:
    total_events = sum(len(evs) for evs in events_by_part.values())
    covered = ", ".join([k for k in PART_ORDER if k in parts])
    return {
        "Parts detected": covered,
        "Total note events": str(total_events),
        "Total issues": str(len(issues)),
        "Pitch basis": "written pitch (score pitch)",
        "Checks": "Range, Crossing/Overlap, Density/Congestion, Duplication"
    }

def main():
    ap = argparse.ArgumentParser(description="Strings v1 orchestration constraint auditor (MusicXML/MIDI)")
    ap.add_argument("input", help="Path to .musicxml/.xml/.mid/.midi")
    ap.add_argument("--out", default="outputs/report.md", help="Output Markdown path")
    args = ap.parse_args()

    score = converter.parse(args.input)
    parts = identify_parts(score)
    parts = {k: v for k, v in parts.items() if k in PART_ORDER}
    events_by_part = {k: extract_events(p) for k, p in parts.items()}

    issues: List[Issue] = []
    issues.extend(check_ranges(parts, events_by_part))
    issues.extend(check_vertical(parts, events_by_part))

    md = render_markdown(summarize(parts, events_by_part, issues), issues)

    import os
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"OK -> {args.out}")

if __name__ == "__main__":
    main()
