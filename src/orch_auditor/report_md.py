# src/orch_auditor/report_md.py
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from collections import Counter
from typing import Dict, Iterable, List, Optional, Tuple

from .model import Confidence, Finding, FixCandidate, Reference, Score, Severity


def _fmt_time(f: Finding) -> str:
    if f.measure is not None:
        base = f"m.{f.measure}"
    else:
        base = "m.?"

    if f.time_seconds is not None:
        return f"{base} | {f.time_seconds:.2f}s"
    if f.time_beats is not None:
        return f"{base} | beat {f.time_beats:.2f}"
    return base


@dataclass(frozen=True)
class ReportMetadata:
    input_path: Optional[str] = None
    config_path: Optional[str] = None
    generated_at_iso: Optional[str] = None
    measures_analyzed: Optional[Tuple[Optional[int], Optional[int]]] = None


def _now_iso_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _severity_icon(sev: Severity) -> str:
    if sev == Severity.ERROR:
        return "❌"
    if sev == Severity.WARN:
        return "⚠️"
    return "✅"


def _severity_order(sev: Severity) -> int:
    return {Severity.ERROR: 0, Severity.WARN: 1, Severity.INFO: 2}.get(sev, 99)


def _measure_span(f: Finding) -> Tuple[Optional[int], Optional[int]]:
    if f.measure_start is not None or f.measure_end is not None:
        return f.measure_start, f.measure_end
    if f.measure is not None:
        return f.measure, f.measure
    return None, None


def _measures_analyzed(score: Score) -> Tuple[Optional[int], Optional[int]]:
    ms: List[int] = []
    for p in score.parts:
        for ev in p.events:
            if ev.measure is not None:
                ms.append(int(ev.measure))
    if not ms:
        return None, None
    return min(ms), max(ms)


def _health_score(findings: Iterable[Finding]) -> int:
    """
    Deterministic placeholder health score (0–100).
    Will be refined in commit 5.
    """
    c = Counter([f.severity for f in findings])
    penalty = c.get(Severity.ERROR, 0) * 15 + c.get(Severity.WARN, 0) * 5 + c.get(Severity.INFO, 0) * 1
    return max(0, min(100, 100 - int(penalty)))


def _finding_sort_key(f: Finding):
    ms, me = _measure_span(f)
    return (
        _severity_order(f.severity),
        ms if ms is not None else 10**9,
        me if me is not None else 10**9,
        f.check_id or f.id,
        f.part_id or "",
        f.message,
    )


def _coerce_check_id(f: Finding) -> str:
    return f.check_id or f.id


def _coerce_short_label(f: Finding) -> str:
    return f.short_label or f.message


def _coerce_parts_involved(f: Finding) -> List[str]:
    if f.parts_involved:
        return f.parts_involved
    if f.part_id:
        return [f.part_id]
    return []


def _fmt_measure_range(ms: Optional[int], me: Optional[int]) -> str:
    if ms is None and me is None:
        return "?"
    if ms is None:
        return f"?–{me}"
    if me is None:
        return f"{ms}–?"
    if ms == me:
        return str(ms)
    return f"{ms}–{me}"


def _fmt_candidate(c: FixCandidate) -> List[str]:
    conf = c.confidence.value if hasattr(c.confidence, "value") else str(c.confidence)
    lines: List[str] = []
    lines.append(f"**{c.title}**")
    if c.steps:
        for s in c.steps:
            lines.append(f"- {s}")
    if c.expected_effect:
        lines.append(f"- Expected impact: {c.expected_effect}")
    if c.tradeoffs:
        lines.append(f"- Tradeoffs: {c.tradeoffs}")
    lines.append(f"- Confidence: {conf}")
    lines.append(f"- Score: {c.score_total:.2f} | breakdown={c.score_breakdown.__dict__}")
    return lines


def _pick_reference(refs: List[Reference]) -> Optional[Reference]:
    return refs[0] if refs else None


def render_markdown(score: Score, findings: List[Finding], meta: Optional[ReportMetadata] = None) -> str:
    lines: List[str] = []
    meta = meta or ReportMetadata(generated_at_iso=_now_iso_utc(), measures_analyzed=_measures_analyzed(score))
    if not meta.generated_at_iso:
        meta = ReportMetadata(
            input_path=meta.input_path,
            config_path=meta.config_path,
            generated_at_iso=_now_iso_utc(),
            measures_analyzed=meta.measures_analyzed or _measures_analyzed(score),
        )

    lines.append("# Orchestration Constraint Report (Strings v1)\n")

    parts = ", ".join([p.id for p in score.parts])
    total_events = sum(len(p.events) for p in score.parts)
    ms, me = meta.measures_analyzed or (None, None)

    lines.append("## Metadata\n")
    if meta.input_path:
        lines.append(f"- **File:** `{meta.input_path}`")
    if meta.config_path:
        lines.append(f"- **Config:** `{meta.config_path}`")
    lines.append(f"- **Generated:** {meta.generated_at_iso}")
    lines.append(f"- **Measures analyzed:** { _fmt_measure_range(ms, me) }")
    if score.tempo_bpm is not None:
        lines.append(f"- **Tempo (approx):** {score.tempo_bpm:.1f} BPM")
    lines.append("")

    lines.append("## Scoreboard\n")
    by_sev = Counter([f.severity for f in findings])
    lines.append(f"- **Orchestration Health:** {_health_score(findings)}/100")
    lines.append(f"- **Critical (ERROR):** {by_sev.get(Severity.ERROR, 0)}")
    lines.append(f"- **Warning (WARN):** {by_sev.get(Severity.WARN, 0)}")
    lines.append(f"- **Info (INFO):** {by_sev.get(Severity.INFO, 0)}")
    lines.append("")

    if not findings:
        lines.append("## Findings\n")
        lines.append("No issues found.\n")
        return "\n".join(lines)

    # Quick Fixes: top candidates across all findings (if present)
    all_candidates: List[Tuple[float, Finding, FixCandidate]] = []
    for f in findings:
        for c in (f.fix_candidates or [])[:3]:
            all_candidates.append((c.score_total, f, c))
    if all_candidates:
        lines.append("## Quick Fixes (top 5 moves)\n")
        for score_total, f, c in sorted(all_candidates, key=lambda x: (-x[0], _finding_sort_key(x[1])))[:5]:
            ms2, me2 = _measure_span(f)
            lines.append(
                f"- {_severity_icon(f.severity)} **{c.title}** "
                f"({ _coerce_check_id(f) }, m.{_fmt_measure_range(ms2, me2)} | parts: {', '.join(_coerce_parts_involved(f)) or '?'}) "
                f"— score {c.score_total:.2f}"
            )
        lines.append("")

    # Findings table
    lines.append("## Findings Table\n")
    lines.append("| Sev | Check | Measures | Parts | Label |")
    lines.append("|---|---|---|---|---|")
    for f in sorted(findings, key=_finding_sort_key):
        ms2, me2 = _measure_span(f)
        parts_involved = ", ".join(_coerce_parts_involved(f)) or "?"
        lines.append(
            f"| {_severity_icon(f.severity)} {f.severity.value} | `{_coerce_check_id(f)}` | { _fmt_measure_range(ms2, me2) } | {parts_involved} | {_coerce_short_label(f)} |"
        )
    lines.append("")

    # Detailed cards
    lines.append("## Detailed Findings\n")
    for f in sorted(findings, key=_finding_sort_key):
        ms2, me2 = _measure_span(f)
        icon = _severity_icon(f.severity)
        title = f.short_label or f.message
        lines.append(f"### {icon} {title} (measures { _fmt_measure_range(ms2, me2) })")

        lines.append(f"**What I saw:** {f.evidence}")

        why = f.why_text or "Pending per-check WHY template (will be filled when checks are upgraded)."
        lines.append(f"**Why it matters:** {why}")

        lines.append("**Top fixes (ranked):**")
        if f.fix_candidates:
            top3 = sorted(f.fix_candidates, key=lambda c: (-c.score_total, c.title))[:3]
            for idx, cand in enumerate(top3, start=1):
                label = "Best move" if idx == 1 else ("Second best" if idx == 2 else "Third best")
                lines.append(f"{idx}) **{label}:** {cand.title}")
                for ln in _fmt_candidate(cand):
                    lines.append(f"   {ln}")
        else:
            # Back-compat: show legacy suggestion if no candidates yet
            if f.suggestion:
                lines.append(f"1) **Best move:** {f.suggestion}")
                lines.append("   - Expected impact: (pending scored simulation)")
                lines.append("   - Tradeoffs: (pending)")
                lines.append("   - Confidence: Med")
            else:
                lines.append("1) **Best move:** (pending candidate generation + scoring)")
        if f.so_what_text:
            lines.append(f"**So what:** {f.so_what_text}")

        ref = _pick_reference(f.references)
        if ref:
            lines.append(f"**Reference:** {ref.book} ({ref.edition}), p.{ref.page}. “{ref.excerpt}”")
        else:
            lines.append("**Reference:** (citation pending)")
        lines.append("")
    return "\n".join(lines)


def render_json(score: Score, findings: List[Finding]) -> Dict:
    return {
        "summary": {
            "parts_detected": [p.id for p in score.parts],
            "total_note_events": sum(len(p.events) for p in score.parts),
            "total_findings": len(findings),
            "tempo_bpm": score.tempo_bpm,
        },
        "findings": [
            {
                "id": f.id,
                "check_id": _coerce_check_id(f),
                "severity": f.severity.value,
                "part": f.part_id,
                "measure": f.measure,
                "measure_start": f.measure_start,
                "measure_end": f.measure_end,
                "parts_involved": _coerce_parts_involved(f),
                "time_beats": f.time_beats,
                "time_seconds": f.time_seconds,
                "message": f.message,
                "evidence": f.evidence,
                "evidence_structured": f.evidence_structured,
                "why_text": f.why_text,
                "so_what_text": f.so_what_text,
                "suggestion": f.suggestion,
                "fix_candidates": [
                    {
                        "title": c.title,
                        "steps": c.steps,
                        "expected_effect": c.expected_effect,
                        "tradeoffs": c.tradeoffs,
                        "confidence": c.confidence.value if hasattr(c.confidence, "value") else str(c.confidence),
                        "score_total": c.score_total,
                        "score_breakdown": c.score_breakdown.__dict__,
                    }
                    for c in (f.fix_candidates or [])
                ],
                "references": [
                    {
                        "book": r.book,
                        "edition": r.edition,
                        "page": r.page,
                        "excerpt": r.excerpt,
                        "url": r.url,
                        "concept": r.concept,
                    }
                    for r in (f.references or [])
                ],
            }
            for f in findings
        ],
    }
