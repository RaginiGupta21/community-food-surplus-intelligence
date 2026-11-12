# %% [markdown]
# # 02 - Data Cleaning, Validation and Master Tables
# **SYNTHETIC DEMO DATA** - Community Food Surplus Intelligence and Redistribution Analysis System
#
# This notebook/script (1) loads the raw CSVs, (2) standardises text and types and logs every fix,
# (3) runs 25+ integrity checks (keys, dates, quantities, status logic, recipient windows, capacity,
# reconciliation) and (4) builds analysis-ready master tables. It **stops with an error** if any
# critical check fails, so downstream analysis never runs on contradictory data.

# %%
import sys, re, pathlib
_here = pathlib.Path(__file__).resolve().parent if "__file__" in globals() else pathlib.Path.cwd()
_scripts = _here if (_here / "common.py").exists() else _here.parent / "scripts"
sys.path.insert(0, str(_scripts))

import numpy as np
import pandas as pd
from common import RAW, CLEAN, TAB, DATA_LABEL, DATA, ensure_dirs
from schema import (TABLES, ZONES, FOOD_CATEGORIES, REASONS, DONOR_CATEGORIES, PACKAGING, STORAGE,
                    COLLECTION_STATUSES, SHIFTS, RECIPIENT_TYPES)

ensure_dirs()
pd.set_option("display.width", 160, "display.max_columns", 40)
raw = {t: pd.read_csv(RAW / f"{t}.csv") for t in TABLES}
print({t: df.shape for t, df in raw.items()})

# %% [markdown]
# ## 1. Standardisation (cleaning log)
# Free-text categorical fields are mapped to canonical labels using a normalised key
# (lower-case, `&`→`and`, punctuation/whitespace removed). Every change is counted in `cleaning_log.csv`.

# %%
log = []


def norm_key(x):
    return re.sub(r"[^a-z0-9]", "", str(x).lower().replace("&", "and"))


def canonicalise(df, col, canon, table):
    mp = {norm_key(c): c for c in canon}
    before = df[col].astype("object")
    mapped = before.map(lambda v: mp.get(norm_key(v), np.nan) if pd.notna(v) else np.nan)
    unmapped = before[mapped.isna() & before.notna()]
    assert unmapped.empty, f"{table}.{col}: unmapped values {unmapped.unique()[:5]}"
    changed = int(((before != mapped) & before.notna()).sum())
    log.append(dict(table=table, column=col, action="Mapped to canonical label (case/whitespace/'&' fixes)", rows_changed=changed))
    df[col] = mapped
    return df


don = raw["donors"].copy()
don = canonicalise(don, "sub_area", ZONES, "donors")
sur = raw["surplus_records"].copy()
sur = canonicalise(sur, "food_category", FOOD_CATEGORIES, "surplus_records")
sur = canonicalise(sur, "surplus_reason", REASONS, "surplus_records")
for col in ("packaging_type", "storage_condition"):
    n = int(sur[col].isna().sum())
    sur[col] = sur[col].fillna("Not Recorded")
    log.append(dict(table="surplus_records", column=col, action="Missing optional value -> 'Not Recorded'", rows_changed=n))
for col in ("food_item", "diet_type", "perishability_class"):
    sur[col] = sur[col].str.strip()

rec, vol, ctx = raw["recipients"].copy(), raw["volunteers"].copy(), raw["daily_context"].copy()
col_, dist = raw["collections"].copy(), raw["distributions"].copy()

# types ---------------------------------------------------------------------------------
for df, cols in ((don, ["onboarded_date", "withdrawn_date"]), (vol, ["onboarded_date"]), (ctx, ["date"])):
    for c in cols:
        df[c] = pd.to_datetime(df[c])
for c in ("report_datetime", "prep_datetime"):
    sur[c] = pd.to_datetime(sur[c])
for c in ("assigned_datetime", "pickup_datetime"):
    col_[c] = pd.to_datetime(col_[c])
dist["distribution_datetime"] = pd.to_datetime(dist["distribution_datetime"])
log.append(dict(table="all", column="date/datetime columns", action="Parsed to datetime64", rows_changed=0))
pd.DataFrame(log).to_csv(TAB / "cleaning_log.csv", index=False)
pd.DataFrame(log)

# %% [markdown]
# ## 2. Validation checks
# Each check returns the number of **violating rows** (0 = pass). Critical checks must all pass.

# %%
checks = []


def check(cid, desc, n_bad, critical=True):
    checks.append(dict(check_id=cid, description=desc, violations=int(n_bad),
                       status="PASS" if n_bad == 0 else ("FAIL" if critical else "WARN"), critical=critical))


# V01 schema vs data dictionary
for t, df in raw.items():
    exp = [c[0] for c in TABLES[t]]
    check("V01", f"{t}: columns match data dictionary exactly", 0 if list(df.columns) == exp else 1)
# V02 primary keys
pk = {"donors": "donor_id", "recipients": "recipient_id", "volunteers": "volunteer_id", "daily_context": "date",
      "surplus_records": "surplus_id", "collections": "collection_id", "distributions": "distribution_id"}
for t, k in pk.items():
    check("V02", f"{t}.{k} is unique and non-null", raw[t][k].duplicated().sum() + raw[t][k].isna().sum())
# V03 foreign keys
check("V03", "surplus_records.donor_id exists in donors", (~sur.donor_id.isin(don.donor_id)).sum())
check("V03", "collections.surplus_id exists in surplus_records", (~col_.surplus_id.isin(sur.surplus_id)).sum())
check("V03", "every surplus record has exactly one collection record",
      (col_.surplus_id.duplicated().sum()) + (~sur.surplus_id.isin(col_.surplus_id)).sum())
check("V03", "collections.volunteer_id exists in volunteers (when present)",
      (~col_.volunteer_id.dropna().isin(vol.volunteer_id)).sum())
check("V03", "distributions.collection_id exists in collections", (~dist.collection_id.isin(col_.collection_id)).sum())
check("V03", "distributions.recipient_id exists in recipients (when present)",
      (~dist.recipient_id.dropna().isin(rec.recipient_id)).sum())
# V04 label
for t, df in raw.items():
    check("V04", f"{t}: data_label = '{DATA_LABEL}'", (df.data_label != DATA_LABEL).sum())
# V05-V07 dates
s = sur.merge(don[["donor_id", "onboarded_date", "withdrawn_date"]], on="donor_id")
check("V05", "prep_datetime <= report_datetime", (s.prep_datetime > s.report_datetime).sum())
check("V06", "report date within 2025-11-01..2026-10-31", (~s.report_datetime.dt.normalize().between("2025-11-01", "2026-10-31")).sum())
check("V06", "report date >= donor onboarded_date", (s.report_datetime.dt.normalize() < s.onboarded_date).sum())
check("V06", "report date <= donor withdrawn_date (when withdrawn)",
      (s.withdrawn_date.notna() & (s.report_datetime.dt.normalize() > s.withdrawn_date)).sum())
check("V06", "daily_context covers every day of the window once",
      0 if (len(ctx) == 365 and ctx.date.is_monotonic_increasing and ctx.date.diff().dropna().eq(pd.Timedelta(days=1)).all()) else 1)
c = col_.merge(sur[["surplus_id", "report_datetime", "prep_datetime", "quantity_kg", "declared_safe_window_hours",
                    "donor_id", "diet_type", "food_category", "portion_size_kg"]], on="surplus_id")
c["expiry"] = c.prep_datetime + pd.to_timedelta(c.declared_safe_window_hours, unit="h")
has_a = c.assigned_datetime.notna()
check("V07", "assigned_datetime >= report_datetime", (has_a & (c.assigned_datetime < c.report_datetime)).sum())
has_p = c.pickup_datetime.notna()
check("V07", "pickup_datetime >= assigned_datetime", (has_p & (c.pickup_datetime < c.assigned_datetime)).sum())
# V08 quantities and status logic
check("V08", "quantity_kg between 0.5 and 200", (~sur.quantity_kg.between(0.5, 200)).sum())
check("V08", "est_portions > 0 and declared_safe_window_hours > 0", ((sur.est_portions <= 0) | (sur.declared_safe_window_hours <= 0)).sum())
check("V08", "0 <= qty_collected_kg <= quantity_kg", ((c.qty_collected_kg < 0) | (c.qty_collected_kg > c.quantity_kg + 1e-9)).sum())
collected = c.collection_status.isin(["Collected - Full", "Collected - Partial"])
check("V08", "collected statuses have qty>0, volunteer and pickup time", (collected & ((c.qty_collected_kg <= 0) | c.volunteer_id.isna() | ~has_p)).sum())
check("V08", "non-collected statuses have qty_collected = 0", (~collected & (c.qty_collected_kg != 0)).sum())
check("V08", "'Collected - Full' equals reported quantity", ((c.collection_status == "Collected - Full") & (c.qty_collected_kg != c.quantity_kg)).sum())
check("V08", "'Collected - Partial' is below reported quantity or load-capped", ((c.collection_status == "Collected - Partial") & (c.qty_collected_kg > c.quantity_kg)).sum())
check("V08", "Cancelled/No-Volunteer rows have no volunteer and no pickup", (c.collection_status.isin(["Cancelled by Donor", "Missed - No Volunteer Available"]) & (c.volunteer_id.notna() | has_p)).sum())
check("V08", "Rejected rows carry a logged rejection_reason", ((c.collection_status == "Rejected - Failed Volunteer Safety Check") & c.rejection_reason.isna()).sum())
# V09-V10 safe window logic (donor-declared window; advisory)
check("V09", "collected pickups happen inside the declared safe window", (collected & (c.pickup_datetime > c.expiry)).sum())
check("V10", "'Arrived Beyond Safe Window' rows really are beyond the window", ((c.collection_status == "Missed - Arrived Beyond Safe Window") & (c.pickup_datetime <= c.expiry)).sum())
# V11-V16 distribution logic
d = dist.merge(c[["collection_id", "surplus_id", "pickup_datetime", "expiry", "qty_collected_kg", "diet_type", "food_category",
                  "portion_size_kg", "donor_id"]], on="collection_id").merge(rec, on="recipient_id", how="left", suffixes=("", "_rec"))
delv = d.distribution_status == "Delivered"
check("V11", "Delivered rows have recipient and datetime; Not Delivered rows have neither", ((delv & (d.recipient_id.isna() | d.distribution_datetime.isna())) | (~delv & (d.recipient_id.notna() | d.distribution_datetime.notna()))).sum())
check("V11", "distribution_datetime >= pickup_datetime", (delv & (d.distribution_datetime < d.pickup_datetime)).sum())
check("V11", "distribution_datetime within declared safe window", (delv & (d.distribution_datetime > d.expiry)).sum())
check("V12", "only collected consignments are distributed; every collected consignment has >=1 row",
      (~dist.collection_id.isin(c.loc[collected, "collection_id"])).sum() + (~c.loc[collected, "collection_id"].isin(dist.collection_id)).sum())
check("V12", "at most 2 distribution rows per consignment", (dist.groupby("collection_id").size() > 2).sum())
recon = d.groupby("collection_id").agg(q=("qty_collected_kg", "first"), dq=("qty_distributed_kg", "sum"), w=("wastage_kg", "sum"))
check("V12", "distributed + wastage = collected (tolerance 0.06 kg)", ((recon.q - recon.dq - recon.w).abs() > 0.06).sum())
check("V12", "wastage_reason present whenever wastage > 0.04 kg on a row", ((d.wastage_kg > 0.04) & d.wastage_reason.isna()).sum())


def in_window(r):
    if r.recipient_id is None or pd.isna(r.recipient_id) or pd.isna(r.distribution_datetime):
        return True
    h = r.distribution_datetime.hour + r.distribution_datetime.minute / 60
    for a, b in (("window1_start", "window1_end"), ("window2_start", "window2_end")):
        if pd.notna(r[a]):
            sa, sb = [int(x) for x in r[a].split(":")], [int(x) for x in r[b].split(":")]
            if sa[0] + sa[1] / 60 - 1e-9 <= h <= sb[0] + sb[1] / 60 + 1e-9:
                return True
    return False


check("V13", "deliveries fall inside a recipient acceptance window", (~d.apply(in_window, axis=1)).sum())
check("V14", "Non-Veg food never delivered to Veg-only recipients", (delv & (d.diet_type == "Non-Veg") & (d.diet_acceptance == "Veg-only")).sum())
check("V14", "Cooked meals never delivered to recipients without cooked-food facilities", (delv & (d.food_category == "Cooked Meals") & (d.accepts_cooked_food == "No")).sum())
cap = d[delv].assign(day=lambda x: x.distribution_datetime.dt.date).groupby(["recipient_id", "day"]).beneficiaries_served.sum().reset_index().merge(rec[["recipient_id", "daily_capacity_portions"]], on="recipient_id")
check("V15", "portions served per recipient per day <= daily capacity", (cap.beneficiaries_served > cap.daily_capacity_portions).sum())
exact = np.floor(d.qty_distributed_kg / d.portion_size_kg + 1e-9)
check("V16", "beneficiaries_served = floor(qty / portion size) (+-1 float tolerance)", ((d.beneficiaries_served - exact).abs() > 1).sum())
# V17 geography
for t, a, b in (("donors", "latitude", "longitude"), ("recipients", "latitude", "longitude"), ("volunteers", "home_latitude", "home_longitude")):
    df = raw[t]
    check("V17", f"{t}: coordinates inside study bounding box", (~df[a].between(18.99, 19.07) | ~df[b].between(72.82, 72.88)).sum())
check("V18", "recipient windows are ordered (start < end)", ((rec.window1_start >= rec.window1_end) | (rec.window2_start.notna() & (rec.window2_start >= rec.window2_end))).sum())
check("V19", "distance fields are within 0-8 km", ((col_.collection_distance_km.dropna() > 8).sum() + (dist.transport_distance_km.dropna() > 8).sum()))

# V20 categorical values: no nulls (note: pandas reads the literal text "None" as NaN - avoided by using 'No Rain'/'No Festival')
allowed = {("daily_context", "rain_level"): ["No Rain", "Light/Moderate", "Heavy"], ("daily_context", "wedding_season_flag"): [0, 1],
           ("surplus_records", "diet_type"): ["Veg", "Non-Veg"], ("surplus_records", "perishability_class"): ["High", "Medium", "Low"],
           ("collections", "collection_status"): COLLECTION_STATUSES, ("distributions", "distribution_status"): ["Delivered", "Not Delivered"],
           ("recipients", "diet_acceptance"): ["Any", "Veg-only"], ("donors", "donor_category"): DONOR_CATEGORIES,
           ("volunteers", "shift"): SHIFTS, ("recipients", "recipient_type"): RECIPIENT_TYPES}
for (t, cname), vals in allowed.items():
    check("V20", f"{t}.{cname} only contains allowed values (no NaN)", (~raw[t][cname].isin(vals)).sum())
check("V20", "daily_context.festival_name has no nulls", raw["daily_context"].festival_name.isna().sum())

val = pd.DataFrame(checks)
val.to_csv(TAB / "validation_report.csv", index=False)
print(val[["check_id", "description", "violations", "status"]].to_string(index=False))
n_fail = int((val.status == "FAIL").sum())
print(f"\n{len(val)} checks | PASS={int((val.status=='PASS').sum())} | FAIL={n_fail}")
if n_fail:
    raise SystemExit("Critical validation failures - fix the generator/data before continuing.")

# %% [markdown]
# ## 3. Feature engineering and master tables
# * `master_surplus` - one row per surplus report: donor attributes + collection outcome + distribution totals.
# * `master_distribution` - one row per distribution record: recipient + food + timing attributes.

# %%
def slot(h):
    return ("Morning (06-12)" if 6 <= h < 12 else "Afternoon (12-17)" if 12 <= h < 17
            else "Evening (17-21)" if 17 <= h < 21 else "Late Night (21-24)")


m = sur.merge(don[["donor_id", "donor_name", "donor_category", "sub_area", "latitude", "longitude", "donor_size_class",
                   "fssai_license_declared", "onboarded_date", "donor_status"]], on="donor_id")
m = m.merge(col_.drop(columns="data_label"), on="surplus_id")
agg = dist.groupby("collection_id").agg(delivered_kg=("qty_distributed_kg", "sum"), post_collection_waste_kg=("wastage_kg", "sum"),
                                       portions_served=("beneficiaries_served", "sum"), n_recipients=("recipient_id", "nunique"),
                                       first_delivery=("distribution_datetime", "min"),
                                       waste_reason=("wastage_reason", lambda x: x.dropna().iloc[0] if x.notna().any() else np.nan),
                                       record_complete=("handover_record_complete", lambda x: (x == "Yes").all())).reset_index()
m = m.merge(agg, on="collection_id", how="left")
for c_ in ("delivered_kg", "post_collection_waste_kg", "portions_served", "n_recipients"):
    m[c_] = m[c_].fillna(0)
m["report_date"] = m.report_datetime.dt.normalize()
m["report_hour"] = m.report_datetime.dt.hour
m["day_name"] = m.report_datetime.dt.day_name()
m["weekday_num"] = m.report_datetime.dt.weekday
m["is_weekend"] = (m.weekday_num >= 5).astype(int)
m["week_start"] = (m.report_date - pd.to_timedelta(m.weekday_num, unit="D"))
m["month"] = m.report_datetime.dt.to_period("M").astype(str)
m["time_slot"] = m.report_hour.map(slot)
m["hours_prep_to_report"] = (m.report_datetime - m.prep_datetime).dt.total_seconds() / 3600
m["assign_delay_min"] = (m.assigned_datetime - m.report_datetime).dt.total_seconds() / 60
m["response_min"] = (m.pickup_datetime - m.report_datetime).dt.total_seconds() / 60
m["expiry"] = m.prep_datetime + pd.to_timedelta(m.declared_safe_window_hours, unit="h")
m["window_used_pct"] = ((m.pickup_datetime - m.prep_datetime).dt.total_seconds() / 3600 / m.declared_safe_window_hours * 100)
m["is_collected"] = m.collection_status.isin(["Collected - Full", "Collected - Partial"]).astype(int)
m["is_delivered"] = (m.delivered_kg > 0).astype(int)
m["not_collected_kg"] = (m.quantity_kg - m.qty_collected_kg).round(2)
m["uncollected_reason"] = np.where(m.is_collected.eq(1) & m.collection_status.eq("Collected - Full"), "Fully Collected",
                           np.where(m.collection_status.eq("Collected - Partial"), "Partial collection (remainder left)", m.collection_status))
m["final_outcome"] = np.select(
    [m.is_collected.eq(0), (m.is_collected.eq(1)) & (m.delivered_kg.eq(0)),
     (m.is_collected.eq(1)) & (m.post_collection_waste_kg > 0.04), (m.is_collected.eq(1))],
    ["Not collected", "Collected but not delivered", "Delivered with some wastage", "Delivered in full"], default="Other")
# high-volume flag: Tukey fence on log-quantity within food category (flag only - never deleted)
lq = np.log(m.quantity_kg)
q1, q3 = lq.groupby(m.food_category).transform(lambda x: x.quantile(.25)), lq.groupby(m.food_category).transform(lambda x: x.quantile(.75))
m["is_high_volume_event"] = (lq > q3 + 1.5 * (q3 - q1)).astype(int)
m["recoverable_gap_kg"] = m.quantity_kg - m.delivered_kg  # reported but never delivered
assert abs(m.quantity_kg.sum() - (m.delivered_kg.sum() + m.post_collection_waste_kg.sum() + m.not_collected_kg.sum())) < 1.0

md = dist.merge(rec[["recipient_id", "recipient_name", "recipient_type", "sub_area", "latitude", "longitude", "daily_capacity_portions"]]
                .rename(columns={"sub_area": "recipient_zone", "latitude": "recipient_lat", "longitude": "recipient_lon"}), on="recipient_id", how="left")
md = md.merge(m[["collection_id", "surplus_id", "donor_id", "donor_category", "sub_area", "food_category", "diet_type", "perishability_class",
                 "report_datetime", "pickup_datetime", "quantity_kg", "month"]].rename(columns={"sub_area": "donor_zone"}), on="collection_id")
md["delivery_hour"] = md.distribution_datetime.dt.hour
md["pickup_to_delivery_min"] = (md.distribution_datetime - md.pickup_datetime).dt.total_seconds() / 60

m.to_csv(CLEAN / "master_surplus.csv", index=False)
md.to_csv(CLEAN / "master_distribution.csv", index=False)
for name, df in (("donors", don), ("recipients", rec), ("volunteers", vol), ("daily_context", ctx)):
    df.to_csv(CLEAN / f"{name}.csv", index=False)
sur.to_csv(CLEAN / "surplus_records.csv", index=False)
col_.to_csv(CLEAN / "collections.csv", index=False)
dist.to_csv(CLEAN / "distributions.csv", index=False)
print("master_surplus:", m.shape, "| master_distribution:", md.shape)
print(m.final_outcome.value_counts())
