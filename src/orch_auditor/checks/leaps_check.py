# src/orch_auditor/checks/leaps_check.py
from __future__ import annotations

from typing import Dict, List

from ..config import Config
from ..model import Finding, Score, Severity


def run_leaps_check(score: Score, config: Config) -> List[Finding]:
    """
    V1 checklist #10: Large melodic leaps + high-speed + extreme register combo warnings.
    
    Heuristic: flag when all three conditions are met:
    - Leap >= min_leap_semitones
    - Tempo >= min_tempo_bpm
    - Register >= min_register_percent (top X% of range)
    """
    findings: List[Finding] = []
    leaps_cfg = config.raw.get("leaps", {})
    min_leap = int(leaps_cfg.get("min_leap_semitones", 13))
    min_tempo = float(leaps_cfg.get("min_tempo_bpm", 90))
    min_register_percent = float(leaps_cfg.get("min_register_percent", 0.7))

    # Check if tempo meets threshold
    if score.tempo_bpm is None or score.tempo_bpm < min_tempo:
        return findings  # Skip if tempo too slow or unknown

    for part in score.parts:
        r = config.ranges_for_part(part.id)
        if not r:
            continue

        min_midi = int(r["min"])
        max_midi = int(r["max"])
        span = max_midi - min_midi
        register_threshold = min_midi + (span * min_register_percent)

        if not part.events:
            continue

        # Group by onset and take top pitch at each onset
        by_onset: Dict[float, int] = {}
        for ev in part.events:
            onset = ev.onset_beats
            if onset not in by_onset:
                by_onset[onset] = ev.pitch_midi
            else:
                by_onset[onset] = max(by_onset[onset], ev.pitch_midi)

        onsets_sorted = sorted(by_onset.keys())
        if len(onsets_sorted) < 2:
            continue

        last_pitch = None
        last_onset = None
        for onset in onsets_sorted:
            pitch = by_onset[onset]
            if last_pitch is not None:
                leap = abs(pitch - last_pitch)
                if leap >= min_leap:
                    # Check if in extreme register
                    if pitch >= register_threshold or last_pitch >= register_threshold:
                        # Find representative event
                        rep_ev = None
                        for ev in part.events:
                            if abs(ev.onset_beats - onset) < 0.01 and ev.pitch_midi == pitch:
                                rep_ev = ev
                                break

                        if rep_ev:
                            last_pitch_name = None
                            for ev in part.events:
                                if abs(ev.onset_beats - last_onset) < 0.01 and ev.pitch_midi == last_pitch:
                                    last_pitch_name = ev.pitch_name
                                    break

                            findings.append(
                                Finding(
                                    id="LEAPS_LARGE_FAST_EXTREME",
                                    severity=Severity.WARN,
                                    part_id=part.id,
                                    measure=rep_ev.measure,
                                    time_beats=onset,
                                    time_seconds=rep_ev.onset_seconds,
                                    message=f"Large leap in extreme register at fast tempo: {last_pitch_name} → {rep_ev.pitch_name}",
                                    evidence=f"leap={leap} semitones, tempo={score.tempo_bpm:.1f} BPM, register={rep_ev.pitch_name} (top {min_register_percent*100:.0f}%)",
                                    suggestion="Consider stepwise motion or reducing tempo for playability (heuristic).",
                                )
                            )
            last_pitch = pitch
            last_onset = onset

    return findings
