"""07 - Create blank FIELD-DATA collection templates (CSV) with the same columns as the data dictionary
(minus constant label columns), plus a lookup sheet of allowed values. Run: python scripts/07_make_templates.py"""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import TEMPLATES, ensure_dirs
from schema import *

ensure_dirs()
extra = {"donors": ["consent_to_participate (Yes/No)", "contact_person_role", "fssai_licence_number_seen (Y/N; do not store the number if not needed)", "verified_by", "verification_date"],
         "recipients": ["authorisation_document_seen (Y/N)", "fssai_registration_verified_on_portal (Y/N)", "verified_by", "verification_date"],
         "surplus_records": ["recorded_by", "photo_reference_optional"],
         "collections": ["volunteer_foSTaC_trained (Y/N)", "temperature_check_done (Y/N)", "temperature_reading_c", "human_go_no_go_decision (Go/No-Go)", "decision_made_by"],
         "distributions": ["recipient_representative_signed (Y/N)", "temperature_on_arrival_c", "human_go_no_go_decision (Go/No-Go)", "decision_made_by", "labelling_done (Y/N)"]}
for t, rows in TABLES.items():
    cols = [r[0] for r in rows if r[0] != "data_label"] + ["data_source (FIELD DATA)"] + extra.get(t, [])
    pd.DataFrame(columns=cols).to_csv(TEMPLATES / f"template_{t}.csv", index=False)
lk = {"donor_category": DONOR_CATEGORIES, "sub_area": ZONES, "food_category": FOOD_CATEGORIES, "surplus_reason": REASONS,
      "collection_status": COLLECTION_STATUSES, "wastage_reason": WASTE_REASONS, "recipient_type": RECIPIENT_TYPES,
      "packaging_type": PACKAGING, "storage_condition": STORAGE, "diet_type": ["Veg", "Non-Veg"]}
n = max(map(len, lk.values()))
pd.DataFrame({k: v + [""] * (n - len(v)) for k, v in lk.items()}).to_csv(TEMPLATES / "allowed_values_lookup.csv", index=False)
(TEMPLATES / "README_templates.md").write_text("""# Field data collection templates
Blank CSVs with the same columns as `data/data_dictionary.csv` plus verification/safety-record columns.
* Use IDs exactly as in the dictionary (D###, R##, V##, S######, C######, X######), continue numbering from 1 for real data.
* Use ONLY labels listed in `allowed_values_lookup.csv`.
* Times: `YYYY-MM-DD HH:MM` (24 h). Quantities: kg, one decimal. Weigh when possible; mark estimates in notes.
* Real records must say `FIELD DATA` in `data_source`; never mix with SYNTHETIC DEMO DATA files.
* `human_go_no_go_decision` is always made and signed by a trained person. Nothing in this project automates food-safety decisions.
* Collect only business-level information. Do not record personal data of beneficiaries; obtain written consent from donors and
  recipient organisations first; keep files on a password-protected device.
""")
print("templates:", sorted(p.name for p in TEMPLATES.iterdir()))
