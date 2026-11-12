# 01 - Area Selection, Scope and Stakeholders

> Scores below are **provisional desk-based analyst judgements (1-5)**, not measured data. No NGO, business or society
> has been contacted, and **no partnership or access is claimed**. Everything in `data/` is SYNTHETIC DEMO DATA.

## Candidate localities and criteria
Seven Mumbai localities were scored on five weighted criteria (`outputs/tables/area_selection_matrix.csv`, figure `00_area_selection.png`):

| Criterion | Weight | Why it matters |
|---|---|---|
| Accessibility (rail/road, walkability) | 20% | Volunteers on foot/bicycle/two-wheeler must reach donors within the safe-food window |
| Donor density and diversity | 25% | Restaurants, bakeries, caterers, sweet shops, canteens, banquet halls and societies give different surplus patterns |
| Proximity to underserved communities | 25% | Short delivery legs protect food quality |
| Recipient / NGO accessibility | 15% | Community kitchens, shelters, children's and old-age homes nearby |
| Compactness / field feasibility | 15% | A student team must be able to survey it on foot in a few days |

Result: **Dadar-Matunga-Mahim (with the Dharavi fringe)** scored 4.45/5; next best were Andheri West and Kurla-Chunabhatti (3.55).
A weight-sensitivity test (10,000 random weight vectors) kept Dadar-Matunga-Mahim first in about 98% of draws; Kurla-Chunabhatti
wins only when "proximity to underserved communities" dominates the weights - a reasonable alternative for a later phase.

## Justification of the selected locality
* Dense, mixed donor base within a few km: Dadar market/station belt, Shivaji Park and Matunga caterers, sweet shops and
  Udupi/Irani-style eateries, colleges and hostels (canteens), Mahim bakeries and eateries, banquet halls and housing societies.
* Underserved communities lie adjacent (Dharavi fringe and informal-settlement pockets, labour camps), so delivery legs are short.
* Western + Central + Harbour-line access (Dadar, Matunga Road, Mahim) makes it reachable for volunteers without cars.
* Compact enough for a walking field survey; fits a 6-8 week student pilot.

## Geographical scope (study area)
Six working zones: **Dadar West, Dadar East, Shivaji Park, Matunga, Mahim, Dharavi Fringe** (roughly 19.01-19.05 N, 72.83-72.87 E).
Public sources describe G North ward as 9.07 km2 with about 5.9-6.0 lakh residents (Census 2011), roughly 66,000 people per km2 and about a third of residents in slums; it covers Dadar, Mahim, Dharavi and Shivaji Park. Sources disagree on whether Matunga East belongs to G North or F North, so **confirm boundaries on a BMC ward map** before reporting (see `data/calibration_sources.csv`).
Coordinates in the synthetic data are zone centroids plus random jitter - they are not real addresses.

## Stakeholders
| Stakeholder | Role | Status in this project |
|---|---|---|
| Food donors (restaurants, bakeries, caterers, sweet shops, canteens, banquet halls, housing societies) | Source of surplus | Hypothetical in demo data; real ones need consent |
| Surplus-food distribution organisations / NGOs (community kitchens, shelters, homes) | Collect, store, hand over food | **Not contacted; none named.** Identify through the FSSAI registry and direct outreach |
| Volunteers / transport partners | Pickup and delivery | Hypothetical |
| Beneficiaries | Receive food | No personal data collected |
| FSSAI / Food Safety Officers, BMC | Regulators | Rules summarised in doc 03; verify the current text |
| University faculty / ethics reviewer | Oversight | Approval needed before any field work |
