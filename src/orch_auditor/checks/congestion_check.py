# src/orch_auditor/checks/congestion_check.py
from __future__ import annotations

from typing import Dict, List

from ..config import Config
from ..model import Finding, Score, Severity

PART_ORDER = ["vln1", "vln2", "vla", "vc", "cb"]


def _time_points(score: Score) -> List[float]:
    pts = set()
    for p in score.parts:
        for ev in p.events:
            pts.add(float(ev.onset_beats))
            pts.add(float(ev.onset_beats + ev.duration_beats))
    return sorted(t for t in pts if t >= 0.0)


def _active_pitches(events, t: float) -> List[int]:
    return [e.pitch_midi for e in events if e.onset_beats <= t < (e.onset_beats + e.duration_beats)]


def run_congestion_check(score: Score, config: Config) -> List[Finding]:
    """
    V1 checklist #7: Register congestion warnings (too many parts within a narrow pitch band).
    """
    findings: List[Finding] = []
    congestion_cfg = config.raw.get("congestion", {})
    window_beats = float(congestion_cfg.get("window_beats", 2.0))
    min_parts = int(congestion_cfg.get("min_parts", 4))
    max_span = int(congestion_cfg.get("max_span_semitones", 12))

    parts_map = {p.id: p for p in score.parts}
    pts = _time_points(score)

    # Sample at regular intervals (every window_beats)
    if not pts:
        return findings

    sampled_times = []
    current = pts[0]
    while current <= pts[-1]:
        sampled_times.append(current)
        current += window_beats

    for t in sampled_times:
        sounding: Dict[str, List[int]] = {}
        for pid in PART_ORDER:
            p = parts_map.get(pid)
            if not p:
                continue
            pitches = _active_pitches(p.events, t)
            if pitches:
                sounding[pid] = pitches

        if len(sounding) < min_parts:
            continue

        # Collect all pitches across all parts
        all_pitches = []
        for pitches in sounding.values():
            all_pitches.extend(pitches)

        if not all_pitches:
            continue

        span = max(all_pitches) - min(all_pitches)
        if span <= max_span:
            # Find a representative part for reporting
            rep_part_id = next(iter(sounding.keys()))
            rep_part = parts_map[rep_part_id]
            rep_ev = None
            for ev in rep_part.events:
                if ev.onset_beats <= t < (ev.onset_beats + ev.duration_beats):
                    rep_ev = ev
                    break

            if rep_ev:
                findings.append(
                    Finding(
                        id="CONGESTION_NARROW_SPAN",
                        severity=Severity.WARN,
                        part_id=rep_part_id,
                        measure=rep_ev.measure,
                        time_beats=t,
                        time_seconds=rep_ev.onset_seconds,
                        message=f"Register congestion: {len(sounding)} parts within {span} semitones",
                        evidence=f"parts={list(sounding.keys())}, span={span} semitones (range: {min(all_pitches)}-{max(all_pitches)})",
                        suggestion="Consider redistributing parts across a wider register to avoid muddiness.",
                    )
                )

    return findings
