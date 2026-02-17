# src/orch_auditor/checks/__init__.py
from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Optional, Set

from ..config import Config
from ..model import Finding, Score

from .range_check import run_range_check
from .crossing_check import run_crossing_check
from .overlap_check import run_overlap_check
from .extreme_register_check import run_extreme_register_check
from .spacing_check import run_spacing_check
from .density_check import run_density_check
from .congestion_check import run_congestion_check
from .doubling_check import run_doubling_check
from .chords_check import run_chords_check
from .leaps_check import run_leaps_check


CheckFn = Callable[[Score, Config], List[Finding]]

CHECKS: Dict[str, CheckFn] = {
    "range": run_range_check,
    "crossing": run_crossing_check,
    "overlap": run_overlap_check,
    "extreme_register": run_extreme_register_check,
    "spacing": run_spacing_check,
    "density": run_density_check,
    "congestion": run_congestion_check,
    "doubling": run_doubling_check,
    "chords": run_chords_check,
    "leaps": run_leaps_check,
}


def run_enabled_checks(
    score: Score,
    config: Config,
    only: Optional[Iterable[str]] = None,
    disable: Optional[Iterable[str]] = None,
) -> List[Finding]:
    enabled = list(config.get_enabled_checks()) or list(CHECKS.keys())

    if only:
        only_set: Set[str] = set(only)
        enabled = [c for c in enabled if c in only_set]

    if disable:
        disable_set: Set[str] = set(disable)
        enabled = [c for c in enabled if c not in disable_set]

    findings: List[Finding] = []
    for check_name in enabled:
        fn = CHECKS.get(check_name)
        if not fn:
            continue
        findings.extend(fn(score, config))

    return findings
