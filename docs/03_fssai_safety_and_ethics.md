# 03 - FSSAI Food-Safety Considerations and Ethics

> This is a project summary, **not legal advice**. The regulation text and FSSAI guidance can be amended - check
> fssai.gov.in and the Eat Right India "Save Food, Share Food" pages for the current version before any real-world use.

## Regulatory frame (as published)
* The **Food Safety and Standards (Recovery and Distribution of Surplus Food) Regulations, 2019** set responsibilities for food donors (food business
  operators) and for *surplus food distribution organisations*. A donor must not pass unsafe food on, and surplus food must be maintained as
  per Schedule I; food may not be distributed after its shelf life has expired.
* Surplus food distribution organisations are expected to be regulated under the **Licensing and Registration of Food Business Regulations, 2011**
  (i.e. to hold the appropriate FSSAI registration/licence), to follow hygiene and storage/transport/reheating requirements, and to have staff trained under
  **FoSTaC**. Compliance dates were extended after the original 2020 date.
* Schedule II requires **records**: donor and distribution-organisation names/addresses, donation date, product, batch/dates and quantity.
* FSSAI's "Save Food, Share Food, Share Joy" initiative encourages food-recovery ecosystems.

## Timing and temperature guidance used for calibration
FSSAI's Save Food Share Food guidance: hot food held at 60 C or above (carriers 65 C or above), cold food at 5 C or below, cooked food consumed within 4 hours at room
temperature (4-6 h listed; 12-24 h refrigerated), cut fruit about 24 h, fresh produce 1-2 days, transport within 2 hours of preparation. The simulator's declared safe windows follow
these ranges for cooked food, snacks and fruit; other windows are assumptions. They remain **advisory planning inputs** only.

## How the project reflects this
| Requirement | Project design |
|---|---|
| Records of donations | `handover_record_complete` field and KPI; field templates capture donor, recipient, date, item, quantity |
| Do not distribute expired food | Declared safe window stored per report; validation proves no delivery after expiry (V09, V11) |
| Recipient suitability | Recipient acceptance windows, diet and cooked-food capability modelled (V13, V14) |
| Trained handlers | `fostac_trained` flag in the volunteer table (synthetic); templates ask for evidence |
| Licence/registration | Donor "declared" status and recipient "verified on portal" columns in templates; never assumed |

## Absolute rules
1. **No automated food-safety decisions.** The system never labels food "safe" or "unsafe". `declared_safe_window_hours` and `perishability_class` are
   *planning inputs*; every collection and hand-over needs a trained person's go/no-go (`human_go_no_go_decision` in the templates).
2. **No invented partners.** NGO names in the data are fictional ("Demo ... 01"); real partners must be verified and must consent.
3. **Privacy**: business-level data only; no beneficiary personal data; written consent; secure storage; anonymised reporting.
4. **Ethics approval** from the university before any survey or pilot; photographs only with permission.
5. **Synthetic vs real**: every table, chart and dashboard page is labelled SYNTHETIC DEMO DATA; mixing with field data is prohibited.
