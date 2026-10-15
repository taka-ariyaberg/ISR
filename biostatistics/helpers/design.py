"""The study design in one place: factor levels, their order, and the outcomes.

Everything else (cleaning, models, tables, figures) reads the design from here,
so a level can never be spelled or ordered differently in two places.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

# The first level of each factor is the reference: normotensive strain, the
# sex used in the original study, and the control treatment.
LEVELS: dict[str, tuple[str, str]] = {
    "strain": ("Wistar", "SHR"),
    "sex": ("Male", "Female"),
    "treatment": ("Vehicle", "Rapamycin"),
}
FACTORS: tuple[str, ...] = tuple(LEVELS)

# The eight experimental groups, in the fixed order used by every table and figure.
CELLS: tuple[tuple[str, str, str], ...] = tuple(itertools.product(*LEVELS.values()))

# The four strain x sex subgroups within which rapamycin is compared to vehicle.
SUBGROUPS: tuple[tuple[str, str], ...] = tuple(
    itertools.product(LEVELS["strain"], LEVELS["sex"])
)

N_PER_CELL = 8
N_TOTAL = N_PER_CELL * len(CELLS)

# Occlusion was confirmed by a drop of at least 70% at the core probe (Beard et al. 2020).
OCCLUSION_THRESHOLD = -70.0


def group_label(cell: tuple[str, ...]) -> str:
    """Human-readable label for a group, e.g. 'Wistar · Male · Vehicle'."""
    return " · ".join(cell)


GROUP_LABELS: tuple[str, ...] = tuple(group_label(c) for c in CELLS)
SUBGROUP_LABELS: tuple[str, ...] = tuple(group_label(s) for s in SUBGROUPS)


@dataclass(frozen=True)
class Outcome:
    """One analysed outcome and how to talk about it.

    Attributes:
        column: Column name in the clean dataset.
        name: Short display name used in titles and tables.
        unit: Unit of the measurement itself.
        diff_unit: Unit of a difference between two groups. For percentages this
            is percentage points (pp), not percent.
        axis_label: y-axis label for plots of the raw values.
        relative: Whether to also express rapamycin effects as a percentage of
            the vehicle mean. Only meaningful for a ratio-scale quantity like a
            volume, not for a value that is already a percentage change.
        direction: What a negative and a positive group difference mean, used
            to label the two ends of effect axes.
        reference: Optional horizontal reference line (value, label) for plots
            of the raw values, e.g. the occlusion threshold for core CBF.
    """

    column: str
    name: str
    unit: str
    diff_unit: str
    axis_label: str
    relative: bool
    direction: tuple[str, str]
    reference: tuple[float, str] | None = None


# Ordered along the causal story: how severe the ischaemia was (core), how much
# the collaterals compensated, and how much tissue was lost.
OUTCOMES: tuple[Outcome, ...] = (
    Outcome("cbf_probe1_pct", "Core CBF (probe 1)", "% change from baseline", "pp",
            "CBF change from baseline (%)", relative=False,
            direction=("larger flow drop", "smaller flow drop"),
            reference=(OCCLUSION_THRESHOLD, "occlusion threshold, −70 %")),
    Outcome("cbf_probe2_pct", "Collateral CBF (probe 2)", "% change from baseline", "pp",
            "CBF change from baseline (%)", relative=False,
            direction=("larger flow drop", "smaller flow drop")),
    Outcome("infarct_mm3", "Infarct volume", "mm³", "mm³",
            "Infarct volume at 24 h (mm³)", relative=True,
            direction=("smaller infarct", "larger infarct")),
)
OUTCOME_BY_COLUMN: dict[str, Outcome] = {o.column: o for o in OUTCOMES}

# ANOVA terms: display label and what the 1-df estimate means, in words.
# Differences are always second level minus first level (SHR - Wistar,
# Female - Male, Rapamycin - Vehicle), which fixes the sign of every estimate.
TERMS: dict[tuple[str, ...], tuple[str, str]] = {
    ("strain",): ("Strain", "SHR − Wistar"),
    ("sex",): ("Sex", "Female − Male"),
    ("treatment",): ("Treatment", "Rapamycin − Vehicle"),
    ("strain", "sex"): ("Strain × Sex", "sex difference in SHR minus in Wistar"),
    ("strain", "treatment"): ("Strain × Treatment", "rapamycin effect in SHR minus in Wistar"),
    ("sex", "treatment"): ("Sex × Treatment", "rapamycin effect in females minus in males"),
    ("strain", "sex", "treatment"): (
        "Strain × Sex × Treatment",
        "Sex × Treatment interaction in SHR minus in Wistar",
    ),
}
TERM_ORDER: tuple[str, ...] = tuple(label for label, _ in TERMS.values())
