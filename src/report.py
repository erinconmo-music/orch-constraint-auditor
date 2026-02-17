import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class Issue:
    kind: str
    when: str
    details: str
    # Optional rich fields (v1 upgrade, backward compatible)
    id: Optional[str] = None
    check_id: Optional[str] = None
    severity: Optional[str] = None  # e.g., "info"|"warning"|"error"
    parts: Optional[List[str]] = None
    location: Optional[Dict[str, Any]] = None  # {"measure":1,"beat":1.0,"offset":0.0}
    title: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None  # structured payload for later "stockfish" fixes
    why_text: Optional[str] = None
    so_what: Optional[str] = None
    # Keep JSON-serializable types (dicts, not nested dataclasses)
    fix_candidates: Optional[List[Dict[str, Any]]] = None  # [{description,score,score_breakdown,...}]
    references: Optional[List[Dict[str, Any]]] = None  # [{book,edition,page,excerpt,url}]

    def to_dict(self) -> Dict[str, Any]:
        # Always include core fields
        d: Dict[str, Any] = {
            "kind": self.kind,
            "when": self.when,
            "details": self.details,
        }
        # Include only non-null extras
        optional_fields = [
            ("id", self.id),
            ("check_id", self.check_id),
            ("severity", self.severity),
            ("parts", self.parts),
            ("location", self.location),
            ("title", self.title),
            ("evidence", self.evidence),
            ("why_text", self.why_text),
            ("so_what", self.so_what),
            ("fix_candidates", self.fix_candidates),
            ("references", self.references),
        ]
        for k, v in optional_fields:
            if v is not None:
                d[k] = v
        return d


def export_json(summary: Dict[str, Any], issues: List[Issue], path: str) -> None:
    data: Dict[str, Any] = {
        "run": {
            "tool": "orch-constraint-auditor",
            "version": "1.0",
        },
        "summary": dict(summary),
        "findings": [issue.to_dict() for issue in issues],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def render_markdown(summary: Dict[str, Any], issues: List[Issue]) -> str:
    lines = []
    lines.append("# Orchestration Constraint Report (Strings v1)\n")
    lines.append("## Summary\n")
    for k, v in summary.items():
        lines.append(f"- **{k}:** {v}")
    lines.append("\n## Issues\n")
    if not issues:
        lines.append("No issues found.\n")
        return "\n".join(lines)

    counts = {}
    for it in issues:
        counts[it.kind] = counts.get(it.kind, 0) + 1

    lines.append("### Counts\n")
    for k in sorted(counts.keys()):
        lines.append(f"- **{k}:** {counts[k]}")

    lines.append("\n### Details (first 60)\n")
    for it in issues[:60]:
        lines.append(f"- **{it.kind}** | {it.when} | {it.details}")

    lines.append("")
    return "\n".join(lines)
