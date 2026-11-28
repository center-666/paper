"""Build article figures with labels that remain readable at journal width."""
from pathlib import Path
import csv
import json

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.legend_handler import HandlerTuple
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
        "sensor": (2.05, 2.55, 1.95, 1.00, "传感与随机触发", "输入量测 $y_t$ 与中心 $c_t$\n输出受保护事件位 $\\gamma_t$"),
        "attack": (4.23, 2.55, 1.88, 1.00, "上行链路偏置攻击", "$z_t=y_t+b$\n仅 $t\\geq k$ 且 $\\gamma_t=1$"),
        "monitor": (6.34, 2.55, 2.02, 1.00, "名义状态估计器", "发送时：以 $z_t$ 更新\n静默时：以 $c_t$ 更新"),
        "output": (10.20, 2.55, 2.55, 1.00, "补偿后估计输出", "$m_t^R=m_t^M-a_t$"),
        "m3": (6.125, 0.48, 2.45, 1.05, "幅值区间补偿器（M3）", "按公开记录计算限幅量 $a_t$"),
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

    ax.text(5.18, 3.86, "受保护事件位与上行数据帧", ha="center", fontsize=6.8,
            bbox=dict(facecolor="white", edgecolor="none", pad=.5))

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
    ax.text(.30, .08, "$\\gamma_t=0$ 为传感端报告的静默事件；补偿不回写名义状态。",
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
        ax.set_title(f"{sign_text}（$b={sign}0.35$ cm，典型样本）", loc="left")
        if group == "strong_positive":
            callout = "515拍：M2无正下界，M3至558拍\n条件改善59.01，下界25.50（10⁻³ cm²）"
        else:
            callout = f"{t}拍后：M2无正下界，M3至{end}拍"
        ax.text(.03, .965, callout, ha="left", va="top", fontsize=6.7,
                transform=ax.transAxes,
                bbox=dict(facecolor="white", edgecolor="#b8c0c8", alpha=.96, pad=1.5))
        ax.set(xlabel="采样时刻 $t$", xlim=(lo, hi))
        top = max(values.max() * 1.16, 35)
        ax.set_ylim(-.92, top)
        if group == "strong_positive":
            actual = (0.28203826574566204**2 - 0.14330258308047225**2)*1000
            certified = trace["bounds"][515][1]*1000
            ax.scatter([515, 515], [0, certified], s=[20, 30],
                       marker="o", facecolors=["white", BLUE],
                       edgecolors=[RED, BLUE], linewidths=1.2, zorder=7)

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
    fig, axes = plt.subplots(1, 2, figsize=(7.25, 2.55), layout="constrained")
    groups = [("strong_positive", BLUE, "o", "强正偏置", "-"),
              ("strong_negative", RED, "s", "强负偏置", "--")]
    order = ["continuous", "12bit", "10bit", "8bit", "6bit", "4bit"]
    tick_labels = ["连续", "12", "10", "8", "6", "4"]

    def draw_point(ax, x, y, color, marker, exceeded):
        ax.scatter([x], [y], s=47 if exceeded else 28, marker=marker,
                   facecolors="white" if exceeded else color,
                   edgecolors=RED if exceeded else color, linewidths=1.25, zorder=5)
        if exceeded:
            ax.scatter([x], [y], s=28, marker="x", color=RED, linewidths=1.3, zorder=6)

    for group, color, marker, label, line_style in groups:
        rows = [row for row in quant if row["group"] == group
                and row["method"] == "M3" and row["scenario"] in order]
        by_scenario = {row["scenario"]: row for row in rows}
        ys = [float(by_scenario[scenario]["useful_steps_mean"]) for scenario in order]
        axes[0].plot(np.arange(len(order)), ys, line_style, color=color, lw=1.5, label=label)
        for x, scenario, y in zip(range(len(order)), order, ys):
            row = by_scenario[scenario]
            draw_point(axes[0], x, y, color, marker, int(row["risk_violations"] or 0) > 0)
    axes[0].set_xticks(range(len(order)), tick_labels)
    axes[0].set(xlabel="上行量测位宽 / bit", ylabel="平均有效补偿步数")
    axes[0].set_title("(a) 量测量化", loc="left")
    axes[0].set_ylim(0, 50)
    axes[0].legend(frameon=False, loc="lower left")
    axes[0].text(.98, .04, "4 bit：近似核验超过下界\n强正 75/2409，强负 149/1447\n健康 M3 出手 3/12",
                 ha="right", va="bottom", fontsize=7.0, transform=axes[0].transAxes,
                 bbox={"facecolor": "white", "edgecolor": "#bbbbbb", "pad": 1.5})

    scenarios = ["decay_00", "decay_05", "decay_10", "decay_20", "decay_35", "decay_50"]
    xs = [0, 5, 10, 20, 35, 50]
    records = [row for row in drift if row["group"] == "strong_positive"
               and row["method"] in {"M3", "M3_rho"}]
    by_method = {method: {row["scenario"]: row for row in records if row["method"] == method}
                 for method in ("M3", "M3_rho")}
    for method, color, marker, line, label in [
        ("M3", BLUE, "o", "-", "静态 M3"),
        ("M3_rho", GREY, "s", "--", r"漂移余量法 M3-$\rho$")]:
        ys = [float(by_method[method][sc]["useful_steps_mean"]) for sc in scenarios]
        axes[1].plot(xs, ys, line, color=color, lw=1.5, label=label)
        for x, sc, y in zip(xs, scenarios, ys):
            row = by_method[method][sc]
            draw_point(axes[1], x, y, color, marker, int(row["risk_violations"] or 0) > 0)
    axes[1].set(xlabel="偏置总衰减 / %", ylabel="平均有效补偿步数")
    axes[1].set_title("(b) 偏置缓慢衰减", loc="left")
    axes[1].set_ylim(0, 48)
    axes[1].legend(frameon=False, loc="upper right")
    axes[1].text(.03, .04, "衰减50%：静态下界28/1202次偏低，涉及2/12条\n"
                 "漂移余量法：0/1202次；上游覆盖尚未建立",
                 ha="left", va="bottom", fontsize=7.0, transform=axes[1].transAxes,
                 bbox={"facecolor": "white", "edgecolor": "#bbbbbb", "pad": 1.5})
    for ax in axes:
        ax.grid(axis="y", linestyle="--", alpha=.25, linewidth=.55)
    no_exceed = Line2D([], [], color=DARK, marker="o", ls="None",
                       markerfacecolor=DARK, label="核验中未见条件改善低于下界")
    exceed = (Line2D([], [], color=RED, marker="o", ls="None", markerfacecolor="white"),
              Line2D([], [], color=RED, marker="x", ls="None"))
    fig.legend([no_exceed, exceed],
               ["核验中未见下界不符", "观察到条件改善低于标称下界"],
               handler_map={tuple: HandlerTuple(ndivide=1)}, loc="outside lower center",
               ncol=2, frameon=False, fontsize=7.2)
    fig.savefig(HERE / "robustness_2panel.pdf", dpi=600, facecolor="white",
                bbox_inches="tight", pad_inches=.08,
                metadata={"Creator": "Registered quantization and drift summaries"})
    fig.savefig(HERE / "robustness_2panel.png", dpi=600, facecolor="white",
                bbox_inches="tight", pad_inches=.08,
                metadata={"Creator": "Registered quantization and drift summaries"})
    plt.close(fig)


if __name__ == "__main__":
    architecture()
    separation()
    mismatch()
from matplotlib.legend_handler import HandlerTuple
from matplotlib.legend_handler import HandlerTuple
