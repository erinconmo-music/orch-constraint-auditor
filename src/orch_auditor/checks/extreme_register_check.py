# src/orch_auditor/checks/extreme_register_check.py
from __future__ import annotations

from typing import List, Optional

from ..config import Config
from ..model import Finding, Score, Severity


def run_extreme_register_check(score: Score, config: Config) -> List[Finding]:
    """
    V1 checklist #2: Sustained extreme register warnings.
    
    Warns on notes in the top/bottom X% of range held for >= min_duration_beats.
    """
    findings: List[Finding] = []
    extreme_cfg = config.raw.get("extreme_register", {})
    top_percent = float(extreme_cfg.get("top_percent", 0.15))
    bottom_percent = float(extreme_cfg.get("bottom_percent", 0.15))
    min_duration = float(extreme_cfg.get("min_duration_beats", 2.0))

    for part in score.parts:
        r = config.ranges_for_part(part.id)
        if not r:
            continue

        min_midi = int(r["min"])
        max_midi = int(r["max"])
        span = max_midi - min_midi

        top_threshold = max_midi - (span * top_percent)
        bottom_threshold = min_midi + (span * bottom_percent)

        for ev in part.events:
            if ev.duration_beats < min_duration:
                continue

            pitch = ev.pitch_midi
            if pitch >= top_threshold:
                findings.append(
                    Finding(
                        id="EXTREME_REGISTER_TOP_SUSTAINED",
                        severity=Severity.WARN,
                        part_id=part.id,
                        measure=ev.measure,
                        time_beats=ev.onset_beats,
                        time_seconds=ev.onset_seconds,
                        message=f"Sustained high register in {part.id}: {ev.pitch_name} held for {ev.duration_beats:.2f} beats",
                        evidence=f"pitch={ev.pitch_name} ({pitch}) in top {top_percent*100:.0f}% of range, duration={ev.duration_beats:.2f} beats",
                        suggestion="Consider easing register or shortening duration for playability.",
                    )
                )
            elif pitch <= bottom_threshold:
                findings.append(
                    Finding(
                        id="EXTREME_REGISTER_BOTTOM_SUSTAINED",
                        severity=Severity.WARN,
                        part_id=part.id,
                        measure=ev.measure,
                        time_beats=ev.onset_beats,
                        time_seconds=ev.onset_seconds,
                        message=f"Sustained low register in {part.id}: {ev.pitch_name} held for {ev.duration_beats:.2f} beats",
                        evidence=f"pitch={ev.pitch_name} ({pitch}) in bottom {bottom_percent*100:.0f}% of range, duration={ev.duration_beats:.2f} beats",
                        suggestion="Consider easing register or shortening duration for playability.",
                    )
                )

    return findings
