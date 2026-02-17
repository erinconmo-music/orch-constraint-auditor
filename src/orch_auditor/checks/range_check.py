# src/orch_auditor/checks/range_check.py
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..config import Config
from ..model import Finding, Score, Severity


def _cb_adjust_pitch_for_mode(pitch_written_midi: int, mode: str) -> int:
    # Written is one octave above sounding.
    if mode == "sounding":
        return pitch_written_midi - 12
    return pitch_written_midi


def _cb_adjust_range_for_mode(min_midi: int, max_midi: int, harmonic_max: int, mode: str) -> Tuple[int, int, int]:
    # Config cb ranges are defined in SOUNDING basis per checklist.
    # If we check WRITTEN, shift the allowed range up +12.
    if mode == "written":
        return min_midi + 12, max_midi + 12, harmonic_max + 12
    return min_midi, max_midi, harmonic_max


def run_range_check(score: Score, config: Config) -> List[Finding]:
    findings: List[Finding] = []
    bass_mode = config.bass_pitch_mode

    for part in score.parts:
        r = config.ranges_for_part(part.id)
        if not r:
            continue

        min_midi = int(r["min"])
        max_midi = int(r["max"])
        harmonic_max = int(r.get("harmonic_max", max_midi))

        for ev in part.events:
            pitch = ev.pitch_midi

            if part.id == "cb":
                # Apply written/sounding logic only for bass
                pitch_cmp = _cb_adjust_pitch_for_mode(pitch_written_midi=pitch, mode=bass_mode)
                min_cmp, max_cmp, harm_cmp = _cb_adjust_range_for_mode(min_midi, max_midi, harmonic_max, bass_mode)
            else:
                pitch_cmp = pitch
                min_cmp, max_cmp, harm_cmp = min_midi, max_midi, harmonic_max

            if pitch_cmp < min_cmp or pitch_cmp > harm_cmp:
                findings.append(
                    Finding(
                        id="RANGE_HARD_OUT_OF_BOUNDS",
                        severity=Severity.ERROR,
                        part_id=part.id,
                        measure=ev.measure,
                        time_beats=ev.onset_beats,
                        time_seconds=ev.onset_seconds,
                        message=f"Hard range violation in {part.id}: {ev.pitch_name}",
                        evidence=f"pitch_midi={pitch_cmp} allowed=[{min_cmp}..{harm_cmp}] mode={bass_mode}",
                        suggestion="Re-orchestrate or re-notate; if intended, verify playability and technique.",
                    )
                )
                continue

            if pitch_cmp > max_cmp:
                findings.append(
                    Finding(
                        id="RANGE_HARMONIC_EXTENSION",
                        severity=Severity.WARN,
                        part_id=part.id,
                        measure=ev.measure,
                        time_beats=ev.onset_beats,
                        time_seconds=ev.onset_seconds,
                        message=f"Above standard range (possible harmonic) in {part.id}: {ev.pitch_name}",
                        evidence=f"pitch_midi={pitch_cmp} standard_max={max_cmp} harmonic_max={harm_cmp} mode={bass_mode}",
                        suggestion="If this is a harmonic, ensure correct notation and verify performer feasibility.",
                    )
                )

    return findings
