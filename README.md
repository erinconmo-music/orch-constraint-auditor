# Orchestration Constraint Auditor (Strings v1)

Python tool to validate basic orchestration constraints from **MusicXML** (recommended) or **MIDI** and generate:
- a **Markdown report** (human-readable)
- a **JSON report** (machine-readable, for UI/metrics)

This repo targets *Strings v1* (Vln I, Vln II, Vla, Vc, Cb).

---

## Checks (v1)
- Instrument range per part (Vln I, Vln II, Vla, Vc, Cb)
- Crossing / overlap between adjacent parts
- Density / register congestion
- Unison/octave duplications
- Sustained high register warnings
- Large melodic leaps (warning)
---

## Install
```bash
python -m pip install -r requirements.txt
```

## Example output

```text
# Orchestration Constraint Report (Strings v1)

## Summary
- Parts detected: vln1, vln2, vla, vc, cb
- Total note events: 50
- Total issues: 5
- Checks: Range, Crossing/Overlap, Density/Congestion, Duplication, Sustained high register, Large leaps

## Counts
- Duplication: 2
- Overlap (warning): 3
```
