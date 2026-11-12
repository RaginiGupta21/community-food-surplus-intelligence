# 02 - Research Methodology

## Pipeline
`00_area_selection` -> `01_generate_data` -> `02_cleaning_validation` -> `03_eda` -> `04_advanced_analytics` -> `05_export_powerbi` -> `06_tests`

## 1. Synthetic data design
A **process simulation** (seed 2026) rather than random columns, so relationships are logically consistent:
1. **Donors (128, 7 categories)** get zone, size class, activity level, onboarding and (8%) withdrawal dates.
2. **Surplus reports (10,302; 1 Nov 2025 - 31 Oct 2026)**: each donor-day is a Bernoulli draw whose probability depends on category, weekday,
   festival windows, wedding season and donor activity. Quantity is log-normal per category; report time is a category-specific mixture
   (e.g. restaurants after lunch and near closing, caterers after events); the declared safe window and preparation lag depend on the food category.
3. **Collections (1 per report)**: cancellation by donor; volunteer availability depends on shift (Morning/Afternoon/Evening/Late), weekday/weekend roster,
   rain and a 4-pickups-per-day cap; arrival time = acknowledgement + mobilisation + travel (vehicle speed) with occasional long delays;
   a volunteer safety check may reject food (a *logged human decision*); vehicle load limits cause partial pickups.
4. **Distributions (1-2 per collected consignment)**: recipients must be open (acceptance windows), accept the diet (Non-Veg vs Veg-only) and food type, have daily
   capacity left, and delivery must occur inside the safe window; otherwise the kg is recorded as wastage with a reason.
5. **Realistic noise**: raw files contain letter-case/whitespace/"&" variants and a few missing optional fields (cleaned in step 2).
   Integrity (keys, dates, quantities) is deliberately never corrupted.

Calibration to public evidence (festival calendar, 2026 monsoon pattern, FSSAI holding times, event/canteen surplus benchmarks, ward demographics) is documented in `docs/07_realism_and_calibration.md`.
Remaining assumptions (all editable in `01_generate_data.py`): one pickup = one volunteer = one trip; fictional organisations; wedding-season windows; day-level rain is simulated; volunteer supply and recipient windows/capacities; donor-declared safe windows are advisory inputs only.

## 2. Cleaning and validation
Canonical-label mapping, type parsing, missing-value policy (optional fields -> "Not Recorded"), and **73 integrity checks** (V01-V20):
schema vs data dictionary, primary/foreign keys, one collection per report, date ordering, donor active period, quantity bounds, status logic,
safe-window logic, recipient windows, diet/cooked-food compatibility, daily capacity, mass reconciliation (distributed + wastage = collected),
bounding box, allowed values. Any critical failure stops the pipeline.
`06_tests.py` also proves the validator **rejects** six kinds of deliberately corrupted data.

## 3. Analysis methods
| Question | Method | Guard-rail |
|---|---|---|
| What, who, why, when | Descriptive statistics, Pareto/Gini, reason x category heat map, weekday x hour heat map | Kg per active donor controls for onboarding growth |
| Do groups differ? | Kruskal-Wallis, Mann-Whitney, chi-square, Spearman | Effect sizes (epsilon^2, rank-biserial, Cramer's V, rho) reported - with ~10k rows p-values alone are uninformative |
| What drives collection? | Logistic regression (odds ratios, 95% CI) | Pseudo-R^2 reported; associations in synthetic data, not causes |
| Efficiency | Collection rate, redistribution yield = delivered/reported, delivery efficiency = delivered/collected, response-time distribution | All KPIs recomputed independently in tests |
| Redistribution gaps | Mass-balance decomposition of every reported kg; zone, hour and zone-to-zone flow analysis | Decomposition must reconcile to reported kg |
| Donor segments | K-Means on 6 behavioural features (standardised), k = 2-7 | Used only if silhouette >= 0.25 **and** bootstrap ARI >= 0.75; outcomes used to *profile*, not cluster |
| Forecast | Seasonal naive, 4-week mean, Holt-Winters, regression; 16-origin rolling back-test, 7-day horizon | Must beat seasonal naive by > 5%; interval from empirical back-test errors; only 1 annual cycle -> 14-day horizon only |
| Hotspots | 300 m grid, nearest-recipient distance, Global Moran's I (999 permutations) | Approximate coordinates -> exploratory |
| Impact scenarios | Transparent arithmetic using observed conversion rates | Labelled indicative, not predictions |

## 4. Reproducibility
Seeded generator; byte-identical regeneration tested; notebooks are generated from, and executed against, the same scripts.
