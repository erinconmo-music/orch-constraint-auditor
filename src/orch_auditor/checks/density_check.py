# src/orch_auditor/checks/density_check.py
from __future__ import annotations

from typing import Dict, List

from ..config import Config
from ..model import Finding, Score, Severity


def run_density_check(score: Score, config: Config) -> List[Finding]:
    """
    V1 checklist #6: Note density warnings per part (events per beat/second over a moving window).
    """
    findings: List[Finding] = []
    density_cfg = config.raw.get("density", {})
    window_beats = float(density_cfg.get("window_beats", 4.0))
    max_events = int(density_cfg.get("max_events_per_window", 12))

    for part in score.parts:
        if not part.events:
            continue

        # Collect all event onsets
        onsets = sorted(set(ev.onset_beats for ev in part.events))
        if len(onsets) < 2:
            continue

        # Sliding window
        for i in range(len(onsets)):
            window_start = onsets[i]
            window_end = window_start + window_beats

            # Count events that start within this window
            count = sum(1 for onset in onsets if window_start <= onset < window_end)

            if count > max_events:
                # Find a representative event in this window for reporting
                window_events = [
                    ev for ev in part.events
                    if window_start <= ev.onset_beats < window_end
                ]
                if window_events:
                    rep_ev = window_events[0]
                    findings.append(
                        Finding(
                            id="DENSITY_TOO_HIGH",
                            severity=Severity.WARN,
                            part_id=part.id,
                            measure=rep_ev.measure,
                            time_beats=window_start,
                            time_seconds=rep_ev.onset_seconds,
                            message=f"High note density in {part.id}: {count} events in {window_beats:.1f} beats",
                            evidence=f"window=[{window_start:.2f}..{window_end:.2f}] beats, count={count} > max={max_events}",
                            suggestion="Consider reducing note density or redistributing material for clarity.",
                        )
                    )
                    # Only report once per window to avoid spam
                    break

    return findings
