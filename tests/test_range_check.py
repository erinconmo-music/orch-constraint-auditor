# tests/test_range_check.py
import pytest

from orch_auditor.config import Config
from orch_auditor.model import NoteEvent, Part, Score
from orch_auditor.checks.range_check import run_range_check


def test_range_check_within_bounds():
    """Test that notes within range produce no findings."""
    score = Score(
        parts=[
            Part(
                id="vln1",
                name="Violin I",
                events=[
                    NoteEvent(
                        part_id="vln1",
                        part_name="Violin I",
                        pitch_midi=60,  # C4, well within G3-A7
                        pitch_name="C4",
                        onset_beats=0.0,
                        duration_beats=1.0,
                        onset_seconds=None,
                        duration_seconds=None,
                        measure=1,
                    )
                ],
            )
        ]
    )
    config = Config.load()
    findings = run_range_check(score, config)
    assert len(findings) == 0


def test_range_check_below_minimum():
    """Test that notes below minimum range produce ERROR findings."""
    score = Score(
        parts=[
            Part(
                id="vln1",
                name="Violin I",
                events=[
                    NoteEvent(
                        part_id="vln1",
                        part_name="Violin I",
                        pitch_midi=50,  # Below G3 (55)
                        pitch_name="D3",
                        onset_beats=0.0,
                        duration_beats=1.0,
                        onset_seconds=None,
                        duration_seconds=None,
                        measure=1,
                    )
                ],
            )
        ]
    )
    config = Config.load()
    findings = run_range_check(score, config)
    assert len(findings) == 1
    assert findings[0].id == "RANGE_HARD_OUT_OF_BOUNDS"
    assert findings[0].severity.value == "ERROR"


def test_range_check_above_max_but_within_harmonic():
    """Test that notes above max but within harmonic_max produce WARN."""
    score = Score(
        parts=[
            Part(
                id="vln1",
                name="Violin I",
                events=[
                    NoteEvent(
                        part_id="vln1",
                        part_name="Violin I",
                        pitch_midi=108,  # Above A7 (105) but below D8 (110)
                        pitch_name="C8",
                        onset_beats=0.0,
                        duration_beats=1.0,
                        onset_seconds=None,
                        duration_seconds=None,
                        measure=1,
                    )
                ],
            )
        ]
    )
    config = Config.load()
    findings = run_range_check(score, config)
    assert len(findings) == 1
    assert findings[0].id == "RANGE_HARMONIC_EXTENSION"
    assert findings[0].severity.value == "WARN"


def test_range_check_bass_written_mode():
    """Test bass range check in written mode (range shifted +12)."""
    score = Score(
        parts=[
            Part(
                id="cb",
                name="Contrabass",
                events=[
                    NoteEvent(
                        part_id="cb",
                        part_name="Contrabass",
                        pitch_midi=23,  # Written B0 (sounds B-1, MIDI 11)
                        pitch_name="B0",
                        onset_beats=0.0,
                        duration_beats=1.0,
                        onset_seconds=None,
                        duration_seconds=None,
                        measure=1,
                    )
                ],
            )
        ]
    )
    config = Config.load()
    # Config has bass_pitch_mode: "written" by default
    # CB range in config is B0-G4 (sounding: 23-67)
    # In written mode, we check written pitch against shifted range: 35-79
    # Written B0 = MIDI 23, which is < 35 (adjusted min), so should error
    findings = run_range_check(score, config)
    assert len(findings) >= 1
    assert any(f.id == "RANGE_HARD_OUT_OF_BOUNDS" for f in findings)
