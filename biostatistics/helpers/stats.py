"""Statistical helpers: the three-way ANOVA, contrasts, effect sizes and checks.

Conventions used throughout:

- The data have one row per animal (the clean dataset from Section 3).
- Differences are always second level minus first level (SHR − Wistar,
  Female − Male, Rapamycin − Vehicle); see ``design.TERMS``.
- Contrasts are computed from the eight group means with the pooled residual
  variance of the full factorial model. That is exactly the error term the
  ANOVA uses, so every estimate here is on the same footing as the F-tests.
"""

from __future__ import annotations

import itertools
import re

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import optimize, stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.multitest import multipletests

from .design import CELLS, FACTORS, GROUP_LABELS, LEVELS, SUBGROUPS, TERMS, group_label

ALPHA = 0.05


# --------------------------------------------------------------------------- #
# The model
# --------------------------------------------------------------------------- #

def formula(outcome: str) -> str:
    """Full three-way factorial model with sum-to-zero ('effect') coding.

    Sum coding makes every Type III test a test of the unweighted group means,
    which is what the design asks about. With the default dummy coding, Type III
    'main effects' would silently become effects in the reference group only.
    """
    return f"{outcome} ~ C(strain, Sum) * C(sex, Sum) * C(treatment, Sum)"


def fit_factorial(data: pd.DataFrame, outcome: str):
    """Fit the three-way ANOVA model by ordinary least squares."""
    return smf.ols(formula(outcome), data=data).fit()


def term_key(name: str) -> tuple[str, ...]:
    """Factor names in a statsmodels term, e.g. 'C(strain, Sum):C(sex, Sum)' -> ('strain', 'sex')."""
    return tuple(re.findall(r"C\((\w+)", name))


def anova(model, typ: int = 3, robust: str | None = None) -> pd.DataFrame:
    """ANOVA table from statsmodels without the intercept row."""
    table = sm.stats.anova_lm(model, typ=typ, robust=robust)
    return table.drop(index="Intercept", errors="ignore")


# --------------------------------------------------------------------------- #
# Group means and contrasts
# --------------------------------------------------------------------------- #

def cell_summary(data: pd.DataFrame, outcome: str) -> pd.DataFrame:
    """Mean and n of each of the eight groups, in the fixed design order."""
    as_text = data.assign(**{f: data[f].astype(str) for f in FACTORS})
    summary = as_text.groupby(list(FACTORS))[outcome].agg(["mean", "count", "var"])
    return summary.reindex(pd.MultiIndex.from_tuples(CELLS, names=FACTORS))


def contrast(data: pd.DataFrame, outcome: str, weights: dict, mse: float,
             df_resid: float, crit: float | None = None, level: float = 0.95,
             variance: str = "pooled") -> dict:
    """Estimate a linear combination of group means, with its t-test and CI.

    Args:
        weights: Weight per group (a key of ``CELLS``); missing groups weigh 0.
        mse, df_resid: Residual mean square and degrees of freedom of the
            factorial model, i.e. the pooled within-group variance.
        crit: Critical t value for the interval. Defaults to the ordinary
            two-sided value for ``level``; pass a larger one for simultaneous
            (multiplicity-adjusted) intervals.
        variance: 'pooled' uses one shared variance (the ANOVA assumption).
            'hc3' lets every group keep its own variance: for a model of group
            means the HC3 variance of a group mean is s² / (n − 1), identical to
            statsmodels' HC3 covariance. The t reference keeps ``df_resid``.

    Returns:
        Dict with estimate, se, t, df, p (two-sided, unadjusted), ci_low, ci_high.
    """
    cells = cell_summary(data, outcome)
    w = np.array([weights.get(cell, 0.0) for cell in CELLS])
    means = cells["mean"].to_numpy(float)
    n = cells["count"].to_numpy(float)
    estimate = float(w @ means)
    if variance == "hc3":
        se = float(np.sqrt(np.sum(w**2 * cells["var"].to_numpy(float) / (n - 1))))
    elif variance == "pooled":
        se = float(np.sqrt(mse * np.sum(w**2 / n)))
    else:
        raise ValueError(f"variance must be 'pooled' or 'hc3', not {variance!r}")
    t = estimate / se
    p = float(2 * stats.t.sf(abs(t), df_resid))
    if crit is None:
        crit = stats.t.ppf(1 - (1 - level) / 2, df_resid)
    return {"estimate": estimate, "se": se, "t": t, "df": df_resid, "p": p,
            "ci_low": estimate - crit * se, "ci_high": estimate + crit * se}


def _sign(factor: str, level: str) -> float:
    return -1.0 if level == LEVELS[factor][0] else 1.0


def term_weights(key: tuple[str, ...]) -> dict:
    """Group weights that turn an ANOVA term into a 1-df difference.

    Each group gets the product of ±1 signs of the factors in the term, divided
    so that a main effect is a difference of two means, a two-way interaction a
    difference of two differences, and the three-way interaction a difference of
    two two-way interactions. The square of this contrast's t equals the term's F.
    """
    scale = 2 ** (len(FACTORS) - len(key))
    return {cell: np.prod([_sign(f, cell[FACTORS.index(f)]) for f in key]) / scale
            for cell in CELLS}


def treatment_weights(cells: list[tuple[str, str, str]]) -> dict:
    """Weights for 'rapamycin minus vehicle', averaged over the given groups."""
    rapa = [c for c in cells if c[2] == "Rapamycin"]
    veh = [c for c in cells if c[2] == "Vehicle"]
    return {**{c: 1 / len(rapa) for c in rapa}, **{c: -1 / len(veh) for c in veh}}


# --------------------------------------------------------------------------- #
# Effect sizes and multiplicity
# --------------------------------------------------------------------------- #

def _noncentrality(F: float, df1: float, df2: float, prob: float) -> float:
    """Noncentrality λ at which the observed F sits at cumulative probability ``prob``."""
    def gap(lam: float) -> float:
        cdf = stats.f.cdf(F, df1, df2) if lam == 0 else stats.ncf.cdf(F, df1, df2, lam)
        return cdf - prob

    if gap(0.0) <= 0:  # even with no effect the observed F is this extreme
        return 0.0
    upper = max(10.0, 4.0 * F * df1)
    while gap(upper) > 0:
        upper *= 2
    return optimize.brentq(gap, 0.0, upper, xtol=1e-10)


def partial_eta_squared_ci(F: float, df1: float, df2: float, level: float = 0.95) -> tuple[float, float]:
    """Confidence interval for partial η² by inverting the noncentral F distribution.

    This is the standard method (Steiger 2004), with λ converted to η² as
    λ / (λ + df1 + df2 + 1), as in the R package ``effectsize``.
    """
    tail = (1 - level) / 2
    total = df1 + df2 + 1
    lam_low = _noncentrality(F, df1, df2, 1 - tail)
    lam_high = _noncentrality(F, df1, df2, tail)
    return lam_low / (lam_low + total), lam_high / (lam_high + total)


def holm(p: pd.Series | np.ndarray) -> np.ndarray:
    """Holm step-down adjusted p-values (controls the family-wise error rate)."""
    return multipletests(np.asarray(p, float), method="holm")[1]


def sidak_p(p, k: int):
    """Šidák-adjusted p-value for one of k comparisons, computed without rounding loss."""
    return -np.expm1(k * np.log1p(-np.asarray(p, float)))


def sidak_level(alpha: float, k: int) -> float:
    """Per-comparison significance level that keeps the family-wise level at ``alpha``."""
    return -np.expm1(np.log1p(-alpha) / k)


def classify(p, p_adjusted, alpha: float = ALPHA) -> np.ndarray:
    """'clear' if significant after adjustment, 'suggestive' if only before, else 'not significant'."""
    p, p_adjusted = np.asarray(p, float), np.asarray(p_adjusted, float)
    return np.select([p_adjusted < alpha, p < alpha], ["clear", "suggestive"], "not significant")


# --------------------------------------------------------------------------- #
# The results tables used in the notebook
# --------------------------------------------------------------------------- #

def anova_table(data: pd.DataFrame, outcome: str, level: float = 0.95) -> pd.DataFrame:
    """Three-way ANOVA with an estimate, CI and partial η² (with CI) for every term.

    p-values are Type III with sum-to-zero coding. ``p_holm`` adjusts across the
    seven terms of this one ANOVA.
    """
    model = fit_factorial(data, outcome)
    table = anova(model)
    ss_res, df_res = table.loc["Residual", ["sum_sq", "df"]]
    rows = []
    for name, r in table.drop(index="Residual").iterrows():
        key = term_key(name)
        label, meaning = TERMS[key]
        est = contrast(data, outcome, term_weights(key), model.mse_resid, model.df_resid, level=level)
        pes_low, pes_high = partial_eta_squared_ci(r["F"], r["df"], df_res, level)
        rows.append({
            "term": label, "meaning": meaning,
            "estimate": est["estimate"], "ci_low": est["ci_low"], "ci_high": est["ci_high"],
            "df": int(r["df"]), "df_resid": int(df_res), "F": r["F"], "p": r["PR(>F)"],
            "partial_eta_sq": r["sum_sq"] / (r["sum_sq"] + ss_res),
            "pes_ci_low": pes_low, "pes_ci_high": pes_high,
        })
    out = pd.DataFrame(rows)
    out["p_holm"] = holm(out["p"])
    out["verdict"] = classify(out["p"], out["p_holm"])
    return out


def rapamycin_effects(data: pd.DataFrame, outcome: str, relative: bool = False,
                      level: float = 0.95, variance: str = "pooled") -> pd.DataFrame:
    """Rapamycin minus vehicle within each strain and within each strain × sex subgroup.

    Two families, each with Šidák adjustment and matching simultaneous CIs:
    - by strain, sexes pooled (k = 2 comparisons);
    - by strain × sex subgroup (k = 4 comparisons).
    Because the intervals are simultaneous, an interval excludes zero exactly
    when the Šidák-adjusted p-value is below 0.05. ``variance='hc3'`` repeats
    the comparisons with group-specific variances (see ``contrast``).
    """
    model = fit_factorial(data, outcome)
    mse, df = model.mse_resid, model.df_resid
    means = cell_summary(data, outcome)["mean"]

    specs = [("By strain (sexes pooled)", strain, "Both sexes",
              [c for c in CELLS if c[0] == strain], len(LEVELS["strain"]))
             for strain in LEVELS["strain"]]
    specs += [("By strain × sex", strain, sex,
               [c for c in CELLS if c[:2] == (strain, sex)], len(SUBGROUPS))
              for strain, sex in SUBGROUPS]

    rows = []
    for family, strain, sex, cells, k in specs:
        crit = stats.t.ppf(1 - sidak_level(1 - level, k) / 2, df)
        est = contrast(data, outcome, treatment_weights(cells), mse, df, crit=crit, variance=variance)
        vehicle_mean = means.loc[[c for c in cells if c[2] == "Vehicle"]].mean()
        rapamycin_mean = means.loc[[c for c in cells if c[2] == "Rapamycin"]].mean()
        row = {"family": family, "strain": strain, "sex": sex, "k": k,
               "vehicle_mean": vehicle_mean, "rapamycin_mean": rapamycin_mean,
               **est, "p_sidak": float(sidak_p(est["p"], k)),
               "cohens_d": est["estimate"] / np.sqrt(mse)}
        if relative:  # the interval treats the vehicle mean as fixed, so it is approximate
            row["pct_of_vehicle"] = 100 * est["estimate"] / vehicle_mean
            row["pct_ci_low"] = 100 * est["ci_low"] / vehicle_mean
            row["pct_ci_high"] = 100 * est["ci_high"] / vehicle_mean
        rows.append(row)
    return pd.DataFrame(rows)


def simple_effects(data: pd.DataFrame, outcome: str, factor: str, within: str,
                   level: float = 0.95, variance: str = "pooled") -> pd.DataFrame:
    """Effect of ``factor`` (second minus first level) within each level of ``within``.

    Averaged over the remaining factor, on the model's pooled error term, with
    Šidák adjustment and simultaneous CIs over the levels of ``within``.
    Example: the sex difference within each strain, averaged over treatment.
    """
    model = fit_factorial(data, outcome)
    k = len(LEVELS[within])
    crit = stats.t.ppf(1 - sidak_level(1 - level, k) / 2, model.df_resid)
    first, second = LEVELS[factor]
    rows = []
    for w_level in LEVELS[within]:
        cells = [c for c in CELLS if c[FACTORS.index(within)] == w_level]
        hi = [c for c in cells if c[FACTORS.index(factor)] == second]
        lo = [c for c in cells if c[FACTORS.index(factor)] == first]
        weights = {**{c: 1 / len(hi) for c in hi}, **{c: -1 / len(lo) for c in lo}}
        est = contrast(data, outcome, weights, model.mse_resid, model.df_resid, crit=crit,
                       variance=variance)
        rows.append({"within": w_level, "difference": f"{second} − {first}", "k": k, **est,
                     "p_sidak": float(sidak_p(est["p"], k))})
    return pd.DataFrame(rows)


def tukey_all_pairs(data: pd.DataFrame, outcome: str) -> pd.DataFrame:
    """Tukey HSD for all 28 pairs of the eight groups.

    ``difference`` is group_2 minus group_1, where the pair order follows
    statsmodels (combinations of the alphabetically sorted group labels).
    """
    result = pairwise_tukeyhsd(data[outcome].to_numpy(float),
                               data["group"].astype(str).to_numpy(), alpha=ALPHA)
    pairs = list(itertools.combinations([str(g) for g in result.groupsunique], 2))
    return pd.DataFrame({
        "group_1": [a for a, _ in pairs], "group_2": [b for _, b in pairs],
        "difference": result.meandiffs,
        "ci_low": result.confint[:, 0], "ci_high": result.confint[:, 1],
        "p_tukey": result.pvalues,
    })


def describe_groups(data: pd.DataFrame, outcome: str) -> pd.DataFrame:
    """n, mean, SD, median and range of one outcome in each of the eight groups."""
    rows = []
    for cell in CELLS:
        v = data.loc[data["group"] == group_label(cell), outcome].astype(float)
        rows.append({"strain": cell[0], "sex": cell[1], "treatment": cell[2], "n": v.size,
                     "mean": v.mean(), "sd": v.std(ddof=1), "median": v.median(),
                     "min": v.min(), "max": v.max()})
    return pd.DataFrame(rows)


def cell_means_ci(data: pd.DataFrame, outcome: str, level: float = 0.95) -> pd.DataFrame:
    """Model-based group means with 95% CIs from the pooled residual variance."""
    model = fit_factorial(data, outcome)
    cells = cell_summary(data, outcome)
    half = stats.t.ppf(1 - (1 - level) / 2, model.df_resid) * np.sqrt(model.mse_resid / cells["count"])
    return cells.assign(ci_low=cells["mean"] - half, ci_high=cells["mean"] + half)


def assumption_checks(data: pd.DataFrame, outcome: str) -> dict:
    """Residual normality, equal variances, outliers and influence for one outcome."""
    model = fit_factorial(data, outcome)
    resid = model.resid.to_numpy(float)
    groups = [data.loc[data["group"] == g, outcome].to_numpy(float) for g in GROUP_LABELS]
    sds = np.array([g.std(ddof=1) for g in groups])
    outliers = model.outlier_test(method="bonf")
    worst = outliers["student_resid"].abs().idxmax()
    cooks = model.get_influence().cooks_distance[0]
    return {
        "shapiro_p": stats.shapiro(resid).pvalue,
        "dagostino_p": stats.normaltest(resid).pvalue,
        "brown_forsythe_p": stats.levene(*groups, center="median").pvalue,
        "sd_ratio": sds.max() / sds.min(),
        "max_abs_student_resid": abs(outliers.loc[worst, "student_resid"]),
        "max_resid_animal": data.loc[worst, "animal_id"],
        "outlier_p_bonferroni": outliers.loc[worst, "bonf(p)"],
        "max_cooks_d": cooks.max(),
        "max_cooks_animal": data["animal_id"].iloc[int(np.argmax(cooks))],
    }


def detectable_effect(scale: float, df: float, alpha: float = ALPHA, power: float = 0.80) -> float:
    """Smallest true effect, in residual SDs, detected with the given power.

    Args:
        scale: Standard error of the contrast in residual-SD units,
            sqrt(sum(w² / n)) for group weights w and group sizes n.
    """
    t_crit = stats.t.ppf(1 - alpha / 2, df)

    def power_at(delta: float) -> float:
        # Probability of a significant result in the wrong direction. It is below
        # 1e-20 once delta > 8, where SciPy's noncentral t can return NaN instead.
        wrong_side = stats.nct.cdf(-t_crit, df, delta)
        return stats.nct.sf(t_crit, df, delta) + (wrong_side if np.isfinite(wrong_side) else 0.0)

    delta = optimize.brentq(lambda d: power_at(d) - power, 1e-6, 10.0)  # power ≈ 1 well before δ = 10
    return delta * scale


def design_sensitivity(df_resid: float, n_per_cell: int, power: float = 0.80) -> pd.DataFrame:
    """What this design can detect: smallest effect with the given power, per comparison type."""
    subgroup = [c for c in CELLS if c[:2] == SUBGROUPS[0]]
    strain = [c for c in CELLS if c[0] == LEVELS["strain"][0]]
    specs = [
        ("Main effect, e.g. rapamycin vs vehicle overall", "32 vs 32",
         term_weights(("treatment",)), 1),
        ("Two-way interaction, e.g. does the effect differ by strain", "16 per arm, 4 arms",
         term_weights(("strain", "treatment")), 1),
        ("Three-way interaction", "8 per arm, 8 arms",
         term_weights(("strain", "sex", "treatment")), 1),
        ("Rapamycin vs vehicle within one strain (Šidák, 2 comparisons)", "16 vs 16",
         treatment_weights(strain), len(LEVELS["strain"])),
        ("Rapamycin vs vehicle within one strain × sex group (Šidák, 4 comparisons)", "8 vs 8",
         treatment_weights(subgroup), len(SUBGROUPS)),
    ]
    rows = []
    for label, animals, weights, k in specs:
        w = np.array(list(weights.values()))
        scale = float(np.sqrt(np.sum(w**2) / n_per_cell))
        alpha = sidak_level(ALPHA, k)
        rows.append({"comparison": label, "animals": animals, "alpha": alpha,
                     "detectable_d": detectable_effect(scale, df_resid, alpha, power)})
    return pd.DataFrame(rows)


def correlation_summary(data: pd.DataFrame, x: str, y: str, level: float = 0.95) -> pd.DataFrame:
    """Overall and pooled within-group Pearson correlation between two outcomes.

    The overall correlation mixes two things: animals that differ, and groups
    that differ. The within-group correlation removes each group's mean from
    both variables first, so it only asks: within a group, do animals with a
    higher x also have a higher y? Its test has n − k − 1 degrees of freedom
    (a partial correlation adjusting for the k − 1 group indicators).
    """
    z_crit = stats.norm.ppf(1 - (1 - level) / 2)
    n, k = len(data), data["group"].nunique()

    overall = stats.pearsonr(data[x], data[y])
    ci = overall.confidence_interval(level)

    dx = data[x] - data.groupby("group", observed=True)[x].transform("mean")
    dy = data[y] - data.groupby("group", observed=True)[y].transform("mean")
    r = float(np.corrcoef(dx, dy)[0, 1])
    dof = n - k - 1
    p = float(2 * stats.t.sf(abs(r * np.sqrt(dof / (1 - r**2))), dof))
    z, se = np.arctanh(r), 1 / np.sqrt(n - k - 2)

    return pd.DataFrame([
        {"x": x, "y": y, "type": "Overall (all 64 animals)", "r": overall.statistic,
         "ci_low": ci.low, "ci_high": ci.high, "p": overall.pvalue, "df": n - 2},
        {"x": x, "y": y, "type": "Within groups (group means removed)", "r": r,
         "ci_low": np.tanh(z - z_crit * se), "ci_high": np.tanh(z + z_crit * se), "p": p, "df": dof},
    ])


def anova_pvalues(data: pd.DataFrame, outcome: str, robust: str | None = None) -> pd.Series:
    """Type III p-value of each term, optionally with heteroscedasticity-robust (HC3) tests."""
    table = anova(fit_factorial(data, outcome), typ=3, robust=robust).drop(index="Residual")
    return pd.Series(table["PR(>F)"].to_numpy(float),
                     index=[TERMS[term_key(n)][0] for n in table.index])
