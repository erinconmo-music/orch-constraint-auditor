import json
import collections
import pathlib


MD_PATH = pathlib.Path("runs/tmp/outputs/report.md")
OUT_PATH = pathlib.Path("runs/tmp/outputs/metrics.json")


def parse_findings_table(md_lines: list[str]) -> list[dict]:
    rows: list[dict] = []
    for ln in md_lines:
        if not ln.startswith("|"):
            continue
        if ("WARN" not in ln and "ERROR" not in ln and "INFO" not in ln):
            continue
        if "`" not in ln:
            continue

        cols = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cols) < 5:
            continue

        check = cols[1]
        if not (check.startswith("`") and check.endswith("`")):
            continue

        rows.append(
            {
                "sev": cols[0].split()[-1],   # e.g., "WARN"
                "check": check.strip("`"),    # e.g., CHORDS_TOO_MANY_NOTES
                "measures": cols[2],          # keep raw (may be "1" or "1–3" or "?")
                "parts": cols[3],
                "label": cols[4],
            }
        )
    return rows


def main() -> None:
    if not MD_PATH.exists():
        raise FileNotFoundError(f"Missing markdown report: {MD_PATH}")

    md_lines = MD_PATH.read_text(encoding="utf-8").splitlines()
    rows = parse_findings_table(md_lines)

    sev = collections.Counter(r["sev"] for r in rows)
    chk = collections.Counter(r["check"] for r in rows)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_md": str(MD_PATH),
        "n_rows": len(rows),
        "severity": dict(sev),
        "top_checks": chk.most_common(10),
        "sample_rows": rows[:20],
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"OK -> {OUT_PATH}")
    print("severity:", dict(sev))
    print("top_checks:", chk.most_common(5))


if __name__ == "__main__":
    main()
