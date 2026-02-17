# tests/test_integration.py
import pytest
from pathlib import Path

from orch_auditor.config import Config
from orch_auditor.parser_musicxml import parse_musicxml
from orch_auditor.checks import run_enabled_checks
from orch_auditor.report_md import render_markdown, render_json


def test_integration_demo_musicxml():
    """Integration test: parse demo.musicxml and generate report."""
    demo_path = Path(__file__).parent.parent / "examples" / "demo.musicxml"
    if not demo_path.exists():
        pytest.skip(f"Demo file not found: {demo_path}")

    score = parse_musicxml(str(demo_path))
    assert len(score.parts) > 0

    config = Config.load()
    findings = run_enabled_checks(score, config)

    # Generate reports
    md = render_markdown(score, findings)
    json_data = render_json(score, findings)

    # Basic assertions
    assert "# Orchestration Constraint Report" in md
    assert "summary" in json_data
    assert "findings" in json_data
    assert isinstance(json_data["findings"], list)

    # Score should have some events
    total_events = sum(len(p.events) for p in score.parts)
    assert total_events > 0
