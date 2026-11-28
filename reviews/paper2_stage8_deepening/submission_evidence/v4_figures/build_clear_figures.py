"""Build article figures with labels that remain readable at journal width."""
from pathlib import Path
import csv
import json

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrowPatch, Patch, Rectangle
import numpy as np

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]
ROBUST = STAGE / "robustness_exploration"
ETA = 1 / 1600
BLUE, RED, DARK, GREY = "#1F4E79", "#B03A2E", "#222222", "#666666"

ZH_FONT = "SimSun"
plt.rcParams.update({
    "font.family": [ZH_FONT, "Times New Roman"],
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
        fig.savefig(HERE / f"{name}.{fmt}", dpi=600, facecolor="white",
                    bbox_inches="tight", pad_inches=.08,
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
    fig, ax = plt.subplots(figsize=(7.25, 3.05))
    ax.set(xlim=(0, 13), ylim=(0, 5))
    ax.axis("off")

    boxes = {
        "plant": (0.30, 2.55, 1.52, 1.00, "被控对象", "输出量测 $y_t$"),
        "sensor": (2.05, 2.55, 1.95, 1.00, "传感与随机触发", "输入 $y_t$ 与 $c_t$\n输出事件位 $\\gamma_t$"),
        "attack": (4.23, 2.55, 1.88, 1.00, "发送后载荷注入", "$z_t=y_t+b$\n仅 $t\\geq k$ 且 $\\gamma_t=1$"),
        "monitor": (6.34, 2.55, 2.02, 1.00, "名义状态估计器", "接收 $z_t$，更新 $m_t^M$"),
        "output": (10.20, 2.55, 2.55, 1.00, "补偿后估计输出", "$m_t^R=m_t^M-a_t$"),
        "m3": (6.125, 0.48, 2.45, 1.05, "区间补偿器（M3）", "读取公开记录并计算 $a_t$"),
    }
    for key, (x, y, width, height, title, detail) in boxes.items():
        edge = RED if key == "attack" else (BLUE if key == "m3" else DARK)
        style = "--" if key == "attack" else "-"
        ax.add_patch(Rectangle((x, y), width, height, facecolor={"attack": "#FDEDEC", "m3": "#EBF5FB"}.get(key, "#f4f5f6"),
                               edgecolor=edge, lw=1.05, linestyle=style))
        ax.text(x + width / 2, y + .69, title, ha="center", va="center",
                fontsize=7.8, fontweight="bold", color=edge if key == "attack" else DARK)
        ax.text(x + width / 2, y + .28, detail, ha="center", va="center", fontsize=6.9)

    def arrow(start, end, color=DARK, style="-", mutation=9.6):
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=mutation,
                                     color=color, lw=1.0, linestyle=style, shrinkA=0, shrinkB=0))

    y_mid = 3.05
    arrow((1.82, y_mid), (2.05, y_mid))
    arrow((4.00, y_mid), (4.23, y_mid))
    arrow((6.11, y_mid), (6.34, y_mid), RED, "--")

    # The monitor sends its uncorrected estimate to a separate subtraction node.
    monitor_right = boxes["monitor"][0] + boxes["monitor"][2]
    sum_x = 9.55
    ax.add_patch(Circle((sum_x, y_mid), .21, facecolor="white", edgecolor=DARK, lw=1))
    arrow((monitor_right, y_mid), (sum_x - .21, y_mid))
    ax.text(9.12, 3.32, r"$m_t^M$", ha="center", fontsize=7.2)
    ax.text(sum_x - .32, y_mid + .18, "+", ha="center", va="center", fontsize=10.5)
    arrow((sum_x + .21, y_mid), (10.20, y_mid))

    # Trusted feedback and audit records use separate paths.
    monitor_cx = boxes["monitor"][0] + boxes["monitor"][2] / 2
    sensor_cx = boxes["sensor"][0] + boxes["sensor"][2] / 2
    ax.plot([monitor_cx, monitor_cx, sensor_cx], [3.55, 4.44, 4.44], color=DARK, lw=.9)
    arrow((sensor_cx, 4.44), (sensor_cx, 3.55))
    ax.text(5.18, 4.54, r"下行反馈：共享预测中心 $c_t$", ha="center", fontsize=7.4,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.0))

    m3_cx = boxes["m3"][0] + boxes["m3"][2] / 2
    arrow((monitor_cx, 2.55), (monitor_cx, 1.53))
    ax.text(7.05, 2.02, r"可信记录 $(c_t,\gamma_t,\gamma_tz_t)$", ha="right", va="center",
            fontsize=6.8, bbox=dict(facecolor="white", edgecolor="none", pad=.6))

    m3_right = boxes["m3"][0] + boxes["m3"][2]
    ax.plot([m3_right, sum_x], [.95, .95], color=DARK, lw=.9)
    arrow((sum_x, .95), (sum_x, y_mid - .21))
    ax.text(9.72, 1.26, r"$a_t$", ha="center", fontsize=7.5,
            bbox=dict(facecolor="white", edgecolor="none", pad=.5))
    ax.text(sum_x + .24, y_mid - .31, "−", ha="center", va="center", fontsize=10.5, color=DARK)
    ax.text(.30, .08, "事件判决先于载荷注入；补偿器仅改变输出估计。",
            fontsize=7.0)

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
    fig, axes = plt.subplots(1, 2, figsize=(7.25, 2.93), layout="constrained")
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
        ax.axvline(t, ymax=.90, ls="-.", lw=.9, color=DARK)
        ax.set_title(f"{sign_text}（$b={sign}0.35$ cm，首条分离样例）", loc="left")
        ax.text(.97, .94,
                f"第 {t} 拍后 M2 首次归零\nM3 高于门限至第 {end} 拍",
                ha="right", va="top", fontsize=7.6,
                transform=ax.transAxes, bbox=dict(facecolor="white", edgecolor="none", alpha=.88, pad=1.5))
        ax.set(xlabel="时间拍", xlim=(lo, hi))
        top = max(values.max() * 1.16, 35)
        ax.set_ylim(-.92, top)
        sends = [t0 for t0, sent, *_ in trace["public"] if sent and lo <= t0 <= hi]
        ax.scatter(sends, np.full(len(sends), top * .975), marker="v", color="#5d6670",
                   s=13, zorder=5, clip_on=False)
        ax.grid(axis="y", ls="--", alpha=.25, linewidth=.55)
        if group == groups[0]:
            ax.set_ylabel(r"条件 MSE 改善下界 / ($10^{-3}$ cm$^2$)")
        sends_all = {t0 for t0, sent, *_ in trace["public"] if sent}
        for i in range(lo, hi + 1):
            samples.append(dict(id=trace["id"], t=i, sent=int(i in sends_all),
                                M2=trace["bounds"][i][0], M3=trace["bounds"][i][1], eta=ETA))
        summary.append(dict(group=group, record=trace["id"], first_split=t,
                            last_contiguous=end, duration=end - t + 1,
                            previous_M2=trace["bounds"][t - 1][0],
                            split_M2=trace["bounds"][t][0], split_M3=trace["bounds"][t][1]))
    legend = [
        Line2D([], [], color=RED, ls="--", marker="s", ms=3,
               label="M2：逐拍放宽半空间法"),
        Line2D([], [], color=BLUE, marker="o", ms=3,
               label="M3：固定幅值区间法"),
        Line2D([], [], color=DARK, ls=":", label=r"有效补偿阈值 $\eta$"),
        Line2D([], [], color="#5d6670", marker="v", ls="None", ms=4,
               label=r"后续发送时刻（$\gamma_t=1$）"),
        Patch(facecolor="#e7ecef", edgecolor="none", label="灰影：两法分离窗口"),
    ]
    fig.legend(handles=legend, loc="outside lower center", ncol=3, frameon=False, fontsize=7.5)
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
    model_audit = read_rows(ROBUST / "model_mismatch_summary.csv")

    fig = plt.figure(figsize=(7.25, 4.42), layout="constrained")
    grid = fig.add_gridspec(2, 2, height_ratios=(1, 1.08))
    axes = [fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1]),
            fig.add_subplot(grid[1, :])]
    colors = {"strong_positive": BLUE, "strong_negative": RED}
    labels = {"strong_positive": "强正偏置", "strong_negative": "强负偏置"}
    markers = {"strong_positive": "o", "strong_negative": "s"}

    def add_audit_marker(ax, x, y, color, marker, violated):
        ax.scatter([x], [y], marker=marker, s=44 if violated else 23,
                   facecolors="white" if violated else color,
                   edgecolors="#C0392B" if violated else color, linewidths=1.25, zorder=5)
        if violated:
            ax.scatter([x], [y], marker="x", s=30, color="#C0392B", linewidths=1.45, zorder=6)

    bit_order = ["continuous", "12bit", "10bit", "8bit", "6bit", "4bit"]
    bit_labels = ["连续", "12", "10", "8", "6", "4"]
    x_bit = np.arange(len(bit_order))
    for group in colors:
        rows = [r for r in quant if r["group"] == group and r["method"] == "M3"]
        rows = sorted(rows, key=lambda r: bit_order.index(r["scenario"]))
        y_values = [float(r["useful_steps_mean"]) for r in rows]
        axes[0].plot(x_bit, y_values, "-" if group == "strong_positive" else "--", color=colors[group], lw=1.35,
                     label=labels[group])
        for x, row, y in zip(x_bit, rows, y_values):
            add_audit_marker(axes[0], x, y, colors[group], markers[group],
                             int(row["risk_violations"] or 0) > 0)
    axes[0].set_xticks(x_bit, bit_labels)
    axes[0].set(xlabel="反馈载荷位宽 / bit", ylabel="平均有效补偿步数")
    axes[0].set_title("(a) 反馈量化精度", loc="left")
    axes[0].set_ylim(4, 52)
    axes[0].text(.97, .04,
                 "4 bit 近似核验违约\n强正75/2409，强负149/1447\n健康组误动3/12",
                 transform=axes[0].transAxes, ha="right", va="bottom", fontsize=6.6,
                 bbox=dict(facecolor="white", edgecolor="#bbbbbb", pad=1.5))
    axes[0].tick_params(axis="x", labelrotation=0, labelsize=7.4)

    decay_order = ["decay_00", "decay_05", "decay_10", "decay_20", "decay_35", "decay_50"]
    rows = [r for r in drift if r["group"] == "strong_positive" and r["method"] in {"M3", "M3_rho"}]
    for method, label, style, color in [
        ("M3", "静态 M3", "o-", BLUE),
        ("M3_rho", "预留漂移余量的 M3-ρ", "s--", GREY),
    ]:
        method_rows = {r["scenario"]: r for r in rows if r["method"] == method}
        x_decay = [0, 5, 10, 20, 35, 50]
        y_decay = [float(method_rows[s]["useful_steps_mean"]) for s in decay_order]
        line_style = "-" if method == "M3" else "--"
        axes[1].plot(x_decay, y_decay, line_style, color=color, lw=1.35, label=label)
        marker = "o" if method == "M3" else "s"
        for x, scenario in zip(x_decay, decay_order):
            row = method_rows[scenario]
            add_audit_marker(axes[1], x, float(row["useful_steps_mean"]), color, marker,
                             int(row["risk_violations"] or 0) > 0)
    axes[1].set(xlabel="偏置全程衰减幅度 / %", ylabel="平均有效补偿步数")
    axes[1].set_title("(b) 偏置缓慢衰减", loc="left")
    axes[1].text(.04, .04,
                 "衰减50%：静态M3违约28/1202（2/12轨）\n"
                 "预留漂移余量的M3-$\\rho$：0/1202",
                 transform=axes[1].transAxes, ha="left", va="bottom", fontsize=7.0,
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
            y_values = [float(group_rows[s]["gain"]) for s in tau_order]
            axes[2].plot(tau_x, y_values, linestyle=style, color=color,
                         lw=1.35, label=label)
            audit_rows = {
                r["scenario"]: r for r in model_audit
                if r["experiment"] == "stable_model" and r["method"] == "M3"
                and r["group"] == group
            }
            for x, scenario, y in zip(tau_x, tau_order, y_values):
                violated = int(audit_rows[scenario]["risk_violations"] or 0) > 0
                add_audit_marker(axes[2], x, y, color, marker, violated)
    axes[2].axhline(0, color=DARK, lw=.7)
    axes[2].set(xlabel="水力时间常数相对偏差 / %",
                ylabel="M3 相对 M2 的配对累计降损 / cm²")
    axes[2].set_xticks(tau_x, ["−5", "−2", "−1", "0", "1", "2", "5"])
    axes[2].set_title("(c) 稳定模型参数摄动", loc="left")
    axes[2].text(.98, .06, "降损均值仍为正，但下界违约\n9/12个非零摄动与偏置符号组合",
                 transform=axes[2].transAxes, ha="right", va="bottom", fontsize=7.6,
                 bbox=dict(facecolor="white", edgecolor="#bbbbbb", pad=2))

    for ax in axes:
        ax.grid(axis="y", color="#dddddd", lw=.55)
        ax.legend(frameon=False, loc="lower left" if ax is axes[2] else "best", fontsize=7.5)
    audit_legend = [
        Line2D([], [], color=DARK, marker="o", ls="None", markerfacecolor=DARK,
               label="核验中未见下界违约"),
        Line2D([], [], color=DARK, marker="X", markerfacecolor="white", markeredgecolor="#C0392B", markeredgewidth=1.6, ls="None",
               label="出现标称下界违约"),
    ]
    fig.legend(handles=audit_legend, loc="outside lower center", ncol=2,
               frameon=False, fontsize=7.4)
    save(fig, "fig3_mismatch_3panel")


if __name__ == "__main__":
    architecture()
    separation()
    mismatch()
