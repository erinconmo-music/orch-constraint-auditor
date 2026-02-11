from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class Issue:
    kind: str
    when: str
    details: str

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
