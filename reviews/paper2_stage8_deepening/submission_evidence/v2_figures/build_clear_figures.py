"""Build article figures with labels that remain readable at journal width."""
from pathlib import Path
import csv
import json

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, Rectangle
import numpy as np

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]
ROBUST = STAGE / "robustness_exploration"
ETA = 1 / 1600
BLUE, RED, DARK, GREY = "#124c70", "#923d30", "#222222", "#666666"

ZH_FONT = "Microsoft YaHei UI"
plt.rcParams.update({
    "font.family": ZH_FONT,
    "font.size": 8.4,
    "axes.titlesize": 9.2,
    "axes.labelsize": 8.3,
    "axes.linewidth": 0.8,
    "legend.fontsize": 8.0,
    "pdf.fonttype": 42,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.unicode_minus": False,
})


def load(path):
    return json.loads(path.read_text(encoding="utf8"))


def save(fig, name):
    for fmt in ("pdf", "png"):
        fig.savefig(HERE / f"{name}.{fmt}", dpi=410, facecolor="white",
                    bbox_inches="tight", pad_inches=.035,
                    metadata={"Creator": "Stage 8 clear-label figure reconstruction"})
    plt.close(fig)


def write_csv(name, rows):
    if not rows:
        return
    with (HERE / name).open("w", newline="", encoding="utf8") as f:
        writer = csv.DictWriter(f, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def architecture():
    fig, ax = plt.subplots(figsize=(7.25, 2.72))
    ax.set(xlim=(0, 12), ylim=(0, 4.05))
    ax.axis("off")
    width, height, y = 2.72, 1.02, 1.62
    boxes = [
        (0.20, "传感与随机触发", r"读取量测 $y_t$"),
        (4.64, "名义状态估计", r"更新估计 $m_t^M$"),
        (9.08, "校正后输出", r"发布 $m_t^R=m_t^M-a_t$"),
    ]
    for x, title, detail in boxes:
        ax.add_patch(Rectangle((x, y), width, height, facecolor="#f1f4f5",
                               edgecolor=DARK, lw=1))
        ax.text(x + width / 2, y + .71, title, ha="center", va="center",
                fontsize=8.6, fontweight="bold")
        ax.text(x + width / 2, y + .28, detail, ha="center", va="center",
                fontsize=8.2)

    def arrow(a, b):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=10.2,
                                     color=DARK, lw=1.0, shrinkA=0, shrinkB=0))

    upper, lower, middle = 3.47, .63, y + height / 2
    xs = [x + width / 2 for x, *_ in boxes]
    ax.plot([xs[1], xs[1], xs[0]], [y + height, upper, upper], color=DARK, lw=1)
    arrow((xs[0], upper), (xs[0], y + height))
    ax.text((xs[0] + xs[1]) / 2, upper + .16, r"下行反馈：共享预测中心 $c_t$",
            ha="center", fontsize=8.0,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.2))
    arrow((boxes[0][0] + width, middle), (boxes[1][0], middle))
    ax.text(3.78, y + height + .12, "事件位 $\\gamma_t$\n发送载荷 $z_t^*$",
            ha="center", va="bottom", fontsize=7.8,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.0))
    arrow((boxes[1][0] + width, middle), (boxes[2][0], middle))
    ax.text(8.20, y + height + .12, "名义估计\n$m_t^M$",
            ha="center", va="bottom", fontsize=7.8,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.0))
    ax.plot([xs[1], xs[1], xs[2]], [y, lower, lower], color=DARK, lw=1)
    arrow((xs[2], lower), (xs[2], y))
    ax.text((xs[1] + xs[2]) / 2, lower - .11,
            "可信记录交给校正器：预测中心、事件位和发送载荷",
            ha="center", va="top", fontsize=7.9,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.0))
    ax.text(boxes[0][0], .03,
            r"注：连续载荷 $z_t^*$ 仅在事件位 $\gamma_t=1$（发送）时产生。",
            fontsize=7.7)
    save(fig, "architecture")


def find_split(record):
    events = record["public"]
    bounds = record["bounds"]
    queries = {item["time"] for item in record["queries"]}
    for t in range(51, 562):
        if (t not in queries and events[t][1] and bounds[t - 1][0] >= ETA
                and bounds[t][0] == 0 and bounds[t][1] >= ETA):
            end = t
            while end <= 561 and end not in queries and bounds[end][0] == 0 and bounds[end][1] >= ETA:
                end += 1
            return t, end - 1
    return None


def separation():
    fig, axes = plt.subplots(1, 2, figsize=(7.25, 2.84), layout="constrained")
    groups = ["strong_positive", "strong_negative"]
    samples, summary = [], []
    for ax, group, sign, sign_text in zip(axes, groups, ["+", "−"], ["强正偏置", "强负偏置"]):
        paths = sorted((STAGE / "results/confirmation").glob(group + "-*.json"))
        trace = load(paths[0])
        t, end = find_split(trace)
        stamp = max(item["time"] for item in trace["queries"] if item["time"] < t)
        lo, hi = stamp - 2, min(561, end + 4)
        times = np.arange(lo, hi + 1)
        values = np.array(trace["bounds"])[times, :] * 1000
        ax.axvspan(t - .5, end + .5, facecolor="#e7ecef", edgecolor="none")
        ax.axhline(ETA * 1000, color=DARK, ls=":", lw=1.1)
        ax.plot(times, values[:, 1], color=BLUE, lw=1.45, marker="o", markersize=2.5, markevery=3)
        ax.plot(times, values[:, 0], color=RED, lw=1.3, ls="--", marker="s", markersize=2.4, markevery=4)
        ax.axvline(t, ls="-.", lw=.9, color=DARK)
        ax.set_title(f"{sign_text}（$b={sign}0.35$ cm，轨迹00）", loc="left")
        ax.text(.97, .94,
                f"第 {t} 拍发送后，M2 下界归零\nM3 下界连续高于门限至第 {end} 拍",
                ha="right", va="top", fontsize=7.9,
                transform=ax.transAxes, bbox=dict(facecolor="white", edgecolor="none", alpha=.88, pad=1.5))
        ax.set(xlabel="时间拍", xlim=(lo, hi))
        ax.set_ylim(-.92, max(values.max() * 1.13, 33))
        ax.grid(axis="y", color="#dddddd", linewidth=.55)
        if group == groups[0]:
            ax.set_ylabel(r"发布下界（$10^{-3}$ cm$^2$）")
        sends = {t0 for t0, sent, *_ in trace["public"] if sent}
        for i in range(lo, hi + 1):
            samples.append(dict(id=trace["id"], t=i, sent=int(i in sends),
                                M2=trace["bounds"][i][0], M3=trace["bounds"][i][1], eta=ETA))
        summary.append(dict(group=group, record=trace["id"], first_split=t,
                            last_contiguous=end, duration=end - t + 1,
                            previous_M2=trace["bounds"][t - 1][0],
                            split_M2=trace["bounds"][t][0], split_M3=trace["bounds"][t][1]))
    legend = [
        Line2D([], [], color=RED, ls="--", marker="s", ms=3,
               label="M2：每拍分别放宽偏置范围"),
        Line2D([], [], color=BLUE, marker="o", ms=3,
               label="M3：跨拍保留固定偏置范围"),
        Line2D([], [], color=DARK, ls=":", label=r"有用校正门限 $\eta$"),
    ]
    fig.legend(handles=legend, loc="outside lower center", ncol=3, frameon=False)
    write_csv("separation_points.csv", samples)
    write_csv("separation_cases.csv", summary)
    save(fig, "separation")


def read_rows(path):
    with path.open(encoding="utf8", newline="") as f:
        return list(csv.DictReader(f))


def mismatch():
    quant = read_rows(ROBUST / "quantization_summary.csv")
    drift = read_rows(ROBUST / "drift_summary.csv")
    paired = read_rows(ROBUST / "incremental_comparisons.csv")

    fig = plt.figure(figsize=(7.25, 4.18), layout="constrained")
    grid = fig.add_gridspec(2, 2, height_ratios=(1, 1.08))
    axes = [fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1]),
            fig.add_subplot(grid[1, :])]
    colors = {"strong_positive": BLUE, "strong_negative": RED}
    labels = {"strong_positive": "强正偏置", "strong_negative": "强负偏置"}

    bit_order = ["continuous", "12bit", "10bit", "8bit", "6bit", "4bit"]
    for group in colors:
        rows = [r for r in quant if r["group"] == group and r["method"] == "M3"]
        rows = sorted(rows, key=lambda r: bit_order.index(r["scenario"]))
        axes[0].plot(["连续", "12", "10", "8", "6", "4"],
                     [float(r["useful_steps_mean"]) for r in rows], "o-",
                     color=colors[group], lw=1.35, ms=3.6, label=labels[group])
    axes[0].set(xlabel="反馈载荷位宽 / bit", ylabel="平均有用校正拍数")
    axes[0].set_title("(a) 反馈量化精度", loc="left")
    axes[0].tick_params(axis="x", labelrotation=0, labelsize=7.4)

    decay_order = ["decay_00", "decay_05", "decay_10", "decay_20", "decay_35", "decay_50"]
    rows = [r for r in drift if r["group"] == "strong_positive" and r["method"] in {"M3", "M3_rho"}]
    for method, label, style, color in [
        ("M3", "静态 M3", "o-", BLUE),
        ("M3_rho", "预留漂移余量的 M3-ρ", "s--", GREY),
    ]:
        vals = {r["scenario"]: float(r["useful_steps_mean"]) for r in rows if r["method"] == method}
        axes[1].plot([0, 5, 10, 20, 35, 50], [vals[s] for s in decay_order], style,
                     color=color, lw=1.35, ms=3.6, label=label)
    axes[1].set(xlabel="偏置全程衰减幅度 / %", ylabel="平均有用校正拍数")
    axes[1].set_title("(b) 偏置缓慢衰减", loc="left")
    axes[1].text(.04, .05,
                 "衰减 50% 时，静态 M3 在 1,202 次检查中有 28 次\n"
                 "下界违约，涉及 12 条轨迹中的 2 条",
                 transform=axes[1].transAxes, ha="left", va="bottom", fontsize=7.5,
                 bbox=dict(facecolor="white", edgecolor="#bbbbbb", pad=2))

    # The paired file stores M3-minus-M2 gains by matched trajectory.
    stable = [r for r in paired if r["experiment"] == "stable_model"
              and r["method"] == "M3" and r["reference"] == "M2"]
    tau_order = ["tau_-5%", "tau_-2%", "tau_-1%", "tau_+0%",
                 "tau_+1%", "tau_+2%", "tau_+5%"]
    tau_x = [-5, -2, -1, 0, 1, 2, 5]
    for group, label, marker, style, color in [
        ("strong_positive", "强正偏置", "o", "-", BLUE),
        ("strong_negative", "强负偏置", "s", "--", RED),
    ]:
        group_rows = {r["scenario"]: r for r in stable if r["group"] == group}
        if all(s in group_rows for s in tau_order):
            axes[2].plot(tau_x, [float(group_rows[s]["gain"]) for s in tau_order],
                         marker=marker, linestyle=style, color=color,
                         lw=1.35, ms=3.6, label=label)
    axes[2].axhline(0, color=DARK, lw=.7)
    axes[2].set(xlabel="水力时间常数相对偏差 / %",
                ylabel="M3 相对 M2 的配对累计降损 / cm²")
    axes[2].set_title("(c) 稳定模型参数摄动", loc="left")
    axes[2].text(.98, .06, "非零摄动组合中，12 组有 9 组出现\n标称风险下界违约",
                 transform=axes[2].transAxes, ha="right", va="bottom", fontsize=7.6,
                 bbox=dict(facecolor="white", edgecolor="#bbbbbb", pad=2))

    for ax in axes:
        ax.grid(axis="y", color="#dddddd", lw=.55)
        ax.legend(frameon=False, loc="best")
    save(fig, "fig3_mismatch_3panel")


if __name__ == "__main__":
    architecture()
    separation()
    mismatch()
