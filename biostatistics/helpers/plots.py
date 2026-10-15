"""Figure style and one function per figure type.

The figures follow the conventions of journals in this field (e.g. *Stroke*,
*JCBFM*): sized to print width (7.2 in = 183 mm, double column), Arial at
7–8 pt, thin black axes with outward ticks, no gridlines, bold panel letters,
and no title inside the figure (the caption carries it). Every figure is saved
as a 600 dpi PNG and as vector SVG and PDF.

Colour carries exactly one meaning across every figure: **blue is rapamycin,
grey is vehicle**. Strain and sex are shown by position and labels, never by
colour. The one exception is the pairwise heatmap, which encodes a signed
difference and therefore uses a separate violet–orange diverging scale, so
blue never means anything else. The blue/grey pair was checked with a
colour-vision-deficiency validator (simulated protanopia/deuteranopia
separation ΔE 15.9; contrast ≥ 3:1).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm, to_rgb
from matplotlib.lines import Line2D
from matplotlib.transforms import ScaledTranslation, blended_transform_factory
from scipy import stats as sps

from .design import GROUP_LABELS, LEVELS, OCCLUSION_THRESHOLD, OUTCOMES, Outcome
from .report import num

# --------------------------------------------------------------------------- #
# Palette, sizes and style
# --------------------------------------------------------------------------- #

SURFACE = "#ffffff"   # figure background (white, as in print)
INK = "#1a1a1a"       # axes, text, summary marks
INK_2 = "#555555"     # secondary text
MUTED = "#8c8c8c"     # tertiary text, de-emphasised marks
REF = "#9e9e9e"       # dashed reference lines (zero, thresholds)

RAPAMYCIN = "#2a78d6"
RAPAMYCIN_DARK = "#1c5cab"   # same hue, one step darker: pooled estimates
VEHICLE = "#898781"
TREATMENT_COLORS = {"Vehicle": VEHICLE, "Rapamycin": RAPAMYCIN}

# Diverging scale for signed differences: violet and orange poles (cool and warm),
# neutral grey middle. Deliberately not blue, which is reserved for rapamycin.
DIVERGING = LinearSegmentedColormap.from_list("violet_neutral_orange", ["#4a3aa7", "#f0efec", "#eb6834"])

DOUBLE = 7.2   # double-column width in inches (183 mm)
DASH = (0, (3, 2))


def set_style() -> None:
    """Apply the journal figure style to matplotlib."""
    mpl.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 7.5, "text.color": INK,
        "axes.titlesize": 8, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 5,
        "axes.labelsize": 7.5, "axes.labelcolor": INK, "axes.edgecolor": INK, "axes.linewidth": 0.6,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
        "xtick.color": INK, "ytick.color": INK, "xtick.labelsize": 7, "ytick.labelsize": 7,
        "xtick.direction": "out", "ytick.direction": "out",
        "xtick.major.size": 2.8, "ytick.major.size": 2.8, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.major.pad": 2.2, "ytick.major.pad": 2.2,
        "legend.frameon": False, "legend.fontsize": 7, "legend.handletextpad": 0.3,
        "legend.columnspacing": 1.2, "legend.handlelength": 1.4, "legend.borderaxespad": 0.2,
        "lines.linewidth": 1.0, "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
        "errorbar.capsize": 2,
        "figure.dpi": 150, "savefig.dpi": 600, "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
        "svg.fonttype": "none", "pdf.fonttype": 42,
    })


def save(fig, folder: Path, stem: str) -> list[Path]:
    """Save a figure as PNG (600 dpi, for slides) and as SVG and PDF (vector, for posters and journals)."""
    paths = [folder / f"{stem}.{ext}" for ext in ("png", "svg", "pdf")]
    for path in paths:
        fig.savefig(path)
    return paths


def _figure(nrows: int, ncols: int, height: float, **kwargs):
    fig, axes = plt.subplots(nrows, ncols, figsize=(DOUBLE, height), layout="constrained", **kwargs)
    fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.04, hspace=0.06)
    return fig, axes


def letter(ax, text: str, dx: float = -26, dy: float = 4) -> None:
    """Bold panel letter at the top-left of a panel, offset in points."""
    offset = ScaledTranslation(dx / 72, dy / 72, ax.figure.dpi_scale_trans)
    ax.text(0, 1, text, transform=ax.transAxes + offset, fontsize=10, fontweight="bold",
            ha="left", va="bottom", color=INK)


def _treatment_handles(summary_label: str | None = None) -> list[Line2D]:
    handles = [Line2D([], [], ls="none", marker="o", markersize=4.5, markerfacecolor=TREATMENT_COLORS[t],
                      markeredgecolor=SURFACE, markeredgewidth=0.4, label=t) for t in LEVELS["treatment"]]
    if summary_label:
        handles.append(Line2D([], [], color=INK, lw=1.1, label=summary_label))
    return handles


def stars(p: float) -> str:
    """Conventional significance marks: *** < 0.001, ** < 0.01, * < 0.05, ns otherwise."""
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"


def _relative_luminance(color) -> float:
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in to_rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# --------------------------------------------------------------------------- #
# Individual animals by group (Figures 1 and 7)
# --------------------------------------------------------------------------- #

# x position of each strain × sex subgroup (a wider gap separates the two strains)
SUBGROUP_X = {("Wistar", "Male"): 0.0, ("Wistar", "Female"): 1.0,
              ("SHR", "Male"): 2.35, ("SHR", "Female"): 3.35}
TREATMENT_DX = {"Vehicle": -0.22, "Rapamycin": 0.22}
OUTWARD = {"Vehicle": -1, "Rapamycin": 1}   # side each cloud prefers to spread to


def swarm(values: np.ndarray, center: float, step: float, dy: float, direction: int = 0) -> np.ndarray:
    """Deterministic beeswarm: nudge points sideways only where they would overlap.

    Points are placed from lowest to highest value at the first free slot.
    ``direction`` 0 alternates sides (0, +1, −1, +2, ...); +1 or −1 alternates
    but tries that side first, which keeps neighbouring clouds apart. Two
    points collide when closer than one step horizontally and ``dy``
    vertically. No randomness, so the figure is identical on every run.
    """
    first = direction or 1
    slots = [0] + [s for k in range(1, 12) for s in (first * k, -first * k)]
    xs = np.empty(len(values))
    placed: list[tuple[float, float]] = []
    for i in np.argsort(values, kind="stable"):
        y = values[i]
        for slot in slots:
            x = center + slot * step
            if all(((x - px) / step) ** 2 + ((y - py) / dy) ** 2 >= 1 for px, py in placed):
                break
        placed.append((x, y))
        xs[i] = x
    return xs


def plot_individuals(ax, data: pd.DataFrame, outcome: Outcome, effects: pd.DataFrame | None = None) -> None:
    """Every animal as a dot with the group mean ± SD, optionally with significance brackets."""
    col = outcome.column
    values = data[col].to_numpy(float)
    span = values.max() - values.min()

    for (strain, sex), x0 in SUBGROUP_X.items():
        in_sub = (data["strain"] == strain) & (data["sex"] == sex)
        for treatment, dx in TREATMENT_DX.items():
            y = data.loc[in_sub & (data["treatment"] == treatment), col].to_numpy(float)
            xs = swarm(y, x0 + dx, step=0.105, dy=0.03 * span, direction=OUTWARD[treatment])
            ax.scatter(xs, y, s=11, color=TREATMENT_COLORS[treatment], edgecolor=SURFACE,
                       linewidth=0.35, zorder=3)
            m, sd = y.mean(), y.std(ddof=1)
            ax.plot([x0 + dx - 0.14, x0 + dx + 0.14], [m, m], color=INK, lw=1.2,
                    solid_capstyle="butt", zorder=4)
            ax.errorbar(x0 + dx, m, yerr=sd, fmt="none", ecolor=INK, elinewidth=0.7,
                        capsize=2, capthick=0.7, zorder=4)

        if effects is not None:
            row = effects[(effects["strain"] == strain) & (effects["sex"] == sex)].iloc[0]
            y_bar = data.loc[in_sub, col].max() + 0.07 * span
            left, right = x0 + TREATMENT_DX["Vehicle"], x0 + TREATMENT_DX["Rapamycin"]
            ax.plot([left, left, right, right], [y_bar - 0.025 * span, y_bar, y_bar, y_bar - 0.025 * span],
                    color=INK, lw=0.6)
            mark = stars(row["p_sidak"])
            ax.text(x0, y_bar + (0.0 if mark != "ns" else 0.012) * span, mark, ha="center", va="bottom",
                    fontsize=8 if mark != "ns" else 6.5, color=INK)

    if outcome.reference is not None:
        value, label = outcome.reference
        ax.axhline(value, color=REF, lw=0.6, ls=DASH, zorder=1)
        ax.text(3.9, value + 0.012 * span, label, ha="right", va="bottom", fontsize=6, color=INK_2)

    ax.set_xticks(list(SUBGROUP_X.values()), [sex for _, sex in SUBGROUP_X])
    trans = blended_transform_factory(ax.transData, ax.transAxes)
    for strain in LEVELS["strain"]:
        xs = [x for (s, _), x in SUBGROUP_X.items() if s == strain]
        ax.plot([min(xs) - 0.42, max(xs) + 0.42], [-0.115, -0.115], transform=trans, color=INK,
                lw=0.6, clip_on=False)
        ax.text(np.mean(xs), -0.135, strain, transform=trans, ha="center", va="top",
                fontsize=7.5, fontweight="bold", color=INK)
    ax.tick_params(axis="x", length=0)
    ax.set_xlim(-0.6, 3.95)
    headroom = 0.2 if effects is not None else 0.08
    ax.set_ylim(values.min() - 0.08 * span, values.max() + headroom * span)
    ax.set_ylabel(outcome.axis_label)
    ax.set_title(outcome.name)


def figure_individuals(data: pd.DataFrame, effects: dict[str, pd.DataFrame], note: str | None = None):
    """One panel per outcome: all 64 animals by strain, sex and treatment.

    ``note`` is printed under the panels, e.g. to say how the p-values were adjusted.
    """
    fig, axes = _figure(1, 3, 2.75)
    for ax, outcome, tag in zip(axes, OUTCOMES, "ABC"):
        plot_individuals(ax, data, outcome, effects.get(outcome.column))
        letter(ax, tag)
    fig.legend(handles=_treatment_handles("Mean ± SD"), loc="outside upper center", ncol=3)
    if note:
        fig.supxlabel(note, fontsize=6.5, color=INK_2)
    return fig


# --------------------------------------------------------------------------- #
# Probe check (Figure 2)
# --------------------------------------------------------------------------- #

def figure_probe_check(data: pd.DataFrame):
    """Each animal's two probe readings joined by a line, one panel per strain."""
    fig, axes = plt.subplots(1, 2, figsize=(4.8, 2.6), sharey=True, layout="constrained")
    fig.get_layout_engine().set(w_pad=0.03, h_pad=0.03, wspace=0.06)
    for ax, strain, tag in zip(axes, LEVELS["strain"], "AB"):
        sub = data[data["strain"] == strain]
        for p1, p2 in zip(sub["cbf_probe1_pct"], sub["cbf_probe2_pct"]):
            ax.plot([0, 1], [p1, p2], color=MUTED, lw=0.5, alpha=0.4, zorder=2)
        m1, m2 = sub["cbf_probe1_pct"].mean(), sub["cbf_probe2_pct"].mean()
        ax.plot([0, 1], [m1, m2], color=INK, lw=1.5, marker="o", markersize=4.5,
                markeredgecolor=SURFACE, markeredgewidth=0.6, zorder=3)
        ax.text(-0.07, m1, num(m1), ha="right", va="center", fontsize=7, color=INK)
        ax.text(1.07, m2, num(m2), ha="left", va="center", fontsize=7, color=INK)
        ax.axhline(OCCLUSION_THRESHOLD, color=REF, lw=0.6, ls=DASH, zorder=1)
        ax.text(1.38, OCCLUSION_THRESHOLD + 1.2, "−70 % threshold", ha="right", va="bottom",
                fontsize=6, color=INK_2)
        ax.set_xticks([0, 1], ["Probe 1\n(MCA core)", "Probe 2\n(collateral)"])
        ax.tick_params(axis="x", length=0)
        ax.set_xlim(-0.42, 1.42)
        ax.set_title(f"{strain} (n = {len(sub)})")
        letter(ax, tag, dx=-22 if tag == "A" else -14)
    axes[0].set_ylabel("CBF change from baseline (%)")
    return fig


# --------------------------------------------------------------------------- #
# Model diagnostics (Figure 3)
# --------------------------------------------------------------------------- #

def figure_diagnostics(models: dict, checks: dict[str, dict]):
    """Q–Q plot and residuals-versus-fitted plot for each outcome's model."""
    fig, axes = _figure(2, 3, 4.4)
    for j, outcome in enumerate(OUTCOMES):
        model = models[outcome.column]
        r = model.get_influence().resid_studentized_external  # same residuals as the checks table
        (theoretical, ordered), _ = sps.probplot(r, dist="norm")
        chk = checks[outcome.column]

        ax = axes[0, j]
        lim = 1.1 * max(np.abs(theoretical).max(), np.abs(ordered).max())
        ax.plot([-lim, lim], [-lim, lim], color=REF, lw=0.7, ls=DASH, zorder=1)
        ax.scatter(theoretical, ordered, s=8, color=INK_2, edgecolor=SURFACE, linewidth=0.3, zorder=2)
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_title(outcome.name)
        ax.set_xlabel("Theoretical normal quantile")
        ax.set_ylabel("Studentised residual")
        ax.text(0.97, 0.04, f"Shapiro–Wilk p = {chk['shapiro_p']:.2f}", transform=ax.transAxes,
                ha="right", va="bottom", fontsize=6.5, color=INK_2)
        letter(ax, "ABC"[j])

        ax = axes[1, j]
        ax.axhline(0, color=REF, lw=0.7, ls=DASH, zorder=1)
        ax.scatter(model.fittedvalues, r, s=8, color=INK_2, edgecolor=SURFACE, linewidth=0.3, zorder=2)
        ax.set_xlabel(f"Fitted value (group mean)\nBrown–Forsythe p = {chk['brown_forsythe_p']:.2f}")
        ax.set_ylabel("Studentised residual")
        letter(ax, "DEF"[j])
    return fig


# --------------------------------------------------------------------------- #
# ANOVA effect sizes (Figure 4)
# --------------------------------------------------------------------------- #

_VERDICT_MARK = {
    "clear": dict(face=INK, edge=INK, line=INK, label="Significant after Holm correction"),
    "suggestive": dict(face=SURFACE, edge=INK, line=INK, label="Significant before correction only"),
    "not significant": dict(face=SURFACE, edge=MUTED, line=MUTED, label="Not significant"),
}


def figure_effect_sizes(anova_tables: dict[str, pd.DataFrame]):
    """Partial η² with 95% CI for every ANOVA term, one panel per outcome."""
    fig, axes = _figure(1, 3, 2.6, sharey=True)
    for ax, outcome, tag in zip(axes, OUTCOMES, "ABC"):
        t = anova_tables[outcome.column]
        ys = np.arange(len(t))
        ax.axvline(0.14, color=REF, lw=0.6, ls=DASH, zorder=0)
        ax.text(0.15, -0.75, "large (0.14)", ha="left", va="center", fontsize=6, color=INK_2)
        for y, (_, r) in zip(ys, t.iterrows()):
            mark = _VERDICT_MARK[r["verdict"]]
            ax.plot([r["pes_ci_low"], r["pes_ci_high"]], [y, y], color=mark["line"], lw=1.0, zorder=2)
            ax.scatter(r["partial_eta_sq"], y, s=22, facecolor=mark["face"], edgecolor=mark["edge"],
                       linewidth=0.9, zorder=3)
        ax.set_yticks(ys, t["term"])
        ax.tick_params(axis="y", length=0)
        ax.set_ylim(len(t) - 0.4, -1.1)
        ax.set_xlim(0, 0.8)
        ax.set_xlabel("Partial η² (95 % CI)")
        ax.set_title(outcome.name)
        letter(ax, tag, dx=-14 if tag != "A" else -96)
    handles = [Line2D([], [], ls="none", marker="o", markersize=5, markerfacecolor=m["face"],
                      markeredgecolor=m["edge"], markeredgewidth=0.9, label=m["label"])
               for m in _VERDICT_MARK.values()]
    fig.legend(handles=handles, loc="outside upper center", ncol=3)
    return fig


# --------------------------------------------------------------------------- #
# Interaction plots (Figure 5)
# --------------------------------------------------------------------------- #

def figure_interactions(cell_cis: dict[str, pd.DataFrame]):
    """Group means (95% CI) by strain, with one panel row per sex.

    Read it as: the vertical gap between blue and grey is the rapamycin effect.
    If the gap changes between Wistar and SHR, the effect depends on strain
    (a strain × treatment interaction); if the pattern differs between the two
    rows, sex modifies that dependence (a three-way interaction).
    """
    fig, axes = _figure(2, 3, 4.3, sharex=True, sharey="col")
    for i, sex in enumerate(LEVELS["sex"]):
        for j, outcome in enumerate(OUTCOMES):
            ax = axes[i, j]
            ci = cell_cis[outcome.column]
            for treatment, dx in (("Vehicle", -0.03), ("Rapamycin", 0.03)):
                rows = [ci.loc[(strain, sex, treatment)] for strain in LEVELS["strain"]]
                xs = np.arange(len(rows)) + dx
                means = np.array([r["mean"] for r in rows])
                low = np.array([r["ci_low"] for r in rows])
                high = np.array([r["ci_high"] for r in rows])
                color = TREATMENT_COLORS[treatment]
                ax.plot(xs, means, color=color, lw=1.3, zorder=2)
                ax.errorbar(xs, means, yerr=[means - low, high - means], fmt="o", color=color,
                            markersize=4, markeredgecolor=SURFACE, markeredgewidth=0.5,
                            elinewidth=0.8, capsize=2, capthick=0.8, zorder=3)
            ax.set_xticks([0, 1], LEVELS["strain"])
            ax.tick_params(axis="x", length=0)
            ax.set_xlim(-0.35, 1.35)
            ax.set_ylabel(outcome.axis_label)
            ax.set_title(f"{outcome.name}, {sex.lower()}s")
            letter(ax, "ABCDEF"[3 * i + j])
    fig.legend(handles=_treatment_handles("Mean with 95 % CI"), loc="outside upper center", ncol=3)
    return fig


# --------------------------------------------------------------------------- #
# Forest plot of rapamycin effects (Figure 6)
# --------------------------------------------------------------------------- #

_FOREST_ROWS = [(s, x) for s in LEVELS["strain"] for x in (*LEVELS["sex"], "Both sexes")]


def figure_forest(effects: dict[str, pd.DataFrame]):
    """Rapamycin minus vehicle with Šidák-simultaneous 95% CIs, one panel per outcome."""
    fig, axes = _figure(1, 3, 2.7, sharey=True)
    ys, labels, y = [], [], 0.0
    for idx, (strain, sex) in enumerate(_FOREST_ROWS):
        if idx and _FOREST_ROWS[idx - 1][0] != strain:
            y += 0.6  # gap between strains
        ys.append(y)
        labels.append(f"{strain} · {sex.lower() if sex == 'Both sexes' else sex}")
        y += 1.0

    for ax, outcome, tag in zip(axes, OUTCOMES, "ABC"):
        eff = effects[outcome.column].set_index(["strain", "sex"])
        ax.axvline(0, color=REF, lw=0.7, ls=DASH, zorder=1)
        for y, key in zip(ys, _FOREST_ROWS):
            r = eff.loc[key]
            pooled = key[1] == "Both sexes"
            color = RAPAMYCIN_DARK if pooled else RAPAMYCIN
            ax.plot([r["ci_low"], r["ci_high"]], [y, y], color=color, lw=1.6 if pooled else 1.0, zorder=2)
            ax.scatter(r["estimate"], y, marker="D" if pooled else "o", s=26 if pooled else 16,
                       color=color, edgecolor=SURFACE, linewidth=0.5, zorder=3)
        lo = min(effects[outcome.column]["ci_low"].min(), 0)
        hi = max(effects[outcome.column]["ci_high"].max(), 0)
        pad = 0.1 * (hi - lo)
        ax.set_xlim(lo - pad, hi + pad)
        ax.set_ylim(ys[-1] + 0.7, ys[0] - 0.7)
        ax.set_yticks(ys, labels)
        ax.tick_params(axis="y", length=0)
        for tick, (_, sex) in zip(ax.get_yticklabels(), _FOREST_ROWS):
            if sex == "Both sexes":
                tick.set_fontweight("bold")
        ax.set_xlabel(f"Rapamycin − vehicle ({outcome.diff_unit})\n"
                      f"← {outcome.direction[0]}      {outcome.direction[1]} →")
        ax.set_title(outcome.name)
        letter(ax, tag, dx=-14 if tag != "A" else -78)
    handles = [
        Line2D([], [], color=RAPAMYCIN, lw=1.0, marker="o", markersize=4, markeredgecolor=SURFACE,
               label="Strain × sex group (Šidák, 4 comparisons)"),
        Line2D([], [], color=RAPAMYCIN_DARK, lw=1.6, marker="D", markersize=4.5, markeredgecolor=SURFACE,
               label="Strain, sexes pooled (Šidák, 2 comparisons)"),
    ]
    fig.legend(handles=handles, loc="outside upper center", ncol=2)
    return fig


# --------------------------------------------------------------------------- #
# Tukey heatmaps (Figure 8)
# --------------------------------------------------------------------------- #

def _tukey_stars(p: float) -> str:
    mark = stars(p)
    return "" if mark == "ns" else mark


def figure_tukey(tukey_tables: dict[str, pd.DataFrame]):
    """Lower-triangle heatmaps of all pairwise differences (row minus column)."""
    k = len(GROUP_LABELS)
    index = {g: i for i, g in enumerate(GROUP_LABELS)}
    fig, axes = _figure(1, 3, 2.55)
    for j, (ax, outcome) in enumerate(zip(axes, OUTCOMES)):
        diff = np.full((k, k), np.nan)
        pval = np.full((k, k), np.nan)
        for _, r in tukey_tables[outcome.column].iterrows():
            a, b = index[r["group_1"]], index[r["group_2"]]
            row, col = max(a, b), min(a, b)
            # stored difference is group_2 − group_1; the cell shows row − column
            diff[row, col] = r["difference"] if b == row else -r["difference"]
            pval[row, col] = r["p_tukey"]
        vmax = np.nanmax(np.abs(diff))
        norm = TwoSlopeNorm(0, -vmax, vmax)
        mesh = ax.pcolormesh(np.ma.masked_invalid(diff), cmap=DIVERGING, norm=norm,
                             edgecolors=SURFACE, linewidth=1.2)
        for row in range(k):
            for col in range(row):
                s = _tukey_stars(pval[row, col])
                if s:
                    fill = DIVERGING(norm(diff[row, col]))
                    ax.text(col + 0.5, row + 0.5, s, ha="center", va="center", fontsize=6.5,
                            color="white" if _relative_luminance(fill) < 0.35 else INK)
        ax.set_xlim(0, k - 1)
        ax.set_ylim(k, 1)
        ax.set_aspect("equal")
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(length=0)
        ax.set_xticks(np.arange(k - 1) + 0.5, [str(i + 1) for i in range(k - 1)])
        ax.set_yticks(np.arange(1, k) + 0.5, [str(i + 1) for i in range(1, k)])
        ax.set_title(outcome.name)
        bar = fig.colorbar(mesh, ax=ax, shrink=0.72, pad=0.02, aspect=18)
        bar.outline.set_visible(False)
        bar.ax.tick_params(labelsize=6.5, width=0.5, length=2)
        bar.set_label(f"Row − column ({outcome.diff_unit})", fontsize=7)
        letter(ax, "ABC"[j], dx=-14)
    key = "   ".join(f"{i + 1} {g}" for i, g in enumerate(GROUP_LABELS))
    fig.supxlabel("Groups: " + key.replace("   5 ", "\n5 ") + "\n* p < 0.05   ** p < 0.01   *** p < 0.001 (Tukey HSD)",
                  fontsize=6.5, color=INK_2)
    return fig


# --------------------------------------------------------------------------- #
# CBF versus infarct (Figure 9)
# --------------------------------------------------------------------------- #

def figure_cbf_infarct(data: pd.DataFrame, corr: pd.DataFrame, x: str = "cbf_probe2_pct",
                       y: str = "infarct_mm3"):
    """Collateral CBF against infarct: all animals (A), then within groups only (B)."""
    fig, (ax_a, ax_b) = _figure(1, 2, 3.0)
    markers = {"Wistar": "o", "SHR": "^"}
    for strain, marker in markers.items():
        for treatment, color in TREATMENT_COLORS.items():
            sub = data[(data["strain"] == strain) & (data["treatment"] == treatment)]
            ax_a.scatter(sub[x], sub[y], marker=marker, s=18, color=color, edgecolor=SURFACE,
                         linewidth=0.4, zorder=3)
    overall = corr[corr["type"].str.startswith("Overall")].iloc[0]
    within = corr[corr["type"].str.startswith("Within")].iloc[0]
    ax_a.set_title("All animals")
    ax_a.text(0.03, 0.04, f"r = {num(overall['r'], 2)}, p < 0.001" if overall["p"] < 0.001
              else f"r = {num(overall['r'], 2)}, p = {overall['p']:.3f}",
              transform=ax_a.transAxes, fontsize=7, color=INK)
    ax_a.set_xlabel("Collateral CBF change from baseline (%)")
    ax_a.set_ylabel("Infarct volume at 24 h (mm³)")
    handles = [Line2D([], [], ls="none", marker="o", markersize=4.5, markerfacecolor=c, markeredgecolor=SURFACE,
                      label=t) for t, c in TREATMENT_COLORS.items()]
    handles += [Line2D([], [], ls="none", marker=m, markersize=4.5, markerfacecolor="none",
                       markeredgecolor=INK_2, markeredgewidth=0.7, label=s) for s, m in markers.items()]
    ax_a.legend(handles=handles, loc="upper right", ncol=2)
    letter(ax_a, "A")

    # Within-group association: deviations from each group's mean (Frisch–Waugh),
    # with the slope's 95% CI on n − k − 1 degrees of freedom.
    dx = (data[x] - data.groupby("group", observed=True)[x].transform("mean")).to_numpy(float)
    dy = (data[y] - data.groupby("group", observed=True)[y].transform("mean")).to_numpy(float)
    n, k = len(data), data["group"].nunique()
    slope = float(dx @ dy / (dx @ dx))
    resid_var = float(((dy - slope * dx) ** 2).sum() / (n - k - 1))
    se = np.sqrt(resid_var / (dx @ dx))
    t_crit = sps.t.ppf(0.975, n - k - 1)
    grid = np.linspace(dx.min(), dx.max(), 100)
    ax_b.fill_between(grid, (slope - t_crit * se) * grid, (slope + t_crit * se) * grid,
                      color=MUTED, alpha=0.18, linewidth=0, zorder=1)
    ax_b.axhline(0, color=REF, lw=0.6, ls=DASH, zorder=1)
    ax_b.axvline(0, color=REF, lw=0.6, ls=DASH, zorder=1)
    ax_b.scatter(dx, dy, s=12, color=INK_2, edgecolor=SURFACE, linewidth=0.35, zorder=3)
    ax_b.plot(grid, slope * grid, color=INK, lw=1.1, zorder=2)
    ax_b.set_title("Within groups (group means removed)")
    ax_b.text(0.03, 0.04, f"r = {num(within['r'], 2)}, p = {within['p']:.2f}", transform=ax_b.transAxes,
              fontsize=7, color=INK)
    ax_b.set_xlabel("Collateral CBF, difference from group mean (pp)")
    ax_b.set_ylabel("Infarct, difference from group mean (mm³)")
    letter(ax_b, "B")
    return fig
