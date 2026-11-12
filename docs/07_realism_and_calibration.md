# 07 - Realism and Calibration (no surveys)

The data are **still synthetic** (and every table says so), but the simulator is now calibrated to public evidence wherever evidence exists.
`data/calibration_sources.csv` lists every parameter with its source, URL and an **evidence status**:
*Sourced* (taken from a public source), *Adapted* (derived from one), *Assumption* (no public source found), *Conflicting - verify*.

## What is now grounded in evidence
| Area | Grounding |
|---|---|
| Study area | G North ward: 9.07 km2, ~5.9-6.0 lakh residents, ~66,000 per km2, ~33% slum population; Dadar, Matunga and Mahim stations |
| Calendar | Festival dates of 2026 cross-checked across public calendars; Diwali (8 Nov 2026) and Diwali 2025 (20-21 Oct) fall outside the data window |
| Weather | 2026 monsoon: onset ~22 June (about two weeks late), very wet July (Santacruz ~1,492 mm vs ~856 mm normal), dry spell 1-4 Aug, below-normal Aug-Sep outlook. Day-level rain is simulated to match these monthly patterns |
| Food safety | FSSAI guidance: hot food >= 60 C, cold <= 5 C, cooked food 4-6 h at room temperature, cut fruit 24 h, fresh produce 1-2 days, transport within 2 h of preparation. Safe windows for cooked food were tightened from 6-8 h to 4-6 h |
| Event surplus | Feeding India / UAS-Bangalore figures: 10-20% of wedding food discarded, ~30-50 kg per average wedding -> caterer and banquet quantities |
| Canteens | University-kitchen study: ~10 kg/day per kitchen -> canteen quantities |
| Scale check | UNEP Food Waste Index 2024: 55 kg household food waste per person per year. See the plausibility check in doc 04 |

## What is still an assumption (and why it matters)
Volunteer supply, recipient windows and capacities, response times, restaurant/bakery quantities, and festival demand multipliers have **no public source**
(nobody publishes them). They drive the late-night and capacity results, so treat those results as scenario outputs, not measurements.
The simulator exposes each of them as an editable parameter in `scripts/01_generate_data.py`.

## How this changes the claims you can make
Say: "a simulation calibrated to published 2026 calendar, weather, FSSAI timing and food-waste benchmarks".
Do not say: "real data" or "verified findings". The deliverable remains a decision-support method demonstrated on synthetic data.

## Cheap upgrades that still need no survey
1. Replace assumptions with ranges from any organisation's public annual report or news story (e.g. pickups per volunteer, meals per day).
2. Run the model with low/base/high parameter sets and show which conclusions survive (a sensitivity analysis).
3. If you later get even one NGO's monthly totals, compare them with the simulator's totals as a one-line validation.
