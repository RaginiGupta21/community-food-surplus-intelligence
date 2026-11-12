"""Shared paths, constants and plotting helpers for the Food Surplus project.

Every dataset in this repository is SYNTHETIC DEMO DATA unless it was collected
in the field with the templates in data/templates/.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
CLEAN = DATA / "clean"
TEMPLATES = DATA / "templates"
OUT = ROOT / "outputs"
FIG = OUT / "figures"
TAB = OUT / "tables"
PBI = ROOT / "powerbi" / "data"

DATA_LABEL = "SYNTHETIC DEMO DATA"
SEED = 2026

# Soft, muted palette (no neon, no black backgrounds) - also used in the Power BI theme
BG = "#F7F5F0"
NAVY, SAGE, TERRA, MUSTARD, ROSE, TEAL, GREY = (
    "#3B5B7A", "#7A9E7E", "#C97B63", "#D4A84B", "#B07C9E", "#5E9EA0", "#9A9488")
PALETTE = [NAVY, SAGE, TERRA, MUSTARD, ROSE, TEAL, GREY]


def ensure_dirs():
    for p in (RAW, CLEAN, TEMPLATES, FIG, TAB, PBI):
        p.mkdir(parents=True, exist_ok=True)


def set_style():
    sns.set_theme(style="whitegrid", palette=PALETTE)
    plt.rcParams.update({
        "figure.facecolor": BG, "axes.facecolor": "#FFFFFF", "savefig.facecolor": BG,
        "axes.edgecolor": "#CFCABF", "grid.color": "#E7E3D9", "axes.titleweight": "bold",
        "axes.titlesize": 12, "axes.labelsize": 10, "font.size": 9,
        "axes.prop_cycle": matplotlib.cycler(color=PALETTE),
    })


def save_fig(fig, name, watermark=True):
    ensure_dirs()
    if watermark:
        fig.text(0.995, 0.005, DATA_LABEL, ha="right", va="bottom", fontsize=7,
                 color=GREY, style="italic")
    fig.savefig(FIG / name, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return FIG / name
