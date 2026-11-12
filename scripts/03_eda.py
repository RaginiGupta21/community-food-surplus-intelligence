# %% [markdown]
# # 03 - Exploratory Data Analysis and Statistical Testing
# **SYNTHETIC DEMO DATA** - results demonstrate the analytical method; they are *not* findings about real
# Mumbai donors or NGOs. Every figure carries a watermark to prevent mis-quoting.
#
# Sections: KPIs -> descriptive statistics -> food / donor / reason analysis -> time trends ->
# collection efficiency -> redistribution efficiency -> hypothesis tests and a logistic model.

# %%
import sys, pathlib
_here = pathlib.Path(__file__).resolve().parent if "__file__" in globals() else pathlib.Path.cwd()
_scripts = _here if (_here / "common.py").exists() else _here.parent / "scripts"
sys.path.insert(0, str(_scripts))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import statsmodels.api as sm
from common import CLEAN, TAB, FIG, set_style, save_fig, PALETTE, NAVY, SAGE, TERRA, MUSTARD, ROSE, TEAL, GREY, BG, ensure_dirs
from schema import FOOD_CATEGORIES, DONOR_CATEGORIES, ZONES

ensure_dirs(); set_style()
pd.set_option("display.width", 170, "display.max_columns", 40, "display.float_format", "{:,.2f}".format)
dt = ["report_datetime", "prep_datetime", "assigned_datetime", "pickup_datetime", "report_date", "week_start", "expiry", "first_delivery", "onboarded_date"]
m = pd.read_csv(CLEAN / "master_surplus.csv", parse_dates=dt)
md = pd.read_csv(CLEAN / "master_distribution.csv", parse_dates=["distribution_datetime", "pickup_datetime", "report_datetime"])
don = pd.read_csv(CLEAN / "donors.csv", parse_dates=["onboarded_date", "withdrawn_date"])
rec = pd.read_csv(CLEAN / "recipients.csv")
ctx = pd.read_csv(CLEAN / "daily_context.csv", parse_dates=["date"])
m = m.merge(ctx[["date", "rain_level", "festival_name", "wedding_season_flag"]], left_on="report_date", right_on="date", how="left").drop(columns="date")
SLOTS = ["Afternoon (12-17)", "Evening (17-21)", "Late Night (21-24)"]  # no reports are made before noon in this dataset
print(m.shape)

# %% [markdown]
# ## 1. Headline KPIs
# Definitions (all in kg unless stated):
# * **Collection rate** = collected kg / reported kg
# * **Redistribution yield** = delivered kg / reported kg (end-to-end)
# * **Delivery efficiency** = delivered kg / collected kg
# * **Waste at source (not collected)** = reported kg - collected kg

# %%
rep, col, dlv = m.quantity_kg.sum(), m.qty_collected_kg.sum(), m.delivered_kg.sum()
resp = m.loc[m.is_collected == 1, "response_min"]
kpi = pd.Series({
    "Surplus reports": len(m), "Donors that reported at least once": m.donor_id.nunique(),
    "Reported surplus (kg)": rep, "Collected (kg)": col, "Delivered to recipients (kg)": dlv,
    "Wasted after collection (kg)": m.post_collection_waste_kg.sum(), "Never collected (kg)": m.not_collected_kg.sum(),
    "Portions served": m.portions_served.sum(), "Collection rate (kg %)": col / rep * 100,
    "Redistribution yield (kg %)": dlv / rep * 100, "Delivery efficiency (kg %)": dlv / col * 100,
    "Reports with a collection (count %)": m.is_collected.mean() * 100,
    "Median report->pickup (min)": resp.median(), "90th pct report->pickup (min)": resp.quantile(.9),
    "Pickups within 60 min (%)": (resp <= 60).mean() * 100,
    "Hand-over records complete (%)": (md.loc[md.distribution_status == "Delivered", "handover_record_complete"] == "Yes").mean() * 100})
kpi.to_frame("value").to_csv(TAB / "kpis.csv")
kpi.to_frame("value")

# %% [markdown]
# ## 2. Descriptive statistics

# %%
def desc(g):
    x = m.groupby(g).quantity_kg
    out = pd.DataFrame({"reports": x.size(), "total_kg": x.sum(), "mean_kg": x.mean(), "median_kg": x.median(),
                        "std_kg": x.std(), "p90_kg": x.quantile(.9), "max_kg": x.max()})
    out["share_of_kg_%"] = out.total_kg / out.total_kg.sum() * 100
    return out.sort_values("total_kg", ascending=False)


by_donor_cat, by_food = desc("donor_category"), desc("food_category")
by_donor_cat.to_csv(TAB / "desc_by_donor_category.csv"); by_food.to_csv(TAB / "desc_by_food_category.csv")
desc("sub_area").to_csv(TAB / "desc_by_zone.csv")
print(by_donor_cat.round(1)); print(by_food.round(1))
print("\nSkewness of quantity_kg:", round(m.quantity_kg.skew(), 2), "| log-quantity skewness:", round(np.log(m.quantity_kg).skew(), 2))

# %% [markdown]
# ## 3. Food category, donor and surplus-reason analysis

# %%
fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
# 3a mass flow
steps = ["Reported", "Never\ncollected", "Collected", "Wasted after\ncollection", "Delivered"]
vals = [rep, m.not_collected_kg.sum(), col, m.post_collection_waste_kg.sum(), dlv]
cols = [NAVY, TERRA, SAGE, TERRA, TEAL]
ax[0].bar(steps, vals, color=cols)
for i, v in enumerate(vals):
    ax[0].text(i, v, f"{v/1000:,.1f}t\n({v/rep*100:.0f}%)", ha="center", va="bottom", fontsize=8)
ax[0].set_title("Food flow: reported -> delivered (kg)"); ax[0].set_ylim(0, rep * 1.2)
# 3b food category
b = by_food.sort_values("total_kg")
ax[1].barh(b.index, b.total_kg / 1000, color=SAGE)
for i, (k, r) in enumerate(b.iterrows()):
    ax[1].text(r.total_kg / 1000, i, f" {r['share_of_kg_%']:.0f}%", va="center", fontsize=8)
ax[1].set_title("Reported surplus by food category (tonnes)"); ax[1].set_xlim(0, b.total_kg.max() / 1000 * 1.15)
# 3c donor category
b = by_donor_cat.sort_values("total_kg")
ax[2].barh(b.index, b.total_kg / 1000, color=NAVY)
for i, (k, r) in enumerate(b.iterrows()):
    ax[2].text(r.total_kg / 1000, i, f" {r['share_of_kg_%']:.0f}%", va="center", fontsize=8)
ax[2].set_title("Reported surplus by donor category (tonnes)"); ax[2].set_xlim(0, b.total_kg.max() / 1000 * 1.15)
fig.tight_layout(); save_fig(fig, "01_flow_food_donor_category.png")

# donor concentration (Pareto) --------------------------------------------------------------
dk = m.groupby("donor_id").quantity_kg.sum().sort_values(ascending=False)
cum = dk.cumsum() / dk.sum() * 100
top20 = cum.iloc[int(np.ceil(len(dk) * .2)) - 1]
gini = (2 * np.sum((np.arange(1, len(dk) + 1)) * np.sort(dk.values)) / (len(dk) * dk.sum())) - (len(dk) + 1) / len(dk)
fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(range(len(dk)), dk.values / 1000, color=SAGE, width=1)
ax2 = ax.twinx(); ax2.plot(range(len(dk)), cum.values, color=TERRA, lw=2); ax2.set_ylim(0, 105); ax2.grid(False)
ax.set_xlabel("Donors ranked by reported kg"); ax.set_ylabel("Tonnes"); ax2.set_ylabel("Cumulative share (%)")
ax.set_title(f"Donor concentration: top 20% of donors = {top20:.0f}% of kg (Gini {gini:.2f})")
fig.tight_layout(); save_fig(fig, "02_donor_pareto.png")
pd.Series({"top_20pct_donors_share_of_kg": top20, "gini_coefficient": gini}).to_csv(TAB / "donor_concentration.csv")

# reasons x donor category -----------------------------------------------------------------
ct = pd.crosstab(m.donor_category, m.surplus_reason, normalize="index") * 100
fig, ax = plt.subplots(figsize=(11, 4.2))
sns.heatmap(ct, annot=True, fmt=".0f", cmap=sns.light_palette(NAVY, as_cmap=True), cbar_kws={"label": "% of reports"}, ax=ax, linewidths=.5)
ax.set_title("Why surplus arises: reason mix by donor category (% of that category's reports)"); ax.set_xlabel(""); ax.set_ylabel("")
plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
fig.tight_layout(); save_fig(fig, "03_reason_by_donor_category.png")
rk = m.groupby("surplus_reason").agg(reports=("surplus_id", "size"), kg=("quantity_kg", "sum")).sort_values("kg", ascending=False)
rk["kg_share_%"] = rk.kg / rk.kg.sum() * 100
rk.to_csv(TAB / "reasons_summary.csv"); rk.round(1)

# %% [markdown]
# ## 4. Time trends (daily, weekly, monthly)
# Surplus volume grows in the synthetic data partly because donors are *onboarded progressively*. To avoid
# mistaking recruitment for behaviour change we also compute **kg per active donor**.

# %%
days = ctx[["date"]].copy()
days["active_donors"] = [int(((don.onboarded_date <= d) & (don.withdrawn_date.isna() | (don.withdrawn_date >= d))).sum()) for d in days.date]
daily = m.groupby("report_date").agg(kg=("quantity_kg", "sum"), reports=("surplus_id", "size"), delivered_kg=("delivered_kg", "sum")).reindex(days.date, fill_value=0).rename_axis("date").reset_index()
daily = daily.merge(days, on="date").merge(ctx[["date", "festival_name", "rain_level", "is_weekend"]], on="date")
daily["kg_per_active_donor"] = daily.kg / daily.active_donors
daily["kg_ma7"] = daily.kg.rolling(7, min_periods=1).mean()
daily.to_csv(TAB / "daily_series.csv", index=False)
monthly = m.groupby("month").agg(reports=("surplus_id", "size"), kg=("quantity_kg", "sum"), collected_kg=("qty_collected_kg", "sum"), delivered_kg=("delivered_kg", "sum")).reset_index()
monthly["active_donors_end"] = [int(days[days.date.dt.to_period("M").astype(str) == mo].active_donors.iloc[-1]) for mo in monthly.month]
monthly["kg_per_active_donor"] = monthly.kg / days.assign(mo=days.date.dt.to_period("M").astype(str)).groupby("mo").active_donors.mean().reindex(monthly.month).values
monthly["collection_rate_%"] = monthly.collected_kg / monthly.kg * 100
monthly["redistribution_yield_%"] = monthly.delivered_kg / monthly.kg * 100
monthly.to_csv(TAB / "monthly_series.csv", index=False)
weekly = m.groupby("week_start").agg(reports=("surplus_id", "size"), kg=("quantity_kg", "sum"), delivered_kg=("delivered_kg", "sum")).reset_index()
weekly.to_csv(TAB / "weekly_series.csv", index=False)

fig, ax = plt.subplots(3, 1, figsize=(12, 10))
ax[0].plot(daily.date, daily.kg, color=SAGE, alpha=.45, lw=1, label="Daily kg")
ax[0].plot(daily.date, daily.kg_ma7, color=NAVY, lw=2, label="7-day average")
for n, g in daily[daily.festival_name != "No Festival"].groupby("festival_name"):
    ax[0].axvspan(g.date.min(), g.date.max() + pd.Timedelta(days=1), color=MUSTARD, alpha=.25)
ax[0].set_title("Daily reported surplus (kg); shaded = approximate festival windows"); ax[0].legend(loc="upper left")
ax[1].bar(weekly.week_start, weekly.kg, width=6, color=NAVY, label="Reported")
ax[1].bar(weekly.week_start, weekly.delivered_kg, width=6, color=TEAL, label="Delivered")
ax[1].set_title("Weekly reported vs delivered (kg)"); ax[1].legend()
x = np.arange(len(monthly)); ax[2].bar(x - .2, monthly.kg / 1000, .4, color=NAVY, label="Total tonnes")
ax[2].set_xticks(x); ax[2].set_xticklabels(monthly.month, rotation=0); ax[2].set_ylabel("Tonnes")
a2 = ax[2].twinx(); a2.plot(x, monthly.kg_per_active_donor, color=TERRA, marker="o", label="kg per active donor"); a2.grid(False)
ax[2].set_title("Monthly total vs kg per active donor (controls for donor onboarding)")
h1, l1 = ax[2].get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels(); ax[2].legend(h1 + h2, l1 + l2, loc="upper left")
fig.tight_layout(); save_fig(fig, "04_time_trends.png")

# weekday x hour heat map and weekday by donor category ----------------------------------------
hm = m.pivot_table(index="day_name", columns="report_hour", values="quantity_kg", aggfunc="sum", fill_value=0).reindex(
    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
fig, ax = plt.subplots(1, 2, figsize=(14, 4.2), gridspec_kw={"width_ratios": [1.5, 1]})
sns.heatmap(hm / 1000, cmap=sns.light_palette(TERRA, as_cmap=True), ax=ax[0], cbar_kws={"label": "tonnes"})
ax[0].set_title("When surplus appears: weekday x hour of report (tonnes)"); ax[0].set_xlabel("Hour of day"); ax[0].set_ylabel("")
wk = m.pivot_table(index="day_name", columns="donor_category", values="quantity_kg", aggfunc="sum").reindex(hm.index)
(wk.div(wk.sum(axis=1), axis=0) * 100).plot(kind="bar", stacked=True, ax=ax[1], color=PALETTE, width=.8)
ax[1].set_title("Donor-category mix by weekday (%)"); ax[1].set_xlabel(""); ax[1].legend(fontsize=7, bbox_to_anchor=(1, 1))
fig.tight_layout(); save_fig(fig, "05_weekday_hour_heatmap.png")
monthly.round(1)

# %% [markdown]
# ## 5. Collection efficiency
# Outcome of every collection attempt by donor category, time slot and rain level; response-time distribution.

# %%
order = ["Collected - Full", "Collected - Partial", "Missed - No Volunteer Available", "Missed - Arrived Beyond Safe Window",
         "Rejected - Failed Volunteer Safety Check", "Cancelled by Donor"]
colr = {order[0]: SAGE, order[1]: "#A9C4AB", order[2]: TERRA, order[3]: MUSTARD, order[4]: ROSE, order[5]: GREY}
fig, ax = plt.subplots(1, 3, figsize=(16, 4.6), sharey=False)
for a, (key, ordr, ttl) in zip(ax, (("donor_category", DONOR_CATEGORIES, "by donor category"), ("time_slot", SLOTS, "by time slot of report"),
                                    ("rain_level", ["No Rain", "Light/Moderate", "Heavy"], "by (synthetic) rain level"))):
    t = pd.crosstab(m[key], m.collection_status, normalize="index").reindex(ordr)[order] * 100
    t.plot(kind="barh", stacked=True, ax=a, color=[colr[c] for c in order], width=.75, legend=False)
    a.set_title(f"Collection outcome {ttl} (%)"); a.set_ylabel("")
ax[2].legend(order, fontsize=7, bbox_to_anchor=(1.02, 1), loc="upper left")
fig.tight_layout(); save_fig(fig, "06_collection_outcomes.png")
eff = m.groupby("donor_category").agg(reports=("surplus_id", "size"), collected_pct=("is_collected", lambda x: x.mean() * 100),
                                      kg=("quantity_kg", "sum"), collected_kg=("qty_collected_kg", "sum"), delivered_kg=("delivered_kg", "sum"))
eff["kg_collection_rate_%"] = eff.collected_kg / eff.kg * 100; eff["kg_yield_%"] = eff.delivered_kg / eff.kg * 100
eff.to_csv(TAB / "efficiency_by_donor_category.csv")
slot_eff = m.groupby("time_slot").agg(reports=("surplus_id", "size"), collected_pct=("is_collected", lambda x: x.mean() * 100), kg=("quantity_kg", "sum"),
                                      delivered_kg=("delivered_kg", "sum"), median_response_min=("response_min", "median")).reindex(SLOTS)
slot_eff["kg_yield_%"] = slot_eff.delivered_kg / slot_eff.kg * 100
slot_eff.to_csv(TAB / "efficiency_by_time_slot.csv")

fig, ax = plt.subplots(1, 3, figsize=(15, 4))
cm = m[m.is_collected == 1]
sns.histplot(cm.response_min.clip(upper=240), bins=40, color=SAGE, ax=ax[0]); ax[0].axvline(cm.response_min.median(), color=NAVY, ls="--")
ax[0].set_title(f"Report -> pickup minutes (median {cm.response_min.median():.0f}; clipped at 240)"); ax[0].set_xlabel("minutes")
sns.boxplot(data=cm, x="time_slot", y="response_min", order=SLOTS, color=SAGE, ax=ax[1], showfliers=False)
ax[1].set_title("Response time by time slot (min)"); ax[1].set_xlabel(""); plt.setp(ax[1].get_xticklabels(), rotation=15)
sns.boxplot(data=cm, x="rain_level", y="response_min", order=["No Rain", "Light/Moderate", "Heavy"], color="#A9C4AB", ax=ax[2], showfliers=False)
ax[2].set_title("Response time by rain level (min)"); ax[2].set_xlabel("")
fig.tight_layout(); save_fig(fig, "07_response_times.png")
slot_eff.round(1)

# %% [markdown]
# ## 6. Distribution efficiency and recipient utilisation

# %%
dd = md[md.distribution_status == "Delivered"]
days_n = ctx.shape[0]
ru = dd.groupby(["recipient_id", "recipient_name", "recipient_type", "recipient_zone"]).agg(
    deliveries=("distribution_id", "size"), kg=("qty_distributed_kg", "sum"), portions=("beneficiaries_served", "sum")).reset_index()
ru = ru.merge(rec[["recipient_id", "daily_capacity_portions"]], on="recipient_id")
ru["avg_daily_portions"] = ru.portions / days_n
ru["utilisation_%"] = ru.avg_daily_portions / ru.daily_capacity_portions * 100
ru.to_csv(TAB / "recipient_utilisation.csv", index=False)
fig, ax = plt.subplots(1, 3, figsize=(16, 4.8))
r_ = ru.sort_values("utilisation_%")
ax[0].barh(r_.recipient_id, r_["utilisation_%"], color=TEAL); ax[0].set_title("Recipient utilisation: avg daily portions / capacity (%)")
t = dd.groupby("delivery_hour").beneficiaries_served.sum()
ax[1].bar(t.index, t.values, color=NAVY); ax[1].set_title("Portions delivered by hour of day"); ax[1].set_xlabel("Hour")
w = md[md.wastage_reason.notna()].groupby("wastage_reason").wastage_kg.sum().sort_values()
ax[2].barh(w.index, w.values / 1000, color=TERRA); ax[2].set_title("Post-collection wastage by reason (tonnes)")
fig.tight_layout(); save_fig(fig, "08_distribution_efficiency.png")
pd.concat([ru.groupby("recipient_type")[["deliveries", "kg", "portions"]].sum(), ru.groupby("recipient_type")["utilisation_%"].mean()], axis=1).round(1)

# %% [markdown]
# ## 7. Hypothesis tests and a logistic model
# Non-parametric tests are used because quantities are strongly right-skewed. Effect sizes are reported
# alongside p-values - with ~10,000 records almost any difference is "significant", so **effect size matters more**.

# %%
def magnitude(name, v):
    """Verbal effect-size label (conventional rule-of-thumb thresholds: Cohen / Tomczak & Tomczak)."""
    v = abs(v)
    th = {"epsilon-squared": (.01, .08, .26), "rank-biserial r": (.1, .3, .5), "Cramer's V": (.1, .3, .5), "rho": (.1, .3, .5)}[name]
    return "negligible" if v < th[0] else "small" if v < th[1] else "moderate" if v < th[2] else "large"


res = []
# T1 Kruskal-Wallis: quantity differs by donor category
groups = [g.quantity_kg.values for _, g in m.groupby("donor_category")]
H, p = stats.kruskal(*groups); k, n = len(groups), len(m)
res.append(dict(test="Kruskal-Wallis: quantity_kg across donor categories", statistic=H, p_value=p, effect_size=(H - k + 1) / (n - k), effect_name="epsilon-squared",
                reading=f"{magnitude('epsilon-squared', (H - k + 1) / (n - k))} effect"))
# T2 weekend vs weekday kg per active donor (daily)
a, b = daily[daily.is_weekend == 1].kg_per_active_donor, daily[daily.is_weekend == 0].kg_per_active_donor
U, p = stats.mannwhitneyu(a, b); rbc = 2 * U / (len(a) * len(b)) - 1
res.append(dict(test="Mann-Whitney: daily kg per active donor, weekend vs weekday", statistic=U, p_value=p, effect_size=rbc, effect_name="rank-biserial r",
                reading=f"{magnitude('rank-biserial r', rbc)} effect; median weekend {a.median():.1f} vs weekday {b.median():.1f} kg/donor/day"))


def chi(label, x, y):
    t = pd.crosstab(x, y); c2, p, dof, _ = stats.chi2_contingency(t)
    v = np.sqrt(c2 / (t.values.sum() * (min(t.shape) - 1)))
    size = magnitude("Cramer's V", v)
    res.append(dict(test=label, statistic=c2, p_value=p, effect_size=v, effect_name="Cramer's V", reading=f"{size} association (dof={dof})"))


chi("Chi-square: collected (Y/N) vs time slot", m.time_slot, m.is_collected)
chi("Chi-square: collected (Y/N) vs rain level", m.rain_level, m.is_collected)
chi("Chi-square: collected (Y/N) vs donor category", m.donor_category, m.is_collected)
chi("Chi-square: collected (Y/N) vs donor zone", m.sub_area, m.is_collected)
rho, p = stats.spearmanr(cm.collection_distance_km, cm.response_min)
res.append(dict(test="Spearman: volunteer distance vs response minutes (collected only)", statistic=rho, p_value=p, effect_size=rho, effect_name="rho", reading=f"{magnitude('rho', rho)} association"))
rho, p = stats.spearmanr(np.log(cm.quantity_kg), cm.response_min)
res.append(dict(test="Spearman: log quantity vs response minutes (collected only)", statistic=rho, p_value=p, effect_size=rho, effect_name="rho", reading=f"{magnitude('rho', rho)} association"))
tests = pd.DataFrame(res); tests.to_csv(TAB / "statistical_tests.csv", index=False); tests

# %%
# Logistic regression: what drives a report being collected?  (statsmodels Logit; odds ratios with 95% CI)
X = pd.DataFrame({
    "late_night_report (21-24h)": (m.time_slot == "Late Night (21-24)").astype(int),
    "evening_report (17-21h)": (m.time_slot == "Evening (17-21)").astype(int),
    "rain_light_moderate": (m.rain_level == "Light/Moderate").astype(int), "rain_heavy": (m.rain_level == "Heavy").astype(int),
    "weekend": m.is_weekend, "festival_day": (m.festival_name != "No Festival").astype(int),
    "log_quantity_kg": np.log(m.quantity_kg), "high_perishability": (m.perishability_class == "High").astype(int)})
X = pd.concat([X, pd.get_dummies(m.donor_category, drop_first=True, dtype=int)], axis=1)
X = sm.add_constant(X.astype(float), has_constant="add")
logit = sm.Logit(m.is_collected.astype(float), X).fit(disp=0)
ci = logit.conf_int()
orr = pd.DataFrame({"odds_ratio": np.exp(logit.params), "ci_low": np.exp(ci[0]), "ci_high": np.exp(ci[1]), "p_value": logit.pvalues}).drop(index="const")
orr.to_csv(TAB / "logit_collection_odds_ratios.csv")
pd.Series({"pseudo_R2_McFadden": logit.prsquared, "n": int(logit.nobs)}).to_csv(TAB / "logit_fit.csv")
fig, ax = plt.subplots(figsize=(8, 5))
o = orr.sort_values("odds_ratio")
ax.errorbar(o.odds_ratio, range(len(o)), xerr=[o.odds_ratio - o.ci_low, o.ci_high - o.odds_ratio], fmt="o", color=NAVY, ecolor=GREY, capsize=3)
ax.axvline(1, color=TERRA, ls="--"); ax.set_yticks(range(len(o))); ax.set_yticklabels(o.index); ax.set_xscale("log")
ax.set_title(f"Odds of a report being collected (McFadden R2 = {logit.prsquared:.2f})"); ax.set_xlabel("Odds ratio (log scale); reference donor category = Bakery")
fig.tight_layout(); save_fig(fig, "09_collection_odds_ratios.png")
orr.round(3)
