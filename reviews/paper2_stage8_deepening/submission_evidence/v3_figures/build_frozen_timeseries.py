"""Reconstruct a time-series figure from one exactly verified frozen test seed."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]
STAGE_CODE = STAGE / "code"
sys.path.insert(0, str(STAGE_CODE))

from experiment import D, Methods, record

ID = "strong_positive-00"
DATA = STAGE / "results" / "confirmation" / f"{ID}.json"
REGISTRATION = STAGE / "registration.json"
FIGURE_STEM = "state_error_and_events"

BLUE = "#124c70"
RED = "#923d30"
GREY = "#626b73"
DARK = "#222222"
plt.rcParams.update({
    "font.family": "Microsoft YaHei UI",
    "font.size": 8.4,
    "axes.titlesize": 9.0,
    "axes.labelsize": 8.1,
    "legend.fontsize": 7.6,
    "pdf.fonttype": 42,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.unicode_minus": False,
    "mathtext.fontset": "stix",
})


def main() -> None:
    frozen = json.loads(DATA.read_text(encoding="utf8"))
    registration = json.loads(REGISTRATION.read_text(encoding="utf8"))
    amplitude = float(frozen["b"])
    group_index = list(registration["groups"]).index(frozen["group"])
    public, states = record(
        registration["test_seed"], group_index, int(frozen["index"]), amplitude
    )
    if public != frozen["public"]:
        raise RuntimeError("Recreated public events and payloads differ from the frozen record")

    methods = Methods(D(str(registration["strong"])), registration["threshold"])
    time = []
    errors = {"M0": [], "M2": [], "M3": []}
    events = []
    for frame, state in zip(public, states, strict=True):
        t, sent, _, _ = frame
        actions, _, _, _ = methods.step(frame)
        monitor = np.asarray(methods.monitor, dtype=float)
        state = np.asarray(state, dtype=float)
        time.append(t)
        events.append(int(sent))
        errors["M0"].append(float(np.linalg.norm(monitor - state)))
        for name in ("M2", "M3"):
            action = np.asarray(actions[name][0], dtype=float)
            errors[name].append(float(np.linalg.norm(monitor - action - state)))

    rows = [
        {"time": t, "event": event,
         "M0_error_norm_cm": errors["M0"][i],
         "M2_error_norm_cm": errors["M2"][i],
         "M3_error_norm_cm": errors["M3"][i]}
        for i, (t, event) in enumerate(zip(time, events, strict=True))
    ]
    with (HERE / f"{FIGURE_STEM}.csv").open("w", newline="", encoding="utf8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    # Smooth measurement-noise-scale fluctuations without changing the frozen
    # trajectory. This makes the sustained estimator-bias response legible.
    window = 25
    smoothed = {
        name: np.sqrt(np.convolve(np.square(values), np.ones(window) / window, mode="valid"))
        for name, values in errors.items()
    }
    smooth_time = time[window - 1:]

    figure, axes = plt.subplots(2, 1, figsize=(7.25, 3.25), sharex=True,
                                gridspec_kw={"height_ratios": [2.0, .72]},
                                layout="constrained")
    upper, lower = axes
    upper.plot(smooth_time, smoothed["M0"], color=GREY, linestyle=(0, (3, 1.5)), linewidth=1.0,
               label="M0：未补偿")
    upper.plot(smooth_time, smoothed["M2"], color=RED, linestyle="--", linewidth=1.0,
               label="M2：半空间补偿")
    upper.plot(smooth_time, smoothed["M3"], color=BLUE, linewidth=1.05,
               label="M3：幅值区间补偿")
    upper.axvline(50, color=RED, linestyle=":", linewidth=1.0)
    for query_time in registration["query_times"]:
        upper.axvline(query_time, color="#9aa1a8", linestyle=(0, (1, 2)), linewidth=.7)
        lower.axvline(query_time, color="#9aa1a8", linestyle=(0, (1, 2)), linewidth=.7)
    upper.text(55, upper.get_ylim()[1] * .92, "偏置开始（第50拍）", color=RED, fontsize=6.8,
               ha="left", va="top", bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
    upper.set_ylabel(r"25拍滑动均方根误差 $\|m_t-x_t\|_2$ / cm")
    upper.set_title("一条冻结强正偏置序列的估计误差变化", loc="left", pad=4)
    upper.grid(axis="y", color="#dddddd", linewidth=.45)
    upper.legend(frameon=False, ncol=3, loc="lower right", fontsize=6.8)

    sent_times = [t for t, sent in zip(time, events, strict=True) if sent]
    lower.vlines(sent_times, 0, 1, color=BLUE, linewidth=.55)
    lower.set_ylim(0, 1.30)
    lower.set_yticks([])
    lower.set_xlabel("时间拍 $t$")
    lower.set_ylabel("发送事件", labelpad=7)
    lower.set_xticks([0, 50, 127, 255, 383, 511, 607])
    lower.grid(axis="x", color="#eeeeee", linewidth=.45)
    lower.legend(handles=[
        Line2D([], [], color=BLUE, linewidth=.9, label=f"发送事件 $\\gamma_t=1$（{sum(events)}次）"),
        Line2D([], [], color=RED, linestyle=":", linewidth=1, label="偏置开始"),
        Line2D([], [], color="#9aa1a8", linestyle=(0, (1, 2)), linewidth=.7,
               label="查询时刻：127、255、383、511拍"),
    ], frameon=False, ncol=3, loc="upper right", fontsize=6.3)

    for extension in ("pdf", "png"):
        figure.savefig(HERE / f"{FIGURE_STEM}.{extension}", dpi=600,
                       bbox_inches="tight", pad_inches=.04,
                       metadata={"Creator": "Frozen-seed deterministic replay"})
    plt.close(figure)
    print(json.dumps({
        "frozen_id": frozen["id"],
        "seed": registration["test_seed"],
        "public_record_exact_match": True,
        "steps": len(public),
        "send_events": sum(events),
        "query_times": registration["query_times"],
        "figure": f"{FIGURE_STEM}.pdf",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
