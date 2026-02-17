# src/orch_auditor/checks/crossing_check.py
from __future__ import annotations

from typing import Dict, List, Tuple

from ..config import Config
from ..model import Finding, Score, Severity

PART_ORDER = ["vln1", "vln2", "vla", "vc", "cb"]
ADJ_PAIRS = [("vln1", "vln2"), ("vln2", "vla"), ("vla", "vc"), ("vc", "cb")]


def _time_points(score: Score) -> List[float]:
    pts = set()
    for p in score.parts:
        for ev in p.events:
            pts.add(float(ev.onset_beats))
            pts.add(float(ev.onset_beats + ev.duration_beats))
    return sorted(t for t in pts if t >= 0.0)


def _active_pitches(events, t: float) -> List[int]:
    return [e.pitch_midi for e in events if e.onset_beats <= t < (e.onset_beats + e.duration_beats)]


def run_crossing_check(score: Score, config: Config) -> List[Finding]:
    findings: List[Finding] = []
    parts_map = {p.id: p for p in score.parts}

    pts = _time_points(score)
    for t in pts:
        sounding: Dict[str, Dict[str, int]] = {}
        for pid in PART_ORDER:
            p = parts_map.get(pid)
            if not p:
                continue
            pitches = _active_pitches(p.events, t)
            if pitches:
                sounding[pid] = {"min": min(pitches), "max": max(pitches)}

        for upper, lower in ADJ_PAIRS:
            if upper not in sounding or lower not in sounding:
                continue
            up_max = sounding[upper]["max"]
            low_max = sounding[lower]["max"]

            if low_max > up_max:
                findings.append(
                    Finding(
                        id="CROSSING_ADJACENT_SIMULTANEOUS",
                        severity=Severity.ERROR,
                        part_id=upper,
                        measure=None,
                        time_beats=t,
                        time_seconds=None,
                        message=f"Voice crossing: {lower} crosses above {upper}",
                        evidence=f"{lower}.max={low_max} > {upper}.max={up_max} at t={t}",
                        suggestion="Redistribute pitches to preserve vertical order or explicitly notate intended crossing.",
                    )
                )

    return findings
