# 05 - Recommendations, Impact Indicators and Pilot Proposal

> Recommendations are hypotheses generated from SYNTHETIC DEMO DATA. They show *how* the analysis would guide action; they must be re-tested on field data.

## A. Practical improvements
**Donor participation**
1. Prioritise onboarding of the high-volume, late-night, high-perishability donor segment (caterers, banquet halls, large restaurants): in the demo they
   hold most of the reported kg but have the lowest redistribution yield.
2. Offer a 2-minute reporting form that captures quantity, preparation time and safe window at the moment of surplus (improves record quality).
3. For event donors, add a pre-event "possible surplus" alert 24 hours ahead so volunteers and recipients can be lined up.

**Collection coordination**
4. Fill the evening/late-night volunteer gap (21:00-24:00): that is when most surplus appears, and "no volunteer available" is the largest loss before collection.
5. Match vehicle to load: dispatch a van or second trip for expected loads above two-wheeler capacity; log "partial - load capacity" as a trigger.
6. Rain protocol: pre-book volunteers on forecast heavy-rain days (rain roughly halves the odds of collection in the demo).

**Redistribution planning**
7. Negotiate extended late acceptance windows with a few recipients (night shelters, community kitchens) - the supply peak (22:00-23:30) meets very few open recipients.
8. Put recipient capacity where surplus is: Dadar West and Shivaji Park have the most surplus but little nearby capacity.
9. Pair every donor with a primary and a backup recipient that accepts its diet (Non-Veg vs Veg-only).

## B. Measurable impact indicators (baseline = demo values; replace with pilot baseline)
| Indicator | Definition | Demo baseline |
|---|---|---|
| Redistribution yield | delivered kg / reported kg | see `outputs/tables/kpis.csv` |
| Collection rate (kg) | collected kg / reported kg | see kpis |
| Evening-slot yield | yield for reports 21:00-24:00 | `efficiency_by_time_slot.csv` |
| Median / P90 report-to-pickup | minutes | kpis |
| Portions served per week | sum of `beneficiaries_served` | kpis |
| Post-collection wastage % | wasted / collected kg | decomposition |
| Hand-over record completeness | % of deliveries with a complete record | kpis |
| Active donors / donor retention | donors reporting in last 30 days | monthly series |
| Safety incidents | reports of illness or complaint (target 0) | field log |

## C. Indicative scenarios (`impact_scenarios.csv`, arithmetic on demo data)
Halving "no volunteer" misses, adding second trips for large loads, and extending recipient windows each add roughly 3-8 percentage points of yield; combined
about 11 points (an upper bound - overlaps not removed).

## D. Proposed small supervised pilot (not started; no partner assumed)
* **Aim**: test whether coordinated evening pickup raises redistribution yield without any food-safety incident.
* **Scope**: 6-8 weeks, 8-12 consenting donors in one or two zones, 1-2 recipient organisations that are **FSSAI-registered and agree in writing**.
* **Partner**: an *authorised* surplus-food distribution organisation, identified through the FSSAI food-licensing/registration records and direct
  outreach with faculty support. The partner owns all food-safety decisions, storage, transport and labelling.
* **Design**: 2 baseline weeks (observe, log) then 4-6 intervention weeks (evening volunteer slot, standard report form); weekly review with the partner.
* **Data**: field templates in `data/templates/`; same pipeline reruns; compare yield, response time and wastage; report effect sizes with intervals.
* **Safeguards**: ethics approval, written consent, trained handlers, temperature/time checks recorded by humans, stop rule on any complaint.
