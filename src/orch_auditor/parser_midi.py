# src/orch_auditor/parser_midi.py
from __future__ import annotations

from .model import Score


def parse_midi(path: str) -> Score:
    """
    Optional (secondary) input support.
    Stub for now — we will implement after MusicXML is stable.
    """
    raise NotImplementedError("MIDI parsing not implemented yet. Use MusicXML.")
