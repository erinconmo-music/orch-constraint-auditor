# src/orch_auditor/model.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Severity(str, Enum):
    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"


@dataclass
class NoteEvent:
    part_id: str
    part_name: str
    pitch_midi: int          # canonical pitch used by checks (written by default)
    pitch_name: str
    onset_beats: float
    duration_beats: float
    onset_seconds: Optional[float]
    duration_seconds: Optional[float]
    measure: Optional[int]
    is_in_chord: bool = False
    is_tied: bool = False
    voice_index: Optional[int] = None


@dataclass
class Part:
    id: str
    name: str
    events: List[NoteEvent]


@dataclass
class Score:
    parts: List[Part]
    tempo_bpm: Optional[float] = None
    time_signature: Optional[str] = None
    title: Optional[str] = None


class Confidence(str, Enum):
    HIGH = "High"
    MED = "Med"
    LOW = "Low"


@dataclass
class ScoreBreakdown:
    """
    Deterministic scoring components for candidate ranking.
    Higher is better for all fields.
    """
    violation_reduction: float = 0.0
    minimal_change_cost: float = 0.0
    clarity_score: float = 0.0


@dataclass
class FixCandidate:
    title: str
    steps: List[str]
    expected_effect: Dict[str, Any] = field(default_factory=dict)
    tradeoffs: str = ""
    confidence: Confidence = Confidence.MED
    score_total: float = 0.0
    score_breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)


@dataclass
class Reference:
    book: str
    edition: str
    page: str
    excerpt: str
    url: Optional[str] = None
    concept: Optional[str] = None


@dataclass
class Finding:
    # Stable rule id (legacy + still used)
    id: str
    severity: Severity
    part_id: Optional[str]

    # Location (legacy fields)
    measure: Optional[int]
    time_beats: Optional[float]
    time_seconds: Optional[float]

    # Primary presentation fields (legacy)
    message: str
    evidence: str
    suggestion: Optional[str] = None

    # --- Chess-engine extensions (all optional; filled by upgraded checks) ---
    check_id: str = ""
    measure_start: Optional[int] = None
    measure_end: Optional[int] = None
    parts_involved: List[str] = field(default_factory=list)
    short_label: Optional[str] = None

    evidence_structured: Dict[str, Any] = field(default_factory=dict)
    why_text: Optional[str] = None
    so_what_text: Optional[str] = None

    fix_candidates: List[FixCandidate] = field(default_factory=list)
    references: List[Reference] = field(default_factory=list)
