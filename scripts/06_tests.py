"""06 - Automated tests for the pipeline.  Run:  python scripts/06_tests.py

1. Reproducibility  - regenerating the data gives byte-identical CSVs (seeded).
2. Independent KPI recomputation - KPIs recomputed from the RAW tables (no master table) match the analysis outputs.
3. Mass balance - reported kg = delivered + wasted after collection + never collected.
4. Negative tests - deliberately corrupted copies of the data MUST be rejected by the validation script.
5. Power BI export - every exported table is labelled SYNTHETIC DEMO DATA and keys resolve.
"""
import hashlib, shutil, subprocess, sys, tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
failures = []


def ok(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")
    if not cond:
        failures.append(name)


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


# 1 reproducibility ------------------------------------------------------------------------
tables = ["donors", "recipients", "volunteers", "daily_context", "surplus_records", "collections", "distributions"]
before = {t: md5(ROOT / "data/raw" / f"{t}.csv") for t in tables}
subprocess.run([PY, str(ROOT / "scripts/01_generate_data.py")], check=True, capture_output=True)
after = {t: md5(ROOT / "data/raw" / f"{t}.csv") for t in tables}
ok("Generator is deterministic (identical MD5 for all 7 raw CSVs)", before == after)

# 2 independent KPI recomputation (raw tables only) --------------------------------------------------
s, c, d = (pd.read_csv(ROOT / f"data/raw/{t}.csv") for t in ("surplus_records", "collections", "distributions"))
k = pd.read_csv(ROOT / "outputs/tables/kpis.csv", index_col=0)["value"]
ok("Reported kg matches", np.isclose(s.quantity_kg.sum(), k["Reported surplus (kg)"]))
ok("Collected kg matches", np.isclose(c.qty_collected_kg.sum(), k["Collected (kg)"]))
ok("Delivered kg matches", np.isclose(d.qty_distributed_kg.sum(), k["Delivered to recipients (kg)"]))
ok("Portions served matches", d.beneficiaries_served.sum() == k["Portions served"])
ok("Redistribution yield % matches", np.isclose(d.qty_distributed_kg.sum() / s.quantity_kg.sum() * 100, k["Redistribution yield (kg %)"]))
sc = c.merge(s[["surplus_id", "report_datetime"]], on="surplus_id")
resp = (pd.to_datetime(sc.pickup_datetime) - pd.to_datetime(sc.report_datetime)).dt.total_seconds() / 60
ok("Median response minutes matches", np.isclose(resp[sc.collection_status.str.startswith("Collected")].median(), k["Median report->pickup (min)"]))

# 3 mass balance ---------------------------------------------------------------------------
never = (s.quantity_kg.sum() - c.qty_collected_kg.sum())
ok("Mass balance: reported = delivered + post-collection waste + never collected",
   np.isclose(s.quantity_kg.sum(), d.qty_distributed_kg.sum() + d.wastage_kg.sum() + never, atol=1.0))
gd = pd.read_csv(ROOT / "outputs/tables/gap_decomposition.csv", index_col=0)
ok("Gap decomposition reconciles to reported kg", np.isclose(gd.kg.sum(), s.quantity_kg.sum(), atol=1.0))

# 4 negative tests: corrupt a COPY of the project and demand that validation fails ----------------
def corrupted_run(label, mutate):
    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp) / "p"
        shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns("outputs", "powerbi", "notebooks", "__pycache__", "clean"))
        for sub in ("data/clean", "outputs/tables", "outputs/figures", "powerbi/data"):
            (dst / sub).mkdir(parents=True, exist_ok=True)
        mutate(dst / "data/raw")
        r = subprocess.run([PY, str(dst / "scripts/02_cleaning_validation.py")], capture_output=True, text=True)
        ok(f"Validation rejects corrupted data: {label}", r.returncode != 0 and "FAIL" in r.stdout)


def m_dup_id(p):
    df = pd.read_csv(p / "surplus_records.csv"); df.loc[1, "surplus_id"] = df.loc[0, "surplus_id"]; df.to_csv(p / "surplus_records.csv", index=False)


def m_pickup_before_report(p):
    df = pd.read_csv(p / "collections.csv"); i = df.index[df.pickup_datetime.notna()][0]
    df.loc[i, "pickup_datetime"] = "2020-01-01 00:00:00"; df.to_csv(p / "collections.csv", index=False)


def m_bad_fk(p):
    df = pd.read_csv(p / "surplus_records.csv"); df.loc[5, "donor_id"] = "D999"; df.to_csv(p / "surplus_records.csv", index=False)


def m_overdistribute(p):
    df = pd.read_csv(p / "distributions.csv"); i = df.index[df.distribution_status == "Delivered"][0]
    df.loc[i, "qty_distributed_kg"] += 50; df.to_csv(p / "distributions.csv", index=False)


def m_nonveg_to_vegonly(p):
    dist, col, sur, rec = (pd.read_csv(p / f"{t}.csv") for t in ("distributions", "collections", "surplus_records", "recipients"))
    nv = dist.merge(col[["collection_id", "surplus_id"]], on="collection_id").merge(sur[["surplus_id", "diet_type"]], on="surplus_id")
    i = nv.index[(nv.diet_type == "Non-Veg") & (nv.distribution_status == "Delivered")][0]
    veg = rec.loc[rec.diet_acceptance == "Veg-only", "recipient_id"].iloc[0]
    dist.loc[dist.distribution_id == nv.loc[i, "distribution_id"], "recipient_id"] = veg; dist.to_csv(p / "distributions.csv", index=False)


def m_no_label(p):
    df = pd.read_csv(p / "donors.csv"); df.loc[0, "data_label"] = "REAL DATA"; df.to_csv(p / "donors.csv", index=False)


for lbl, fn in (("duplicate primary key", m_dup_id), ("pickup before report", m_pickup_before_report), ("orphan foreign key", m_bad_fk),
                ("distributed + wastage != collected", m_overdistribute), ("Non-Veg food sent to Veg-only recipient", m_nonveg_to_vegonly),
                ("synthetic label removed", m_no_label)):
    corrupted_run(lbl, fn)

# 5 Power BI export --------------------------------------------------------------------------
pbi = ROOT / "powerbi/data"
files = sorted(pbi.glob("*.csv"))
ok("Power BI export has >= 15 tables", len(files) >= 15, f"({len(files)})")
ok("Every Power BI table carries the SYNTHETIC DEMO DATA label", all((pd.read_csv(f, usecols=["data_label"]).data_label == "SYNTHETIC DEMO DATA").all() for f in files))
fs, fd = pd.read_csv(pbi / "fact_surplus.csv"), pd.read_csv(pbi / "fact_distribution.csv")
ok("fact_surplus -> dim_date/donor/food keys resolve",
   fs.date_key.isin(pd.read_csv(pbi / "dim_date.csv").date.str[:10]).all() and fs.donor_id.isin(pd.read_csv(pbi / "dim_donor.csv").donor_id).all()
   and fs.food_category.isin(pd.read_csv(pbi / "dim_food_category.csv").food_category).all() and fs.time_slot.isin(pd.read_csv(pbi / "dim_time_slot.csv").time_slot).all())
ok("fact_distribution -> fact_surplus / dim_recipient keys resolve",
   fd.collection_id.isin(fs.collection_id).all() and fd.recipient_id.dropna().isin(pd.read_csv(pbi / "dim_recipient.csv").recipient_id).all())
ok("fact_surplus.collection_id unique (one-to-many to distributions)", fs.collection_id.is_unique)

print(f"\n{'ALL TESTS PASSED' if not failures else 'FAILED: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
