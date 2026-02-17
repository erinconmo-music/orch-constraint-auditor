# src/orch_auditor/checks/overlap_check.py
from __future__ import annotations

from typing import Dict, List

from ..config import Config
from ..model import Finding, Score, Severity

PART_ORDER = ["vln1", "vln2", "vla", "vc", "cb"]
ADJ_PAIRS = [("vln1", "vln2"), ("vln2", "vla"), ("vla", "vc"), ("vc", "cb")]


def run_overlap_check(score: Score, config: Config) -> List[Finding]:
    """
    V1 checklist #4: Voice overlap (successive) between adjacent parts.
    
    Detects when a note in the lower part overlaps in register with a previous
    note in the upper part that is still sounding (or vice versa in edge cases).
    """
    findings: List[Finding] = []
    parts_map = {p.id: p for p in score.parts}

    for upper_id, lower_id in ADJ_PAIRS:
        upper_part = parts_map.get(upper_id)
        lower_part = parts_map.get(lower_id)
        if not upper_part or not lower_part:
            continue

        # For each note in lower part, check if it overlaps with any currently
        # sounding note from upper part
        for lower_ev in lower_part.events:
            lower_start = lower_ev.onset_beats
            lower_end = lower_ev.onset_beats + lower_ev.duration_beats
            lower_pitch = lower_ev.pitch_midi

            # Check all upper part events that are sounding during lower note
            for upper_ev in upper_part.events:
                upper_start = upper_ev.onset_beats
                upper_end = upper_ev.onset_beats + upper_ev.duration_beats
                upper_pitch = upper_ev.pitch_midi

                # Time overlap: upper note is still sounding when lower note starts
                if upper_start < lower_start < upper_end:
                    # Register overlap: lower pitch is >= upper pitch
                    if lower_pitch >= upper_pitch:
                        findings.append(
                            Finding(
                                id="OVERLAP_SUCCESSIVE_ADJACENT",
                                severity=Severity.WARN,
                                part_id=lower_id,
                                measure=lower_ev.measure,
                                time_beats=lower_ev.onset_beats,
                                time_seconds=lower_ev.onset_seconds,
                                message=f"Voice overlap: {lower_id} {lower_ev.pitch_name} overlaps with {upper_id} {upper_ev.pitch_name}",
                                evidence=f"{lower_id}.{lower_ev.pitch_name} (m.{lower_ev.measure}) overlaps {upper_id}.{upper_ev.pitch_name} (m.{upper_ev.measure})",
                                suggestion="Consider redistributing or adjusting timing to avoid register overlap between adjacent parts.",
                            )
                        )

    return findings
