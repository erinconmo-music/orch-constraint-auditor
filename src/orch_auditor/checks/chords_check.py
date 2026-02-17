# src/orch_auditor/checks/chords_check.py
from __future__ import annotations

from typing import Dict, List

from ..config import Config
from ..model import Finding, Score, Severity


def run_chords_check(score: Score, config: Config) -> List[Finding]:
    """
    V1 checklist #9: Chords/double-stops playability warnings.
    
    2-note chords allowed; 3-4 note chords flagged (configurable).
    """
    findings: List[Finding] = []
    chords_cfg = config.raw.get("chords", {})
    max_notes = int(chords_cfg.get("max_notes_per_chord", 2))

    for part in score.parts:
        # Group events by onset to detect chords
        by_onset: Dict[float, List] = {}
        for ev in part.events:
            onset = ev.onset_beats
            by_onset.setdefault(onset, []).append(ev)

        for onset, events_at_onset in by_onset.items():
            # Filter to distinct pitches (avoid counting same pitch twice)
            distinct_pitches = set(ev.pitch_midi for ev in events_at_onset)
            note_count = len(distinct_pitches)

            if note_count > max_notes:
                rep_ev = events_at_onset[0]
                pitch_names = ", ".join(sorted(set(ev.pitch_name for ev in events_at_onset)))
                findings.append(
                    Finding(
                        id="CHORDS_TOO_MANY_NOTES",
                        severity=Severity.WARN,
                        part_id=part.id,
                        measure=rep_ev.measure,
                        time_beats=onset,
                        time_seconds=rep_ev.onset_seconds,
                        message=f"Chord with {note_count} notes in {part.id}: {pitch_names}",
                        evidence=f"onset={onset:.2f} beats, pitches={pitch_names}, max_allowed={max_notes}",
                        suggestion=f"Consider reducing to <={max_notes} notes or redistributing across parts for playability.",
                    )
                )

    return findings
