# %% [markdown]
# # 04 - Advanced Analytics: Redistribution Gaps, Donor Segmentation, Forecasting, Hotspots, Scenarios
# **SYNTHETIC DEMO DATA.** Each technique has an explicit *suitability test* so that machine learning is only
# used where the data justify it:
# * K-Means is reported as meaningful only if silhouette >= 0.25 **and** segments are stable under resampling.
# * Forecasting is judged against naive baselines in a rolling-origin back-test; a model must beat the baseline.
# * Hotspot statistics are exploratory (grid-cell level, approximate coordinates).

# %%
import sys, pathlib, warnings
_here = pathlib.Path(__file__).resolve().parent if "__file__" in globals() else pathlib.Path.cwd()
_scripts = _here if (_here / "common.py").exists() else _here.parent / "scripts"
sys.path.insert(0, str(_scripts))
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, davies_bouldin_score, adjusted_rand_score
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from common import CLEAN, TAB, set_style, save_fig, PALETTE, NAVY, SAGE, TERRA, MUSTARD, ROSE, TEAL, GREY, SEED, ensure_dirs
from schema import ZONES

ensure_dirs(); set_style()
pd.set_option("display.width", 170, "display.max_columns", 40, "display.float_format", "{:,.2f}".format)
m = pd.read_csv(CLEAN / "master_surplus.csv", parse_dates=["report_datetime", "report_date", "onboarded_date"])
md = pd.read_csv(CLEAN / "master_distribution.csv", parse_dates=["distribution_datetime"])
don = pd.read_csv(CLEAN / "donors.csv", parse_dates=["onboarded_date", "withdrawn_date"])
rec = pd.read_csv(CLEAN / "recipients.csv")
ctx = pd.read_csv(CLEAN / "daily_context.csv", parse_dates=["date"])
N_DAYS = len(ctx)

# %% [markdown]
# ## 1. Redistribution gap identification
# **Gap = reported surplus that never reached a recipient.** We decompose it by *where it was lost*
# (never collected vs lost after collection), by zone, by hour-of-day (supply vs recipient availability) and by donor-zone -> recipient-zone flow.

# %%
rep, dlv = m.quantity_kg.sum(), m.delivered_kg.sum()
# (a) decomposition of every reported kg
loss = {
    "Delivered to recipients": dlv,
    "Not collected: no volunteer available": m.loc[m.collection_status == "Missed - No Volunteer Available", "quantity_kg"].sum(),
    "Not collected: arrived beyond safe window": m.loc[m.collection_status == "Missed - Arrived Beyond Safe Window", "quantity_kg"].sum(),
    "Not collected: cancelled by donor": m.loc[m.collection_status == "Cancelled by Donor", "quantity_kg"].sum(),
    "Not collected: failed volunteer safety check": m.loc[m.collection_status == "Rejected - Failed Volunteer Safety Check", "quantity_kg"].sum(),
    "Left behind in partial collections": m.loc[m.collection_status == "Collected - Partial", "not_collected_kg"].sum(),
}
for r_, g in md[md.wastage_reason.notna()].groupby("wastage_reason"):
    loss[f"Lost after collection: {r_}"] = g.wastage_kg.sum()
decomp = pd.Series(loss).rename("kg").to_frame()
decomp["share_of_reported_%"] = decomp.kg / rep * 100
assert abs(decomp.kg.sum() - rep) < 1.0, "decomposition must reconcile to reported kg"
decomp.to_csv(TAB / "gap_decomposition.csv")
print(decomp.round(1))

# (b) zone level
z = m.groupby("sub_area").agg(donors=("donor_id", "nunique"), reports=("surplus_id", "size"), reported_kg=("quantity_kg", "sum"),
                              collected_kg=("qty_collected_kg", "sum"), delivered_kg=("delivered_kg", "sum"),
                              wasted_after_collection_kg=("post_collection_waste_kg", "sum")).reindex(ZONES)
zr = rec.groupby("sub_area").agg(recipients=("recipient_id", "size"), recipient_capacity_portions=("daily_capacity_portions", "sum")).reindex(ZONES).fillna(0)
z = z.join(zr)
z["gap_kg"] = z.reported_kg - z.delivered_kg
z["yield_%"] = z.delivered_kg / z.reported_kg * 100
z["avg_daily_reported_kg"] = z.reported_kg / N_DAYS
z["reported_portions_per_day_per_capacity"] = (m.groupby("sub_area").est_portions.sum().reindex(ZONES) / N_DAYS) / z.recipient_capacity_portions.replace(0, np.nan)
dz = md[md.distribution_status == "Delivered"].groupby("donor_zone").transport_distance_km.mean().reindex(ZONES)
z["avg_delivery_km"] = dz
# share of a zone's delivered food that is delivered into the SAME zone
flow = md[md.distribution_status == "Delivered"].pivot_table(index="donor_zone", columns="recipient_zone", values="qty_distributed_kg", aggfunc="sum", fill_value=0).reindex(index=ZONES, columns=ZONES, fill_value=0)
z["delivered_within_own_zone_%"] = [flow.loc[a, a] / flow.loc[a].sum() * 100 if flow.loc[a].sum() else np.nan for a in ZONES]
z.to_csv(TAB / "gap_by_zone.csv"); flow.to_csv(TAB / "flow_matrix_kg.csv")
print(z.round(1))

# (c) supply vs recipient availability by hour of day
def open_hours(r):
    hrs = np.zeros(24)
    for a, b in ((r.window1_start, r.window1_end), (r.window2_start, r.window2_end)):
        if isinstance(a, str):
            s, e = [int(x) / 1 for x in a.split(":")], [int(x) for x in b.split(":")]
            s_, e_ = s[0] + s[1] / 60, e[0] + e[1] / 60
            for h in range(24):
                hrs[h] += max(0, min(e_, h + 1) - max(s_, h))
    return hrs


open_share = np.vstack([open_hours(r) * r.daily_capacity_portions / max(1e-9, 1) for r in rec.itertuples()])  # capacity-hours
rec_open_cap = pd.Series(open_share.sum(axis=0), name="capacity_weighted_open_hours")
rec_open_n = pd.Series(np.vstack([open_hours(r) for r in rec.itertuples()]).sum(axis=0), name="recipient_open_equivalents")
supply = m.groupby("report_hour").agg(reported_kg=("quantity_kg", "sum"), reports=("surplus_id", "size"), delivered_kg=("delivered_kg", "sum"))
hourly = pd.DataFrame({"hour": range(24)}).join(supply, on="hour").fillna(0).join(rec_open_n, on="hour")
hourly["yield_%"] = np.where(hourly.reported_kg > 0, hourly.delivered_kg / hourly.reported_kg.replace(0, np.nan) * 100, np.nan)
hourly.to_csv(TAB / "hourly_supply_vs_recipient_availability.csv", index=False)
fig, ax = plt.subplots(1, 2, figsize=(14, 4.4))
ax[0].bar(hourly.hour, hourly.reported_kg / 1000, color=NAVY, label="Reported surplus (t)")
a2 = ax[0].twinx(); a2.step(hourly.hour, hourly.recipient_open_equivalents, where="mid", color=TERRA, lw=2, label="Recipients open (count-equivalents)"); a2.grid(False)
ax[0].set_xlabel("Hour of day"); ax[0].set_title("Supply vs availability: when food appears vs when recipients can take it")
h1, l1 = ax[0].get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels(); ax[0].legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8)
sns.heatmap(flow / 1000, annot=True, fmt=".1f", cmap=sns.light_palette(TEAL, as_cmap=True), ax=ax[1], cbar_kws={"label": "tonnes delivered"})
ax[1].set_title("Where food travels: donor zone (rows) -> recipient zone (cols)"); ax[1].set_ylabel(""); ax[1].set_xlabel("")
plt.setp(ax[1].get_xticklabels(), rotation=30, ha="right")
fig.tight_layout(); save_fig(fig, "10_supply_vs_recipient_availability.png")

fig, ax = plt.subplots(1, 2, figsize=(14, 4.6))
d_ = decomp.sort_values("kg")
ax[0].barh(d_.index, d_.kg / 1000, color=[SAGE if "Delivered" in i else TERRA if "Not collected" in i or "Left" in i else MUSTARD for i in d_.index])
for i, (k, r) in enumerate(d_.iterrows()):
    ax[0].text(r.kg / 1000, i, f" {r['share_of_reported_%']:.1f}%", va="center", fontsize=8)
ax[0].set_title("Where every reported kg ended up (tonnes, % of reported)"); ax[0].set_xlim(0, d_.kg.max() / 1000 * 1.18)
zz = z.sort_values("gap_kg")
ax[1].barh(zz.index, zz.delivered_kg / 1000, color=SAGE, label="Delivered"); ax[1].barh(zz.index, zz.gap_kg / 1000, left=zz.delivered_kg / 1000, color=TERRA, label="Gap (not delivered)")
ax[1].set_title("Delivered vs gap by donor zone (tonnes)"); ax[1].legend(fontsize=8)
fig.tight_layout(); save_fig(fig, "11_gap_decomposition_zones.png")

# %% [markdown]
# ## 2. K-Means donor segmentation (only if statistically meaningful)
# Features describe **donor behaviour only** (not outcomes) so segments are actionable at onboarding time:
# typical batch size, reporting frequency, variability, late-night share, high-perishability share, weekend share.
# Outcomes (collection / yield) are used afterwards to *profile* segments.

# %%
end = pd.Timestamp("2026-10-31")
g = m.groupby("donor_id")
f = pd.DataFrame({"reports": g.size(), "mean_kg": g.quantity_kg.mean(), "sd_kg": g.quantity_kg.std(),
                  "late_night_share": g.apply(lambda x: (x.report_hour >= 21).mean()),
                  "high_perishability_share": g.apply(lambda x: (x.perishability_class == "High").mean()),
                  "weekend_share": g.is_weekend.mean()})
f = f.join(don.set_index("donor_id")[["onboarded_date", "withdrawn_date", "donor_category", "sub_area"]])
last = f.withdrawn_date.fillna(end); first = f.onboarded_date.clip(lower=pd.Timestamp("2025-11-01"))
f["months_active"] = ((last - first).dt.days + 1) / 30.4
f["reports_per_month"] = f.reports / f.months_active
f["cv_kg"] = f.sd_kg / f.mean_kg
f["log_mean_kg"] = np.log(f.mean_kg)
FEATS = ["log_mean_kg", "reports_per_month", "cv_kg", "late_night_share", "high_perishability_share", "weekend_share"]
fe = f[f.reports >= 10].copy()
print(f"Donors with >=10 reports used for clustering: {len(fe)} of {len(f)}")
Z = StandardScaler().fit_transform(fe[FEATS])
rows = []
for k in range(2, 8):
    km = KMeans(k, n_init=20, random_state=SEED).fit(Z)
    rows.append(dict(k=k, inertia=km.inertia_, silhouette=silhouette_score(Z, km.labels_), davies_bouldin=davies_bouldin_score(Z, km.labels_)))
ks = pd.DataFrame(rows); ks.to_csv(TAB / "kmeans_model_selection.csv", index=False); print(ks)
best_k = int(ks.loc[ks.silhouette.idxmax(), "k"]); best_sil = float(ks.silhouette.max())
km = KMeans(best_k, n_init=50, random_state=SEED).fit(Z); fe["cluster"] = km.labels_
# stability: re-cluster 100 random 80% subsamples, compare with full-sample labels on the same donors (ARI)
rs = np.random.default_rng(SEED); aris = []
for _ in range(100):
    idx = rs.choice(len(fe), int(len(fe) * .8), replace=False)
    sub = KMeans(best_k, n_init=10, random_state=int(rs.integers(1e6))).fit(Z[idx])
    aris.append(adjusted_rand_score(km.labels_[idx], sub.labels_))
stab = float(np.mean(aris))
ari_cat = adjusted_rand_score(fe.donor_category, fe.cluster)
verdict = ("MEANINGFUL: silhouette >= 0.25 and stable (ARI >= 0.75)" if best_sil >= .25 and stab >= .75 else
           "WEAK: do not use segments for decisions; fall back to donor_category")
print(f"best k={best_k} | silhouette={best_sil:.3f} | bootstrap ARI={stab:.3f} | ARI vs donor_category={ari_cat:.3f}\n-> {verdict}")

# name segments from the two most distinctive centroid z-scores (deterministic, data-driven wording)
cent = pd.DataFrame(km.cluster_centers_, columns=FEATS)
WORDS = {"log_mean_kg": ("Large-batch", "Small-batch"), "reports_per_month": ("Frequent", "Occasional"),
         "cv_kg": ("Variable-size", "Consistent-size"), "late_night_share": ("Late-night", "Daytime/evening"),
         "high_perishability_share": ("High-perishability", "Low-perishability"), "weekend_share": ("Weekend-heavy", "Weekday-only")}
names = {}
for c_ in cent.index:
    top = cent.loc[c_].abs().sort_values(ascending=False).index[:2]
    names[c_] = " / ".join(WORDS[t][0 if cent.loc[c_, t] > 0 else 1] for t in top)
if len(set(names.values())) < len(names):  # ensure unique labels
    names = {c_: f"{n} (S{c_ + 1})" for c_, n in names.items()}
fe["segment"] = fe.cluster.map(names)
prof = fe.groupby("segment").agg(donors=("reports", "size"), reports=("reports", "sum"), mean_kg=("mean_kg", "mean"), reports_per_month=("reports_per_month", "mean"),
                                 cv_kg=("cv_kg", "mean"), late_night_share=("late_night_share", "mean"), weekend_share=("weekend_share", "mean"),
                                 high_perishability_share=("high_perishability_share", "mean"))
mm = m.merge(fe[["segment"]], left_on="donor_id", right_index=True)
out = mm.groupby("segment").agg(total_kg=("quantity_kg", "sum"), collected_kg=("qty_collected_kg", "sum"), delivered_kg=("delivered_kg", "sum"))
out["kg_collection_rate_%"] = out.collected_kg / out.total_kg * 100; out["kg_yield_%"] = out.delivered_kg / out.total_kg * 100
prof = prof.join(out); prof["dominant_donor_category"] = fe.groupby("segment").donor_category.agg(lambda x: x.value_counts().index[0])
prof["share_in_dominant_category_%"] = fe.groupby("segment").donor_category.agg(lambda x: x.value_counts(normalize=True).iloc[0] * 100)
prof.to_csv(TAB / "kmeans_segment_profiles.csv"); print(prof.round(2).T)
f.join(fe[["segment"]]).reset_index().to_csv(TAB / "donor_features_segments.csv", index=False)

pc = PCA(2, random_state=SEED).fit(Z); P = pc.transform(Z)
fig, ax = plt.subplots(1, 3, figsize=(17, 4.6))
ax[0].plot(ks.k, ks.silhouette, "o-", color=NAVY); ax[0].axhline(.25, color=TERRA, ls="--", lw=1); ax[0].set_title("Silhouette by k (dashed = 0.25 threshold)"); ax[0].set_xlabel("k")
for i, s_ in enumerate(sorted(fe.segment.unique())):
    sel = (fe.segment == s_).values
    ax[1].scatter(P[sel, 0], P[sel, 1], s=28, color=PALETTE[i % len(PALETTE)], label=f"{s_} (n={sel.sum()})", alpha=.85, edgecolor="white", lw=.4)
ax[1].set_title(f"Donor segments (PCA view, {pc.explained_variance_ratio_.sum()*100:.0f}% variance)"); ax[1].legend(fontsize=7)
ct = pd.crosstab(fe.segment, fe.donor_category, normalize="index") * 100
sns.heatmap(ct, annot=True, fmt=".0f", cmap=sns.light_palette(SAGE, as_cmap=True), ax=ax[2], cbar=False); ax[2].set_title("Segment composition by donor category (%)"); ax[2].set_ylabel(""); ax[2].set_xlabel("")
plt.setp(ax[2].get_xticklabels(), rotation=35, ha="right")
fig.tight_layout(); save_fig(fig, "12_kmeans_donor_segments.png")
pd.Series({"n_donors_clustered": len(fe), "best_k": best_k, "silhouette": best_sil, "bootstrap_ARI_mean": stab, "ARI_vs_donor_category": ari_cat, "verdict": verdict}).to_csv(TAB / "kmeans_summary.csv")

# %% [markdown]
# ## 3. Surplus forecasting (back-tested, baseline-controlled)
# **Suitability:** 365 daily observations (52 full weeks) support *weekly* seasonality and a back-test, but only
# **one** annual cycle - so annual seasonality and festival effects cannot be validated. The forecast below is therefore a
# 14-day *operational-planning demonstration*, not a prediction of real-world surplus.

# %%
d = pd.read_csv(TAB / "daily_series.csv", parse_dates=["date"])
d = d.merge(ctx[["date", "wedding_season_flag", "monsoon_season_flag"]], on="date")
d["festival"] = (d.festival_name != "No Festival").astype(int)
d["t"] = np.arange(len(d)); d["dow"] = d.date.dt.weekday
y = d.kg.values


def design(df, last_active):
    X = pd.get_dummies(df.dow, dtype=float).reindex(columns=range(7), fill_value=0.0)
    X.columns = [f"dow{i}" for i in range(7)]
    X["active_donors"] = last_active if last_active is not None else df.active_donors.values
    X["festival"] = df.festival.values; X["wedding"] = df.wedding_season_flag.values; X["monsoon"] = df.monsoon_season_flag.values
    return X.values.astype(float)


def f_naive7(tr, h, **k): return np.array([tr[-7 + (i % 7)] for i in range(h)])
def f_mean4w(tr, h, **k):
    """Mean of the same weekday over the previous 4 weeks."""
    return np.array([np.mean([tr[len(tr) - 7 * j + (i % 7)] for j in range(1, 5)]) for i in range(h)])
def f_hw(tr, h, **k):
    fit = ExponentialSmoothing(tr, trend="add", damped_trend=True, seasonal="add", seasonal_periods=7).fit()
    return fit.forecast(h)
def f_reg(tr, h, df_tr=None, df_te=None, **k):
    la = df_tr.active_donors.values[-1]
    Xtr, Xte = design(df_tr, None), design(df_te, la)
    beta, *_ = np.linalg.lstsq(Xtr, tr, rcond=None)
    return np.clip(Xte @ beta, 0, None)


MODELS = {"Seasonal naive (same weekday last week)": f_naive7, "Mean of same weekday, last 4 weeks": f_mean4w,
          "Holt-Winters (damped trend, weekly season)": f_hw, "Regression (weekday + calendar flags + active donors)": f_reg}
H = 7
ORIGINS = list(range(len(d) - 16 * 7, len(d) - H + 1, 7))
bt = []
for t0 in ORIGINS:
    tr, te = y[:t0], y[t0:t0 + H]
    for name, fn in MODELS.items():
        pred = fn(tr, H, df_tr=d.iloc[:t0], df_te=d.iloc[t0:t0 + H])
        for i in range(H):
            bt.append(dict(model=name, origin=d.date[t0], date=d.date[t0 + i], horizon=i + 1, actual=te[i], pred=float(pred[i])))
bt = pd.DataFrame(bt); bt["err"] = bt.actual - bt.pred
naive_mae = bt[bt.model.str.startswith("Seasonal naive")].err.abs().mean()
score = bt.groupby("model").apply(lambda x: pd.Series({"MAE_kg": x.err.abs().mean(), "RMSE_kg": np.sqrt((x.err ** 2).mean()),
                                                       "WAPE_%": x.err.abs().sum() / x.actual.sum() * 100, "bias_kg": x.err.mean()}))
score["MAE_vs_seasonal_naive_%"] = (1 - score.MAE_kg / naive_mae) * 100
score = score.sort_values("MAE_kg"); score.to_csv(TAB / "forecast_backtest_scores.csv"); print(score.round(2))
bt.to_csv(TAB / "forecast_backtest_detail.csv", index=False)
best = score.index[0]
beats = bool(score.loc[best, "MAE_vs_seasonal_naive_%"] > 5 and best != "Seasonal naive (same weekday last week)")
print(f"Best model: {best} | beats seasonal naive by >5%: {beats}")

# final 14-day forecast with empirical 80% interval from back-test residuals of the best model
FH = 14
fut_dates = pd.date_range(d.date.max() + pd.Timedelta(days=1), periods=FH)
fut = pd.DataFrame({"date": fut_dates, "dow": fut_dates.weekday, "festival": 0, "wedding_season_flag": 0,
                    "monsoon_season_flag": 0, "active_donors": d.active_donors.iloc[-1]})
pred = MODELS[best](y, FH, df_tr=d, df_te=fut)
res = bt[bt.model == best].err
lo_q, hi_q = res.quantile(.10), res.quantile(.90)
fc = pd.DataFrame({"date": fut_dates, "forecast_kg": pred, "lower_80_kg": np.clip(pred + lo_q, 0, None), "upper_80_kg": pred + hi_q, "model": best})
fc.to_csv(TAB / "forecast_next_14_days.csv", index=False)
print(fc.round(1))

fig, ax = plt.subplots(1, 2, figsize=(15, 4.4))
ax[0].plot(d.date.iloc[-84:], d.kg.iloc[-84:], color=GREY, lw=1.2, label="Actual")
bb = bt[bt.model == best]; ax[0].plot(bb.date, bb.pred, color=TERRA, lw=1.5, label=f"Back-test prediction (7-day horizon)")
ax[0].plot(fc.date, fc.forecast_kg, color=NAVY, lw=2, label="Next 14 days"); ax[0].fill_between(fc.date, fc.lower_80_kg, fc.upper_80_kg, color=NAVY, alpha=.15, label="80% interval")
ax[0].set_title(f"Surplus forecast: {best.split('(')[0].strip()}"); ax[0].legend(fontsize=7); ax[0].tick_params(axis="x", rotation=20)
sc = score.reset_index(); ax[1].barh(sc.model.str.replace(r" \(.*\)", "", regex=True), sc.MAE_kg, color=[SAGE if i == 0 else GREY for i in range(len(sc))])
ax[1].set_title("Back-test MAE (kg/day), 16 weekly origins; lower is better"); ax[1].invert_yaxis()
fig.tight_layout(); save_fig(fig, "13_forecast_backtest.png")
pd.Series({"best_model": best, "beats_seasonal_naive_by_>5pct": beats, "backtest_origins": len(ORIGINS), "interval": "empirical 10-90% of back-test errors"}).to_csv(TAB / "forecast_summary.csv")

# %% [markdown]
# ## 4. Geographical hotspot analysis
# Donor coordinates are *approximate* (zone centroid + jitter), so only ~300 m grid cells are used and results are exploratory.
# Global Moran's I (k=4 nearest neighbours, 999 permutations) tests whether unserved surplus is spatially clustered.

# %%
STEP, LAT0, LON0 = 0.003, 18.995, 72.830
dm = m.groupby("donor_id").agg(reported_kg=("quantity_kg", "sum"), collected_kg=("qty_collected_kg", "sum"), delivered_kg=("delivered_kg", "sum"), reports=("surplus_id", "size")).reset_index().merge(
    don[["donor_id", "latitude", "longitude", "sub_area", "donor_category"]], on="donor_id")
dm["gy"] = np.floor((dm.latitude - LAT0) / STEP).astype(int); dm["gx"] = np.floor((dm.longitude - LON0) / STEP).astype(int)
cells = dm.groupby(["gy", "gx"]).agg(donors=("donor_id", "size"), reported_kg=("reported_kg", "sum"), collected_kg=("collected_kg", "sum"), delivered_kg=("delivered_kg", "sum"),
                                     zone=("sub_area", lambda x: x.value_counts().index[0])).reset_index()
cells["lat"] = LAT0 + (cells.gy + .5) * STEP; cells["lon"] = LON0 + (cells.gx + .5) * STEP
cells["unserved_kg"] = cells.reported_kg - cells.delivered_kg; cells["unserved_rate_%"] = cells.unserved_kg / cells.reported_kg * 100


def hav(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2); a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


cells["nearest_recipient_km"] = [min(hav(r.lat, r.lon, a, b) for a, b in zip(rec.latitude, rec.longitude)) for r in cells.itertuples()]
cells["recipients_within_1km"] = [sum(hav(r.lat, r.lon, a, b) <= 1.0 for a, b in zip(rec.latitude, rec.longitude)) for r in cells.itertuples()]
q75 = cells.unserved_kg.quantile(.75)
cells["gap_hotspot"] = ((cells.unserved_kg >= q75) & (cells.donors >= 2)).astype(int)


def morans_i(v, xy, k=4, n_perm=999, seed=SEED):
    v = np.asarray(v, float); n = len(v); zc = v - v.mean()
    D = np.sqrt(((xy[:, None, :] - xy[None, :, :]) ** 2).sum(-1)); W = np.zeros((n, n))
    for i in range(n):
        W[i, np.argsort(D[i])[1:k + 1]] = 1 / k
    I = n / W.sum() * (zc @ W @ zc) / (zc @ zc)
    r = np.random.default_rng(seed); sims = np.array([n / W.sum() * (zc[p] @ W @ zc[p]) / (zc @ zc) for p in (r.permutation(n) for _ in range(n_perm))])
    return I, -1 / (n - 1), (np.sum(sims >= I) + 1) / (n_perm + 1)


xy = cells[["lat", "lon"]].values
mi = {}
for col in ("unserved_kg", "unserved_rate_%"):
    I, EI, p = morans_i(cells[col], xy); mi[col] = dict(morans_I=I, expected_I=EI, p_value_one_sided=p)
mi = pd.DataFrame(mi).T; mi.to_csv(TAB / "morans_i.csv"); print(mi.round(3)); print(f"grid cells with donors: {len(cells)}")
cells.sort_values("unserved_kg", ascending=False).to_csv(TAB / "hotspot_grid_cells.csv", index=False)

fig, ax = plt.subplots(1, 2, figsize=(14, 5.6))
sc_ = ax[0].scatter(cells.lon, cells.lat, s=cells.unserved_kg / cells.unserved_kg.max() * 900 + 20, c=cells["unserved_rate_%"], cmap=sns.light_palette(TERRA, as_cmap=True), edgecolor=GREY, lw=.6, alpha=.9)
ax[0].scatter(rec.longitude, rec.latitude, marker="^", s=70, color=TEAL, edgecolor="white", label="Recipient (synthetic)", zorder=5)
for zn, (la, lo) in {"Dadar W": (19.0185, 72.8415), "Dadar E": (19.0225, 72.8490), "Shivaji Pk": (19.0275, 72.8380), "Matunga": (19.0270, 72.8570), "Mahim": (19.0405, 72.8405), "Dharavi fringe": (19.0400, 72.8535)}.items():
    ax[0].annotate(zn, (lo, la), fontsize=7, color=GREY, ha="center", xytext=(0, -14), textcoords="offset points")
ax[0].set_title("Unserved surplus by 300 m cell (size = kg, colour = % unserved)"); ax[0].set_xlabel("Longitude"); ax[0].set_ylabel("Latitude"); ax[0].legend(fontsize=8, loc="lower right")
plt.colorbar(sc_, ax=ax[0], label="% of reported kg not delivered", shrink=.8)
hs = cells[cells.gap_hotspot == 1]
ax[1].scatter(cells.nearest_recipient_km, cells.unserved_kg / 1000, s=40, color=GREY, alpha=.7, label="Grid cell")
ax[1].scatter(hs.nearest_recipient_km, hs.unserved_kg / 1000, s=70, color=TERRA, label="Gap hotspot (top quartile kg)")
ax[1].set_xlabel("Distance from cell centre to nearest recipient (km)"); ax[1].set_ylabel("Unserved surplus (tonnes)"); ax[1].set_title("Is the gap explained by distance to recipients?"); ax[1].legend(fontsize=8)
rho_d = cells[["nearest_recipient_km", "unserved_kg"]].corr(method="spearman").iloc[0, 1]; ax[1].text(.02, .95, f"Spearman rho = {rho_d:.2f}", transform=ax[1].transAxes, fontsize=9, va="top")
fig.tight_layout(); save_fig(fig, "14_hotspot_map.png")

# %% [markdown]
# ## 5. Indicative impact scenarios (transparent arithmetic - not predictions)
# Recoverable kg are computed from *observed* conversion rates in this dataset. Each scenario states its assumption explicitly.

# %%
late = m[m.time_slot == "Late Night (21-24)"]
conv_late = late.delivered_kg.sum() / late.qty_collected_kg.sum() if late.qty_collected_kg.sum() else 0
miss_vol_kg = m.loc[m.collection_status == "Missed - No Volunteer Available", "quantity_kg"].sum()
miss_vol_late = m.loc[(m.collection_status == "Missed - No Volunteer Available") & (m.time_slot == "Late Night (21-24)"), "quantity_kg"].sum()
win_waste = md.loc[md.wastage_reason == "No Recipient Window Within Safe Time", "wastage_kg"].sum()
ppk = m.portions_served.sum() / dlv  # portions per delivered kg (observed)
sc_rows = []
def scen(name, add_kg, assumption):
    sc_rows.append(dict(scenario=name, extra_delivered_kg=add_kg, extra_portions=add_kg * ppk, new_yield_pct=(dlv + add_kg) / rep * 100,
                        uplift_pts=add_kg / rep * 100, assumption=assumption))
scen("A1: halve 'no volunteer' misses", miss_vol_kg * .5 * (dlv / m.qty_collected_kg.sum()), "50% of misses become collections; they convert to delivery at the observed overall delivery efficiency")
scen("A2: halve late-night 'no volunteer' misses", miss_vol_late * .5 * conv_late, "extra Late-shift volunteers; converts at the observed late-night delivery efficiency")
load_left = m.loc[(m.collection_status == "Collected - Partial") & (m.partial_reason == "Vehicle/Load Capacity"), "not_collected_kg"].sum()
scen("A3: second trip / van for loads above vehicle capacity", load_left * .5 * (dlv / m.qty_collected_kg.sum()), "half of the kg left behind for load-capacity reasons is collected and converts at the observed delivery efficiency")
scen("B: halve 'no recipient window' wastage", win_waste * .5, "two recipients agree to extended evening/night acceptance windows; recovered kg delivered in full")
scen("C: A1 + B combined (not additive-overlap adjusted)", miss_vol_kg * .5 * (dlv / m.qty_collected_kg.sum()) + win_waste * .5, "simple sum; real overlap would make the true gain somewhat smaller")
scn = pd.DataFrame(sc_rows); scn.to_csv(TAB / "impact_scenarios.csv", index=False); scn.round(2)
