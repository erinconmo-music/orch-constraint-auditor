# tests/test_crossing_check.py
import pytest

from orch_auditor.config import Config
from orch_auditor.model import NoteEvent, Part, Score
from orch_auditor.checks.crossing_check import run_crossing_check


def test_crossing_check_no_crossing():
    """Test that properly ordered parts produce no findings."""
    score = Score(
        parts=[
            Part(
                id="vln1",
                name="Violin I",
                events=[
                    NoteEvent(
                        part_id="vln1",
                        part_name="Violin I",
                        pitch_midi=72,  # C5
                        pitch_name="C5",
                        onset_beats=0.0,
                        duration_beats=1.0,
                        onset_seconds=None,
                        duration_seconds=None,
                        measure=1,
                    )
                ],
            ),
            Part(
                id="vln2",
                name="Violin II",
                events=[
                    NoteEvent(
                        part_id="vln2",
                        part_name="Violin II",
                        pitch_midi=60,  # C4, below vln1
                        pitch_name="C4",
                        onset_beats=0.0,
                        duration_beats=1.0,
                        onset_seconds=None,
                        duration_seconds=None,
                        measure=1,
                    )
                ],
            ),
        ]
    )
    config = Config.load()
    findings = run_crossing_check(score, config)
    assert len(findings) == 0


def test_crossing_check_detects_crossing():
    """Test that crossing (lower part above upper) produces ERROR."""
    score = Score(
        parts=[
            Part(
                id="vln1",
                name="Violin I",
                events=[
                    NoteEvent(
                        part_id="vln1",
                        part_name="Violin I",
                        pitch_midi=60,  # C4
                        pitch_name="C4",
                        onset_beats=0.0,
                        duration_beats=1.0,
                        onset_seconds=None,
                        duration_seconds=None,
                        measure=1,
                    )
                ],
            ),
            Part(
                id="vln2",
                name="Violin II",
                events=[
                    NoteEvent(
                        part_id="vln2",
                        part_name="Violin II",
                        pitch_midi=72,  # C5, above vln1 -> crossing
                        pitch_name="C5",
                        onset_beats=0.0,
                        duration_beats=1.0,
                        onset_seconds=None,
                        duration_seconds=None,
                        measure=1,
                    )
                ],
            ),
        ]
    )
    config = Config.load()
    findings = run_crossing_check(score, config)
    assert len(findings) >= 1
    assert any(f.id == "CROSSING_ADJACENT_SIMULTANEOUS" for f in findings)
    assert any(f.severity.value == "ERROR" for f in findings)
