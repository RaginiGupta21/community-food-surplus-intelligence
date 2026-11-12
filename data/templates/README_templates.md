# Field data collection templates
Blank CSVs with the same columns as `data/data_dictionary.csv` plus verification/safety-record columns.
* Use IDs exactly as in the dictionary (D###, R##, V##, S######, C######, X######), continue numbering from 1 for real data.
* Use ONLY labels listed in `allowed_values_lookup.csv`.
* Times: `YYYY-MM-DD HH:MM` (24 h). Quantities: kg, one decimal. Weigh when possible; mark estimates in notes.
* Real records must say `FIELD DATA` in `data_source`; never mix with SYNTHETIC DEMO DATA files.
* `human_go_no_go_decision` is always made and signed by a trained person. Nothing in this project automates food-safety decisions.
* Collect only business-level information. Do not record personal data of beneficiaries; obtain written consent from donors and
  recipient organisations first; keep files on a password-protected device.
