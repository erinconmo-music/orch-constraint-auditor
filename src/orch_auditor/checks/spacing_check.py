# src/orch_auditor/checks/spacing_check.py
from __future__ import annotations

from typing import Dict, List

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


def run_spacing_check(score: Score, config: Config) -> List[Finding]:
    """
    V1 checklist #5: Register spacing / "mud risk" warnings.
    
    Heuristic: wider gaps required in low register, smaller gaps higher up,
    optionally widen again at extreme high register.
    """
    findings: List[Finding] = []
    spacing_cfg = config.raw.get("spacing", {})
    low_break = int(spacing_cfg.get("low_break_midi", 52))
    high_break = int(spacing_cfg.get("high_break_midi", 72))
    min_interval_low = int(spacing_cfg.get("min_interval_low", 7))
    min_interval_mid = int(spacing_cfg.get("min_interval_mid", 4))
    min_interval_high = int(spacing_cfg.get("min_interval_high", 6))

    parts_map = {p.id: p for p in score.parts}
    pts = _time_points(score)

    for t in pts:
        sounding: Dict[str, List[int]] = {}
        for pid in PART_ORDER:
            p = parts_map.get(pid)
            if not p:
                continue
            pitches = _active_pitches(p.events, t)
            if pitches:
                sounding[pid] = pitches

        for upper_id, lower_id in ADJ_PAIRS:
            if upper_id not in sounding or lower_id not in sounding:
                continue

            upper_max = max(sounding[upper_id])
            lower_min = min(sounding[lower_id])
            interval = lower_min - upper_max

            if interval < 0:
                continue  # Crossing handled by crossing_check

            # Determine register band based on average pitch
            avg_pitch = (upper_max + lower_min) / 2.0
            if avg_pitch < low_break:
                required_interval = min_interval_low
                band = "low"
            elif avg_pitch > high_break:
                required_interval = min_interval_high
                band = "high"
            else:
                required_interval = min_interval_mid
                band = "mid"

            if interval < required_interval:
                findings.append(
                    Finding(
                        id="SPACING_TOO_NARROW",
                        severity=Severity.WARN,
                        part_id=upper_id,
                        measure=None,
                        time_beats=t,
                        time_seconds=None,
                        message=f"Register spacing too narrow between {upper_id} and {lower_id}",
                        evidence=f"interval={interval} semitones < required {required_interval} in {band} register (avg={avg_pitch:.1f})",
                        suggestion=f"Consider widening spacing to >= {required_interval} semitones to avoid muddiness (heuristic).",
                    )
                )

    return findings
