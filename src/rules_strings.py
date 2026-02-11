# Strings v1 rules (WRITTEN pitch MIDI numbers)
# C4 = 60. Contrabass sounds 8ve lower, but we validate written pitch.

PART_ORDER = ["vln1", "vln2", "vla", "vc", "cb"]

RANGES = {
    "vln1": (55, 105),  # G3 - A7
    "vln2": (55, 103),  # G3 - G7
    "vla":  (48, 88),   # C3 - E6
    "vc":   (36, 76),   # C2 - E5
    "cb":   (40, 79),   # E2 - G5 (written; sounds E1 - G4)
}

CONGESTION_DENSITY = 4       # parts sounding
CONGESTION_SPAN_MAX = 12     # semitones (<= 1 octave)
DUPLICATION_INTERVALS = {0, 12, 24}  # unison, octave, 2 octaves
