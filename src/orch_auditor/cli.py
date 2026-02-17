# src/orch_auditor/cli.py
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .config import Config
from .parser_musicxml import parse_musicxml
from .parser_midi import parse_midi
from .checks import run_enabled_checks
from .report_md import ReportMetadata, render_markdown, render_json


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Strings v1 orchestration constraint auditor (MusicXML primary, MIDI secondary)."
    )
    parser.add_argument("--input", required=True, help="Path to input score (.musicxml/.xml/.mid/.midi).")
    parser.add_argument("--out", required=True, help="Path to output Markdown report.")
    parser.add_argument("--json-out", default=None, help="Optional JSON output path (defaults to --out with .json).")
    parser.add_argument("--config", default=None, help="Optional config YAML path (defaults to config/default_config.yaml).")
    return parser


def _parse_score(path: Path):
    ext = path.suffix.lower()
    if ext in [".musicxml", ".xml"]:
        return parse_musicxml(str(path))
    if ext in [".mid", ".midi"]:
        return parse_midi(str(path))
    raise ValueError(f"Unsupported input extension: {ext}")


def main() -> None:
    args = build_arg_parser().parse_args()

    cfg = Config.load(args.config)
    input_path = Path(args.input)
    out_md = Path(args.out)
    out_json = Path(args.json_out) if args.json_out else out_md.with_suffix(".json")

    score = _parse_score(input_path)
    findings = run_enabled_checks(score, cfg)

    meta = ReportMetadata(
        input_path=str(input_path),
        config_path=str(Path(args.config)) if args.config else None,
        generated_at_iso=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        measures_analyzed=None,
    )

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_markdown(score, findings, meta=meta), encoding="utf-8")

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(render_json(score, findings), ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK -> {out_md} (Markdown) and {out_json} (JSON)")


if __name__ == "__main__":
    main()
