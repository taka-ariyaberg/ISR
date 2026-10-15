# Data

| File | What it is | Written by |
|---|---|---|
| `Dataset Antistroke FC.xlsx` | Raw dataset provided by the course: two sheets, `CBF` and `Infarct`, with one row per animal | The course. Never edit it: the notebook checks its SHA-256 fingerprint before reading anything |
| `processed/antistroke_clean.csv` | Clean, analysis-ready table: one row per animal, both sheets merged | [`../statistical_analysis.ipynb`](../statistical_analysis.ipynb), Section 3 |

## Preprocessing (Section 3 of the notebook)

1. Reads both sheets with the column headers on row 2 (row 1 is a sheet title).
2. Renames the columns to short lowercase names with the unit as a suffix.
3. Trims trailing spaces: the raw `Sex:` column has `"Female "` or `"Male "` for A010, A018, A033 and A058 on both sheets. Untrimmed, the models would see four sexes.
4. Makes strain, sex and treatment categorical with a fixed level order (the first level is the reference).
5. Merges the sheets on `animal_id` and checks that the group labels agree, the design is balanced (8 per group), nothing is missing and every value is plausible.
6. Adds `group`, `subgroup` and `meets_strict_occlusion`.

## Data dictionary: `processed/antistroke_clean.csv`

| Column | Type | Values | Description |
|---|---|---|---|
| `animal_id` | text | A001 to A064 | Animal identifier, as in the raw file |
| `strain` | category | Wistar, SHR | Rat strain; reference level Wistar |
| `sex` | category | Male, Female | Sex; reference level Male |
| `treatment` | category | Vehicle, Rapamycin | Randomised treatment; reference level Vehicle |
| `group` | category | 8 levels | Strain · sex · treatment, e.g. `Wistar · Male · Vehicle` |
| `subgroup` | category | 4 levels | Strain · sex, e.g. `Wistar · Male` |
| `cbf_probe1_pct` | number | −83 to −70 | Core CBF (laser-Doppler probe 1, MCA core territory), % change from baseline |
| `cbf_probe2_pct` | number | −51 to −15 | Collateral CBF (probe 2, collateral or peri-infarct territory), % change from baseline |
| `infarct_mm3` | number | 36 to 99 | Infarct volume 24 h after stroke, mm³ |
| `meets_strict_occlusion` | true/false | 58 true, 6 false | Core flow fell by more than 70 %. The six `false` animals sit exactly at −70 |

The dataset does not name the probe positions; the ones above are from the original study (Beard et al. 2020, *Stroke* 51:2834–2843). A CBF value of −70 means flow fell to 30 % of its baseline. All measurements were recorded as whole numbers.
