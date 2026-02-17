# src/orch_auditor/checks/doubling_check.py
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


def run_doubling_check(score: Score, config: Config) -> List[Finding]:
    """
    V1 checklist #8: Unison/octave stacking warnings (excessive doublings).
    """
    findings: List[Finding] = []
    doubling_cfg = config.raw.get("doubling", {})
    max_unison = int(doubling_cfg.get("max_unison_count", 2))
    max_octave = int(doubling_cfg.get("max_octave_count", 2))
    max_two_octave = int(doubling_cfg.get("max_two_octave_count", 2))

    parts_map = {p.id: p for p in score.parts}
    pts = _time_points(score)

    for t in pts:
        # Map pitch -> list of parts that have it
        pitch_to_parts: Dict[int, List[str]] = {}
        part_pitches: Dict[str, List[int]] = {}

        for pid in PART_ORDER:
            p = parts_map.get(pid)
            if not p:
                continue
            pitches = _active_pitches(p.events, t)
            if pitches:
                part_pitches[pid] = pitches
                for pitch in set(pitches):  # Avoid counting same pitch twice in one part
                    pitch_to_parts.setdefault(pitch, []).append(pid)

        # Check unisons (interval 0)
        for pitch, parts_list in pitch_to_parts.items():
            if len(parts_list) > max_unison:
                rep_part = parts_map[parts_list[0]]
                rep_ev = None
                for ev in rep_part.events:
                    if ev.onset_beats <= t < (ev.onset_beats + ev.duration_beats) and ev.pitch_midi == pitch:
                        rep_ev = ev
                        break

                if rep_ev:
                    findings.append(
                        Finding(
                            id="DOUBLING_UNISON_EXCESSIVE",
                            severity=Severity.WARN,
                            part_id=parts_list[0],
                            measure=rep_ev.measure,
                            time_beats=t,
                            time_seconds=rep_ev.onset_seconds,
                            message=f"Excessive unison doubling: {len(parts_list)} parts on {rep_ev.pitch_name}",
                            evidence=f"parts={parts_list}, pitch={rep_ev.pitch_name} ({pitch}), max_allowed={max_unison}",
                            suggestion="Consider reducing to <=2 parts or redistributing.",
                        )
                    )

        # Check octaves (intervals 12, 24)
        checked_intervals = set()
        for pitch1, parts1 in pitch_to_parts.items():
            for interval in [12, 24]:
                pitch2 = pitch1 + interval
                if pitch2 not in pitch_to_parts:
                    continue

                interval_key = (min(pitch1, pitch2), max(pitch1, pitch2))
                if interval_key in checked_intervals:
                    continue
                checked_intervals.add(interval_key)

                parts2 = pitch_to_parts[pitch2]
                total_parts = len(set(parts1 + parts2))

                max_allowed = max_octave if interval == 12 else max_two_octave
                if total_parts > max_allowed:
                    rep_part = parts_map[parts1[0]]
                    rep_ev = None
                    for ev in rep_part.events:
                        if ev.onset_beats <= t < (ev.onset_beats + ev.duration_beats) and ev.pitch_midi == pitch1:
                            rep_ev = ev
                            break

                    if rep_ev:
                        interval_name = "octave" if interval == 12 else "two octaves"
                        findings.append(
                            Finding(
                                id=f"DOUBLING_{interval_name.upper().replace(' ', '_')}_EXCESSIVE",
                                severity=Severity.WARN,
                                part_id=parts1[0],
                                measure=rep_ev.measure,
                                time_beats=t,
                                time_seconds=rep_ev.onset_seconds,
                                message=f"Excessive {interval_name} doubling: {total_parts} parts",
                                evidence=f"parts={list(set(parts1 + parts2))}, pitches={rep_ev.pitch_name}/{pitch2}, max_allowed={max_allowed}",
                                suggestion=f"Consider reducing to <={max_allowed} parts or redistributing.",
                            )
                        )

    return findings
