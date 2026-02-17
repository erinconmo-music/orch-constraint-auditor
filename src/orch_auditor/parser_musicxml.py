# src/orch_auditor/parser_musicxml.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from music21 import converter, note, chord, tempo as m21tempo, meter

from .model import Score, Part, NoteEvent


PART_ORDER = ["vln1", "vln2", "vla", "vc", "cb"]


def _part_key_from_name(name: str) -> Optional[str]:
    if not name:
        return None
    s = name.lower().strip()

    # violins
    if "violin" in s or "vln" in s:
        if "ii" in s or "2" in s:
            return "vln2"
        if "i" in s or "1" in s:
            return "vln1"
        return "vln1"

    # viola
    if "viola" in s or "vla" in s:
        return "vla"

    # cello
    if "violoncello" in s or "cello" in s or "vc" in s:
        return "vc"

    # bass
    if (
        "contrabass" in s
        or "double bass" in s
        or "contrabajo" in s
        or "cb" in s
        or "bass" == s
    ):
        return "cb"

    return None


def _detect_tempo_bpm(score_stream) -> Optional[float]:
    try:
        marks = list(score_stream.recurse().getElementsByClass(m21tempo.MetronomeMark))
        for mm in marks:
            bpm = mm.getQuarterBPM()
            if bpm:
                return float(bpm)
    except Exception:
        return None
    return None


def _detect_time_signature(score_stream) -> Optional[str]:
    try:
        ts = list(score_stream.recurse().getElementsByClass(meter.TimeSignature))
        if ts:
            return ts[0].ratioString
    except Exception:
        return None
    return None


def _beats_to_seconds(beats: float, tempo_bpm: Optional[float]) -> Optional[float]:
    if tempo_bpm is None:
        return None
    return float(beats) * (60.0 / float(tempo_bpm))


def parse_musicxml(path: str) -> Score:
    s = converter.parse(path)

    tempo_bpm = _detect_tempo_bpm(s)
    time_sig = _detect_time_signature(s)

    # Keep only parts with notes
    parts_all = list(getattr(s, "parts", []))
    nonempty_parts = []
    for p in parts_all:
        try:
            if len(list(p.recurse().notes)) > 0:
                nonempty_parts.append(p)
        except Exception:
            continue

    # Identify canonical part ids by name or instrument, then fill remaining by order
    found: Dict[str, any] = {}
    for p in nonempty_parts:
        pname = (getattr(p, "partName", "") or "").strip()
        inst = None
        try:
            inst = p.getInstrument(returnDefault=False)
        except Exception:
            inst = None
        iname = ""
        if inst is not None:
            iname = (getattr(inst, "instrumentName", None) or "") or ""
            if not iname:
                try:
                    iname = inst.bestName() or ""
                except Exception:
                    iname = ""

        key = _part_key_from_name(pname) or _part_key_from_name(iname)
        if key and key not in found:
            found[key] = p

    remaining = [k for k in PART_ORDER if k not in found]
    if remaining:
        unused = [p for p in nonempty_parts if p not in found.values()]
        for k, p in zip(remaining, unused):
            found[k] = p

    parts: List[Part] = []
    for part_id in PART_ORDER:
        if part_id not in found:
            continue
        p = found[part_id]
        part_name = (getattr(p, "partName", None) or "").strip() or part_id

        events = _extract_events(p, part_id=part_id, part_name=part_name, tempo_bpm=tempo_bpm)
        parts.append(Part(id=part_id, name=part_name, events=events))

    return Score(parts=parts, tempo_bpm=tempo_bpm, time_signature=time_sig, title=None)


def _measure_number_for(el) -> Optional[int]:
    try:
        m = el.getContextByClass("Measure")
        if m is not None:
            n = getattr(m, "number", None)
            return int(n) if n is not None else None
    except Exception:
        return None
    return None


def _extract_events(p_stream, part_id: str, part_name: str, tempo_bpm: Optional[float]) -> List[NoteEvent]:
    """
    Extract NoteEvents from a part.
    - Uses offsets in quarterLength as "beats".
    - Merges ties for note.Note (basic but robust for common MusicXML exports).
    - For chords, emits one NoteEvent per pitch at the same onset, and marks is_in_chord=True.
    """
    raw: List[Tuple[float, float, int, str, Optional[int], bool, bool]] = []
    # (onset_beats, dur_beats, midi, pitch_name, measure, is_in_chord, is_tied)

    for el in p_stream.recurse().notes:
        onset = float(el.offset)
        dur = float(el.quarterLength)
        meas = _measure_number_for(el)

        if isinstance(el, note.Note):
            midi = int(el.pitch.midi)
            pname = el.pitch.nameWithOctave
            tied = bool(getattr(el, "tie", None) is not None)
            raw.append((onset, dur, midi, pname, meas, False, tied))

        elif isinstance(el, chord.Chord):
            # chord: emit per pitch
            tied = bool(getattr(el, "tie", None) is not None)
            for pit in el.pitches:
                midi = int(pit.midi)
                pname = pit.nameWithOctave
                raw.append((onset, dur, midi, pname, meas, True, tied))

    # Merge ties (per pitch) for note events that share the same midi and are consecutive.
    # Heuristic: if an event is tied, and the next event starts exactly at end time with same midi, merge.
    raw_sorted = sorted(raw, key=lambda x: (x[0], x[2]))
    merged: List[Tuple[float, float, int, str, Optional[int], bool, bool]] = []

    i = 0
    while i < len(raw_sorted):
        onset, dur, midi, pname, meas, is_chord, is_tied = raw_sorted[i]
        end = onset + dur

        # Only attempt merge when flagged tied (MusicXML exports usually mark both sides).
        if is_tied:
            j = i + 1
            total_dur = dur
            last_end = end
            last_meas = meas
            # Merge consecutive same-pitch events whose onset equals last_end
            while j < len(raw_sorted):
                n_onset, n_dur, n_midi, n_pname, n_meas, n_is_chord, n_is_tied = raw_sorted[j]
                if n_midi != midi:
                    j += 1
                    continue
                if abs(n_onset - last_end) < 1e-6:
                    total_dur += n_dur
                    last_end = n_onset + n_dur
                    last_meas = last_meas or n_meas
                    j += 1
                    continue
                break

            merged.append((onset, total_dur, midi, pname, meas, is_chord, True))
            i = j
            continue

        merged.append((onset, dur, midi, pname, meas, is_chord, False))
        i += 1

    events: List[NoteEvent] = []
    for onset, dur, midi, pname, meas, is_chord, tied in merged:
        onset_s = _beats_to_seconds(onset, tempo_bpm)
        dur_s = _beats_to_seconds(dur, tempo_bpm)
        events.append(
            NoteEvent(
                part_id=part_id,
                part_name=part_name,
                pitch_midi=midi,
                pitch_name=pname,
                onset_beats=onset,
                duration_beats=dur,
                onset_seconds=onset_s,
                duration_seconds=dur_s,
                measure=meas,
                is_in_chord=is_chord,
                is_tied=tied,
                voice_index=None,
            )
        )

    return sorted(events, key=lambda e: (e.onset_beats, e.pitch_midi))
