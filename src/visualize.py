"""Publication-ready figures (colour-blind safe, CI bands, PDF + 300 dpi PNG)."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.ticker import FuncFormatter, NullFormatter

from process_data import BASELINE, PROPOSED

CUES = ["urgency", "authority", "familiarity"]
CUE_LABEL = {"urgency": "Urgency", "authority": "Authority", "familiarity": "Familiarity"}

PAL = sns.color_palette("colorblind")
STYLE = {  # colour + marker + line style, so the plot also reads in black and white
    BASELINE: dict(color=PAL[0], marker="o", linestyle="-"),
    PROPOSED: dict(color=PAL[1], marker="s", linestyle="--"),
}
HATCH = {BASELINE: "", PROPOSED: "//"}


def _plain_log_axis(ax):
    """Show plain numbers (2, 5, 10, 20) instead of 10^x on a log axis."""
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.yaxis.set_minor_formatter(FuncFormatter(lambda v, _: f"{v:g}" if v in (2, 3, 4, 5, 6, 7, 8, 20, 30) else ""))


def _save(fig, outdir, name):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    fig.savefig(outdir / f"{name}.pdf", bbox_inches="tight")             # vector
    fig.savefig(outdir / f"{name}.png", dpi=300, bbox_inches="tight")    # raster
    return [outdir / f"{name}.pdf", outdir / f"{name}.png"]


def fig_latency_vs_load(summary, outdir="reports/figures", name="fig1_latency_vs_load"):
    """(a) median response time and (b) error rate per cue type, with 95% CI bands."""
    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    summ = summary[summary["channel"] == "all"]
    x = np.arange(len(CUES))
    for grp, st in STYLE.items():
        d = summ[summ["group"] == grp].set_index("cue_type").reindex(CUES)
        if d["median_s"].isna().all():
            continue
        ax = axes[0]
        ax.plot(x, d["median_s"], label=grp, linewidth=2, markersize=7, **st)
        ax.fill_between(x, d["median_ci_lo"], d["median_ci_hi"], color=st["color"], alpha=0.2)
        ax = axes[1]
        ax.plot(x, 100 * d["error_rate"], label=grp, linewidth=2, markersize=7, **st)
        ax.fill_between(x, 100 * d["error_ci_lo"], 100 * d["error_ci_hi"], color=st["color"], alpha=0.2)
    axes[0].set_ylabel("Median response time (s)")
    axes[0].set_yscale("log")
    _plain_log_axis(axes[0])
    axes[0].set_title("(a) Response time vs. cue type")
    axes[1].set_ylabel("Error rate (%)")
    axes[1].set_title("(b) Error rate (guardrail) vs. cue type")
    for ax in axes:
        ax.set_xlabel("Social-engineering cue type (load)")
        ax.set_xticks(x)
        ax.set_xticklabels([CUE_LABEL[c] for c in CUES])
    axes[1].set_ylim(bottom=0)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, title="Shaded band: 95% bootstrap CI", loc="lower center", ncol=2, frameon=True)
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    paths = _save(fig, outdir, name)
    return fig, paths


def fig_distribution_boxplot(df_eval, summary, outdir="reports/figures",
                             name="fig2_distribution_boxplot"):
    """Response-time distribution per load level and group; bars = 95% CI of the median."""
    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    levels = [c for c in CUES if c in set(df_eval["cue_type"])]
    width = 0.34
    for j, grp in enumerate((BASELINE, PROPOSED)):
        pos, data = [], []
        for i, lv in enumerate(levels):
            v = df_eval[(df_eval["group"] == grp) & (df_eval["cue_type"] == lv)]["response_time_s"]
            if len(v):
                pos.append(i + (j - 0.5) * width * 1.1)
                data.append(v.to_numpy())
        if not data:
            continue
        bp = ax.boxplot(data, positions=pos, widths=width, patch_artist=True, showfliers=True,
                        medianprops=dict(color="black", linewidth=1.6),
                        flierprops=dict(marker=STYLE[grp]["marker"], markersize=3, alpha=0.5))
        for box in bp["boxes"]:
            box.set(facecolor=STYLE[grp]["color"], alpha=0.65, hatch=HATCH[grp])
        # 95% bootstrap CI of the median as black error bars
        s = summary[(summary["group"] == grp) & (summary["channel"] == "all")].set_index("cue_type")
        for p, lv in zip(pos, [lv for lv in levels
                               if len(df_eval[(df_eval["group"] == grp) & (df_eval["cue_type"] == lv)])]):
            if lv in s.index and not np.isnan(s.loc[lv, "median_ci_lo"]):
                m = s.loc[lv, "median_s"]
                ax.errorbar(p, m, yerr=[[m - s.loc[lv, "median_ci_lo"]], [s.loc[lv, "median_ci_hi"] - m]],
                            fmt="none", ecolor="black", capsize=4, elinewidth=1.2)
    ax.set_yscale("log")
    _plain_log_axis(ax)
    ax.set_xticks(range(len(levels)))
    ax.set_xticklabels([CUE_LABEL[c] for c in levels])
    ax.set_xlabel("Social-engineering cue type (load)")
    ax.set_ylabel("Response time (s)")
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=STYLE[g]["color"], alpha=0.65, hatch=HATCH[g], label=g)
               for g in (BASELINE, PROPOSED)]
    ax.legend(handles=handles, title="Black bars: 95% CI of median", frameon=True)
    fig.tight_layout()
    paths = _save(fig, outdir, name)
    return fig, paths
