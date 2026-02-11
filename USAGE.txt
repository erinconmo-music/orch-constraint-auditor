How to use — Orchestration Constraint Auditor (Strings v1)
This repository validates basic orchestration constraints from a MusicXML file and generates a Markdown report.
1) Requirements (Mac)
Python installed


This repo cloned locally


A virtual environment already created in the repo (.venv)


MusicXML exported from notation software (recommended)


If you already set up the repo once, you only need to activate the environment and run the script.
2) Recommended input format
✅ Preferred: name.musicxml (MusicXML)
 Also accepted: .xml (MusicXML) and .mid/.midi (less reliable for part names)
Correct extension is name.musicxml (not .musxml).
3) Export recommendations (Sibelius / Finale / Dorico / MuseScore)
A) Keep a clean 5-part strings score
This tool assumes a reduced strings template:
Violin I


Violin II


Viola


Violoncello (Cello)


Contrabass (Double Bass)


B) Use clear instrument/part names
The tool identifies parts mainly by part names / instrument names found in the MusicXML.
Recommended names (exact or very similar):
Violin I / Violin 1


Violin II / Violin 2


Viola


Violoncello / Cello


Contrabass / Double Bass / Contrabajo


Avoid ambiguous labels like “Strings”, “Staff 1”, “Pizz”, etc.
C) Export as plain MusicXML (not compressed)
If your software offers “compressed MusicXML”, avoid it and export standard MusicXML.
D) Vertical score (recommended)
A vertical score (all parts aligned) improves the quality of vertical checks (overlap/crossing/density).
4) First-time setup (only once)
Open Terminal and run:
cd "$HOME/Projects/orch-constraint-auditor"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

5) Daily usage (every time you run it)
Step 1 — Go to the repo
cd "$HOME/Projects/orch-constraint-auditor"

Step 2 — Activate the environment
source .venv/bin/activate

Step 3 — Run the validator
 Example (input file on Desktop):
python src/validate_orch.py ~/Desktop/name.musicxml --out outputs/report.md

Step 4 — Open the report
open outputs/report.md

6) Output
A Markdown report is generated, containing:
Summary (parts detected, note events, total issues)


Counts by issue type


Issue details with musical location (measure/beat when available)


7) What the tool checks (Strings v1)
Range per instrument (written pitch / score pitch)


Crossing between adjacent parts (error)


Overlap between adjacent parts (warning)


Density / congestion (many parts in a narrow register)


Duplication (unison/octaves / double-octaves)


Note: Validation uses written pitch. Contrabass is evaluated by written range (it sounds one octave lower).
8) Troubleshooting
A) “Parts detected” is missing something
 Fix the part names in your notation software:
Make sure each staff has an instrument assigned (not just a label)


Use standard names like “Violin I/II, Viola, Violoncello, Contrabass”


Re-export the MusicXML and run again


B) MusicXML entity errors (rare)
 If parsing fails due to weird entities, re-export MusicXML from the notation software.
 If needed, you can search the file for suspicious entities:
grep -oE "&[a-zA-Z]+;" name.musicxml | sort | uniq | head -50

C) Report not created
 Make sure you are running inside the repo and using the correct paths:
pwd
ls examples
ls outputs

9) Suggested file naming convention
Use consistent names for inputs and outputs:
Input: project_piece_version.musicxml


Output: project_piece_version_report.md


Example:
python src/validate_orch.py ~/Desktop/psalm23_v3.musicxml --out outputs/psalm23_v3_report.md
open outputs/psalm23_v3_report.md

