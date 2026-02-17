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

# Additional melodic / tessitura checks
# "Comfortable" high register (approx.) for sustained notes.
# Anything clearly above this, held for LONG_NOTE_MIN_QL or more, is flagged.
COMFORTABLE_HI = {
    "vln1": 100,  # around E7
    "vln2": 98,   # around D7
    "vla":  84,   # around C6
    "vc":   72,   # around C5
    "cb":   67,   # around G4 (written)
}

# Minimum duration (in quarter lengths) to consider a note "sustained"
LONG_NOTE_MIN_QL = 2.0

# Interval (in semitones) above which melodic leaps are flagged
# (e.g., > 12 = larger than an octave)
LARGE_LEAP_INTERVAL_MIN = 13
