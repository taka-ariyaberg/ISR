# Rapamycin after stroke in aged rats: statistical analysis

Does rapamycin given after an experimental stroke still reduce infarct size in old rats, and does the answer depend on strain or sex? This folder holds the complete statistical analysis of the course dataset for that question, from the raw spreadsheet to the final tables and figures, with everything needed to reproduce it.

**Read the report:** [statistical_analysis.html](https://taka-ariyaberg.github.io/ISR/biostatistics/statistical_analysis.html) opens the formatted report in the browser; [statistical_analysis.ipynb](statistical_analysis.ipynb) is the executed notebook itself.

## Study

Sixty-four aged rats, Wistar and spontaneously hypertensive (SHR), females and males, received rapamycin or vehicle after an experimental stroke: a fully crossed 2 × 2 × 2 design with 8 rats per group. Treatment was randomised and coded. Three outcomes were measured:

| Outcome | Measurement | Unit |
|---|---|---|
| Core CBF | Laser-Doppler probe 1, over the core of the middle cerebral artery (MCA) territory | % change from baseline |
| Collateral CBF | Laser-Doppler probe 2, over the collateral (peri-infarct) territory | % change from baseline |
| Infarct volume | Tissue lost 24 h after the stroke | mm³ |

CBF is cerebral blood flow. The dataset numbers the probes without naming their positions; the positions above are those of the original study, which used young male rats only (Beard et al. 2020).

## Main results

- Rapamycin reduced mean infarct volume from 77.2 to 61.3 mm³, by 15.9 mm³ or 21 % (p < 0.001).
- The reduction depended on strain (strain × treatment p = 0.003): 23.1 mm³ (31 %) in Wistar rats and 8.8 mm³ (11 %) in SHR, where it is modest and borderline (Šidák p = 0.019, or 0.049 when each group keeps its own variance).
- There was no detectable sex difference in the rapamycin effect overall (sex × treatment p = 0.16). In Wistar the reduction was larger in males than in females, but the three-way interaction behind this is only suggestive.
- Treated Wistar rats lost 10.3 percentage points less collateral flow than vehicle rats; in SHR the difference (3.4 points) was not significant, and core flow showed no detectable treatment difference. The dataset does not say whether CBF was recorded before or after dosing, so these flow differences count as drug effects only if it was recorded after.
- Vehicle-treated SHR and Wistar rats had similar infarcts (+3.2 mm³, p = 0.55); with rapamycin, SHR infarcts were 17.6 mm³ larger than Wistar infarcts.

Section 12 of the report compares these results with the original study and lists the limitations.

## Methods in brief

Each outcome was analysed with a three-way ANOVA (strain × sex × treatment with all interactions, Type III sums of squares), with Holm-adjusted p-values across its seven terms. Rapamycin was compared with vehicle by planned contrasts within each strain and within each strain × sex group, Šidák-adjusted, with simultaneous 95 % confidence intervals. Model assumptions were checked on the residuals. The conclusions were then re-tested with heteroscedasticity-consistent (HC3) standard errors, without the six animals exactly at the −70 % occlusion threshold, and with one Holm correction across all 21 ANOVA tests. Section 4 of the report gives the reason for every choice.

## Reproduce the analysis

You need [conda](https://conda-forge.org/download/) (Miniforge is the smallest installer) and git. In a terminal:

```bash
git clone https://github.com/taka-ariyaberg/ISR.git
cd ISR/biostatistics
conda env create -f environment.yml      # once: Python 3.12 with every package pinned
conda activate ISR
jupyter nbconvert --to notebook --execute --inplace statistical_analysis.ipynb
python export_html.py                    # rebuilds statistical_analysis.html
```

To work in the notebook interactively, register the environment as a kernel once with `python -m ipykernel install --user --name ISR --display-name "Python (ISR)"`, open `statistical_analysis.ipynb` in JupyterLab or VS Code, choose the **Python (ISR)** kernel and run all cells.

A full run takes about 30 seconds. It checks the SHA-256 fingerprint of the raw file before reading anything, rewrites `data/processed/antistroke_clean.csv`, `figures/` and `tables/`, and stops with an error if any of its 13 verification checks fails; one of those checks recomputes the key numbers quoted in the report's text. Nothing in the analysis is random, so every run gives the same numbers. The figures use Arial where it is installed and DejaVu Sans otherwise.

## Contents

```
biostatistics/
├── README.md                       this file
├── environment.yml                 conda environment "ISR", every package pinned
├── statistical_analysis.ipynb      the analysis, executed, with all outputs
├── statistical_analysis.html       the same notebook as a formatted report
├── export_html.py                  builds the report from the executed notebook
├── helpers/                        modules the notebook calls
│   ├── design.py                   factor levels, groups and outcomes
│   ├── stats.py                    models, contrasts, effect sizes and corrections
│   ├── plots.py                    figure style and one function per figure
│   └── report.py                   number formatting and tables
├── data/
│   ├── README.md                   data dictionary and preprocessing steps
│   ├── Dataset Antistroke FC.xlsx  raw dataset, as provided by the course
│   └── processed/
│       └── antistroke_clean.csv    clean table written by the notebook
├── figures/                        nine figures, each as PNG (600 dpi), SVG and PDF
└── tables/                         results tables as CSV
```

| Figure | Shows |
|---|---|
| `fig01_individual_animals` | Every animal by strain, sex and treatment, with mean ± SD |
| `fig02_probe_check` | Probe 1 against probe 2 within each animal |
| `fig03_model_checks` | Q–Q plots and residual plots |
| `fig04_effect_sizes` | Partial η² for every ANOVA term |
| `fig05_interactions` | Group means by strain, sex and treatment |
| `fig06_rapamycin_effects` | Rapamycin − vehicle with simultaneous 95 % CIs |
| `fig07_individual_animals_with_tests` | Figure 1 with significance marks for rapamycin − vehicle |
| `fig08_tukey_all_pairs` | All 28 pairwise group differences |
| `fig09_cbf_vs_infarct` | Collateral CBF against infarct volume, overall and within groups |

| Table | Contents |
|---|---|
| `table1_descriptives.csv` | Group means, SDs and ranges |
| `table2_anova.csv` | Three-way ANOVA for each outcome |
| `table3_strain_and_sex_follow_ups.csv` | Strain difference within each treatment and sex difference within each strain |
| `table4_rapamycin_effects.csv` | Rapamycin − vehicle by strain and by strain × sex group |
| `table5_robustness_anova.csv` | ANOVA verdicts under each robustness check |
| `table6_robustness_rapamycin.csv` | Rapamycin comparisons under each robustness check |
| `table7_cbf_infarct_correlations.csv` | Correlations between CBF and infarct volume |
| `tableS1_tukey_all_pairs.csv` | All 28 pairwise comparisons (Tukey HSD) |

## Software

Python 3.12.14, NumPy 2.5.3, pandas 3.0.6, SciPy 1.18.1, statsmodels 0.15.0, matplotlib 3.11.2 and openpyxl 3.1.5, all from conda-forge. `environment.yml` pins these and the Jupyter tools, and resolves on macOS, Windows and Linux. Section 14 of the report lists the versions of the run that produced the files here.

## References

1. Beard DJ, Li Z, Schneider AM, Couch Y, Cipolla MJ, Buchan AM. Rapamycin induces an eNOS (endothelial nitric oxide synthase) dependent increase in brain collateral perfusion in Wistar and spontaneously hypertensive rats. *Stroke*. 2020;51(9):2834–2843. [doi:10.1161/STROKEAHA.120.029781](https://doi.org/10.1161/STROKEAHA.120.029781)
2. Fisher M, Feuerstein G, Howells DW, Hurn PD, Kent TA, Savitz SI, Lo EH; STAIR Group. Update of the Stroke Therapy Academic Industry Roundtable preclinical recommendations. *Stroke*. 2009;40(6):2244–2250. [doi:10.1161/STROKEAHA.108.541128](https://doi.org/10.1161/STROKEAHA.108.541128)

The report lists every reference it cites.

## About

Analysis by Taka Ariyaberg for the group assignment "Anti-stroke Project (Extended)" in the course Introduction to Scientific Research, Uppsala University, 2026. The dataset was provided by the course for this assignment.
