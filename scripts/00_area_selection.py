"""00 - Multi-criteria area selection (desk-based, analyst-judgement scores) + weight-sensitivity analysis.

IMPORTANT: scores are provisional 1-5 desk judgements, NOT measured data. They must be validated by
a field walk-through and by BMC/FSSAI registries before any real decision. Run: python scripts/00_area_selection.py
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import TAB, set_style, save_fig, NAVY, SAGE, TERRA, GREY, SEED, ensure_dirs

ensure_dirs(); set_style()
CRIT = {"Accessibility (rail/road, walkability)": .20, "Donor density & diversity": .25, "Proximity to underserved communities": .25,
        "Recipient/NGO accessibility": .15, "Compactness / field feasibility": .15}
S = {  # analyst scores 1-5
    "Dadar-Matunga-Mahim (G North/F North)": [5, 5, 4, 4, 4], "Andheri West (Lokhandwala-Versova)": [4, 5, 3, 3, 2],
    "Bandra West-Khar": [4, 4, 3, 3, 3], "Ghatkopar-Vidyavihar": [4, 3, 4, 3, 3], "Kurla-Chunabhatti": [4, 3, 5, 3, 2],
    "Borivali West": [4, 3, 2, 3, 2], "Colaba-Fort": [4, 4, 2, 3, 4]}
df = pd.DataFrame(S, index=list(CRIT)).T
w = np.array(list(CRIT.values()))
df["weighted_score"] = df.iloc[:, :5].values @ w
df = df.sort_values("weighted_score", ascending=False)
rng = np.random.default_rng(SEED)
W = rng.dirichlet(np.ones(5), 10000)
winners = pd.Series((df.iloc[:, :5].values @ W.T).argmax(axis=0)).map(dict(enumerate(df.index))).value_counts(normalize=True) * 100
df["win_share_under_random_weights_%"] = winners.reindex(df.index).fillna(0)
df.to_csv(TAB / "area_selection_matrix.csv"); print(df.round(2).to_string())
fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
ax[0].barh(df.index[::-1], df.weighted_score[::-1], color=[GREY] * (len(df) - 1) + [NAVY]); ax[0].set_title("Weighted suitability score (1-5), provisional desk assessment")
ax[1].barh(df.index[::-1], df["win_share_under_random_weights_%"][::-1], color=[GREY] * (len(df) - 1) + [SAGE]); ax[1].set_title("% of 10,000 random weightings in which the area ranks first")
fig.tight_layout(); save_fig(fig, "00_area_selection.png", watermark=False)
