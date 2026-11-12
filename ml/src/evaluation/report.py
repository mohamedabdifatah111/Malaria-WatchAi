"""Chart-ready validation summary for the dashboard + static figures for the pitch.

Outputs
  data/processed/validation_summary.json   frontend renders its own charts from this
  ml/outputs/figures/*.png                 slides / README (static, light theme)

Run:  python -m ml.src.evaluation.report   (after predict, efficacy, survey_priority)
"""
from __future__ import annotations

import json
import logging

import matplotlib

matplotlib.use("Agg")
import geopandas as gpd  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap, ListedColormap  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from ml.src import config, io  # noqa: E402
from ml.src.data import boundaries  # noqa: E402

log = logging.getLogger("ml.report")

# Reference palette (dataviz skill): categorical slots 1-3 validate all-pairs.
MODEL_COLOR = {"idw": "#2a78d6", "adm1_mean": "#eb6834", "lightgbm": "#1baf7a"}
MODEL_LABEL = {"idw": "IDW baseline", "adm1_mean": "ADM1-mean baseline", "lightgbm": "LightGBM"}
SCHEME_LABEL = {"random_5fold": "Random 5-fold\n(optimistic)", "spatial_block_5fold": "Spatial block 5-fold\n(primary)",
                "leave_one_adm1_out": "Leave-one-ADM1-out"}
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE_SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
ORANGE_SEQ = LinearSegmentedColormap.from_list("orange", ["#fde9df", "#f4a27f", "#eb6834", "#a8431a"])


def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.yaxis.label.set_color(INK2)
    ax.xaxis.label.set_color(INK2)


def summary(metrics: dict) -> dict:
    rows = []
    for s, v in metrics["schemes"].items():
        for m, r in v["models"].items():
            o = r["overall"]
            rows.append({"scheme": s, "model": m, "mae": o["mae"], "rmse": o["rmse"], "spearman": o["spearman"],
                         "bias": o["bias"], "n": o["n"]})
    by_country = []
    for m, r in metrics["schemes"]["spatial_block_5fold"]["models"].items():
        for c, o in r["by_country"].items():
            by_country.append({"model": m, "country": c, "mae": o["mae"], "rmse": o["rmse"], "n": o["n"]})
    u = metrics["uncertainty"]["prevalence_interval"]["coverage"]
    return {
        "units": "PfPR proportion 0-1, out-of-fold per survey",
        "primary_scheme": "spatial_block_5fold",
        "overall": rows,
        "spatial_by_country": by_country,
        "comparison": {s: v["comparison"] for s, v in metrics["schemes"].items()},
        "interval_coverage": {"nominal": u["nominal"], "survey_level": u["survey_level_coverage"],
                              "prevalence_interval_large_surveys": u["prevalence_interval_coverage_large_surveys"],
                              "n_large_surveys": u["n_large_surveys"]},
        "headline": ("LightGBM beats both baselines under spatial validation, but error rises from random to "
                     "spatial CV - accuracy drops away from surveyed areas, which is why every estimate "
                     "carries a reliability flag."),
        "evidence_ids": [f"MODEL-PFPR-{config.ml()['model_version']}", "MAP-PR-SURVEYS"],
    }


def fig_cv(s: dict, out):
    d = pd.DataFrame(s["overall"])
    schemes = ["random_5fold", "spatial_block_5fold", "leave_one_adm1_out"]
    models = ["idw", "adm1_mean", "lightgbm"]
    fig, ax = plt.subplots(figsize=(8, 4.2), facecolor=SURFACE)
    _style(ax)
    w = 0.26
    for i, m in enumerate(models):
        vals = [d[(d.scheme == sc) & (d.model == m)]["mae"].iloc[0] for sc in schemes]
        x = np.arange(len(schemes)) + (i - 1) * (w + 0.02)
        ax.bar(x, vals, width=w, color=MODEL_COLOR[m], label=MODEL_LABEL[m], edgecolor=SURFACE, linewidth=2)
        if m == "lightgbm":
            for xi, v in zip(x, vals):
                ax.text(xi, v + 0.003, f"{v:.3f}", ha="center", va="bottom", fontsize=8.5, color=INK)
    ax.set_xticks(np.arange(len(schemes)), [SCHEME_LABEL[sc] for sc in schemes], fontsize=9, color=INK2)
    ax.set_ylabel("Mean absolute error (PfPR, 0-1)")
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("Model error by validation design - lower is better", loc="left", fontsize=11, color=INK)
    fig.text(0.01, 0.01, "Out-of-fold error on 2,555 MAP surveys. Random CV is optimistic because nearby surveys "
             "share train and test.", fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(out / "cv_comparison.png", dpi=180, facecolor=SURFACE)
    plt.close(fig)


def fig_obs_pred(out):
    o = pd.read_parquet(config.outputs_dir() / "oof_predictions.parquet")
    o = o[o["scheme"] == "spatial_block_5fold"]
    fig, ax = plt.subplots(figsize=(4.8, 4.6), facecolor=SURFACE)
    _style(ax)
    ax.plot([0, 1], [0, 1], color=INK2, linewidth=1, linestyle="--")
    ax.scatter(o["pred_lightgbm"], o["prevalence"], s=10, color=MODEL_COLOR["lightgbm"], alpha=0.35,
               edgecolors="none")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Predicted PfPR (spatial out-of-fold)")
    ax.set_ylabel("Observed survey PfPR")
    ax.set_title("LightGBM, spatial block CV", loc="left", fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(out / "observed_vs_predicted.png", dpi=180, facecolor=SURFACE)
    plt.close(fig)


def _map(ax, geo, column, cmap, norm, title, hatch_mask=None):
    geo.plot(column=column, cmap=cmap, norm=norm, ax=ax, edgecolor=SURFACE, linewidth=0.2)
    if hatch_mask is not None and hatch_mask.any():
        geo[hatch_mask].plot(ax=ax, facecolor="none", edgecolor=INK2, hatch="////", linewidth=0)
    boundaries.level("ADM0").boundary.plot(ax=ax, color=INK, linewidth=0.6)
    ax.set_axis_off()
    ax.set_title(title, loc="left", fontsize=11, color=INK)


def fig_maps(out):
    P = config.processed_dir()
    geo = gpd.read_file(P / "prevalence_adm2.geojson")
    edges = [0, 0.01, 0.05, 0.10, 0.20, 0.35, 0.50, 1.0]
    norm = BoundaryNorm(edges, len(BLUE_SEQ))
    fig, axs = plt.subplots(1, 2, figsize=(11, 6.2), facecolor=SURFACE)
    _map(axs[0], geo, "estimate", ListedColormap(BLUE_SEQ), norm,
         "Modelled PfPR (2-10), 2020 - by district", geo["extrapolation_flag"].astype(bool))
    sm = plt.cm.ScalarMappable(norm=norm, cmap=ListedColormap(BLUE_SEQ))
    cb = fig.colorbar(sm, ax=axs[0], shrink=0.6, ticks=edges)
    cb.ax.set_yticklabels([f"{int(e * 100)}%" for e in edges], fontsize=8, color=INK2)
    _map(axs[1], geo, "interval_width", ORANGE_SEQ, plt.Normalize(0, geo["interval_width"].max()),
         "Uncertainty: 90% interval width", geo["extrapolation_flag"].astype(bool))
    sm2 = plt.cm.ScalarMappable(norm=plt.Normalize(0, geo["interval_width"].max()), cmap=ORANGE_SEQ)
    cb2 = fig.colorbar(sm2, ax=axs[1], shrink=0.6)
    cb2.ax.tick_params(labelsize=8, colors=INK2)
    axs[1].legend(handles=[Patch(facecolor="none", edgecolor=INK2, hatch="////",
                                 label="Extrapolated (>50% of people far from surveys)")],
                  frameon=False, fontsize=8, loc="lower left")
    fig.text(0.01, 0.01, "Model-based estimates, not observations. Population-weighted mean of 5 km cells. "
             "Sources: MAP surveys, WorldClim, MODIS, WorldPop, GHSL, HydroRIVERS, geoBoundaries.",
             fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out / "map_prevalence_uncertainty.png", dpi=180, facecolor=SURFACE)
    plt.close(fig)


def fig_priority(out):
    P = config.processed_dir()
    geo = gpd.read_file(P / "survey_priority_adm2.geojson")
    s = gpd.read_parquet(P / "surveys.parquet")
    fig, ax = plt.subplots(figsize=(6.5, 6.5), facecolor=SURFACE)
    geo.plot(ax=ax, color="#f0efec", edgecolor=SURFACE, linewidth=0.2)
    top = geo.sort_values("rank_overall").groupby("country").head(10)
    top.plot(ax=ax, color="#eb6834", edgecolor=SURFACE, linewidth=0.3)
    s.plot(ax=ax, color=INK, markersize=1.5, alpha=0.5)
    boundaries.level("ADM0").boundary.plot(ax=ax, color=INK, linewidth=0.6)
    ax.set_axis_off()
    ax.legend(handles=[Patch(color="#eb6834", label="Top 10 districts per country for a new survey"),
                       plt.Line2D([], [], marker="o", linestyle="", color=INK, markersize=3,
                                  label="Existing open survey")], frameon=False, fontsize=8,
              loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=2)
    ax.set_title("Where one new survey would reduce the most uncertainty", loc="left", fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(out / "map_survey_priority.png", dpi=180, facecolor=SURFACE)
    plt.close(fig)


def fig_efficacy(out):
    P = config.processed_dir()
    st = pd.read_parquet(P / "efficacy_studies.parquet")
    po = pd.read_parquet(P / "efficacy_pooled.parquet")
    st = st[(st["drug"] == "AL") & (st["followup_days"] == 28) & (st["status"] == "ok")]
    po = po[(po["drug"] == "AL") & (po["followup_days"] == 28) & (po["status"] == "ok")]
    fig, ax = plt.subplots(figsize=(7, 3.6), facecolor=SURFACE)
    _style(ax)
    names = {"KEN": "Kenya", "TZA": "Tanzania", "ETH": "Ethiopia"}
    for i, c in enumerate(["KEN", "TZA", "ETH"]):
        s = st[st["country"] == c]
        ax.scatter(s["acpr_percent"], np.full(len(s), i) + np.linspace(-0.18, 0.18, len(s)), s=14,
                   color="#9ec5f4", edgecolors="none", zorder=2)
        p = po[po["country"] == c]
        if len(p):
            p = p.iloc[0]
            ax.plot([p["confidence_interval_lower"], p["confidence_interval_upper"]], [i, i], color="#184f95",
                    linewidth=2, zorder=3)
            ax.scatter([p["acpr_percent"]], [i], s=60, marker="D", color="#184f95", zorder=4)
            ax.text(101.0, i, f"{p['acpr_percent']:.1f}%\n{int(p['study_count'])} studies",
                    va="center", fontsize=8.5, color=INK)
    ax.axvline(90, color="#d03b3b", linewidth=1.2, linestyle="--")
    ax.text(90.2, 2.45, "WHO 10% failure signal (policy review)", fontsize=8, color="#d03b3b", va="bottom")
    ax.set_yticks([0, 1, 2], [names[c] for c in ["KEN", "TZA", "ETH"]], fontsize=9, color=INK2)
    ax.set_xlim(80, 105)
    ax.set_xticks([80, 85, 90, 95, 100])
    ax.text(101.0, 2.45, "Pooled", fontsize=8, color=INK2, va="bottom")
    ax.set_ylim(-0.6, 2.8)
    ax.set_xlabel("PCR-corrected ACPR, day 28 (%)")
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title("Artemether-lumefantrine efficacy: studies (dots) and pooled estimate (95% CI)", loc="left",
                 fontsize=10.5, color=INK)
    fig.text(0.01, 0.01, "Source: WHO Malaria Threats Map therapeutic efficacy studies. Random-effects pooling.",
             fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(out / "efficacy_al_day28.png", dpi=180, facecolor=SURFACE)
    plt.close(fig)


def run() -> dict:
    metrics = json.loads((config.processed_dir() / "metrics.json").read_text(encoding="utf-8"))
    s = summary(metrics)
    io.write_json(s, "validation_summary.json")
    out = config.outputs_dir() / "figures"
    out.mkdir(exist_ok=True)
    for f in (lambda: fig_cv(s, out), lambda: fig_obs_pred(out), lambda: fig_maps(out),
              lambda: fig_priority(out), lambda: fig_efficacy(out)):
        f()
    figs = sorted(p.name for p in out.glob("*.png"))
    log.info("figures: %s", figs)
    return {"figures": figs}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    print(run())
