"""Reconstruct a time-series figure from one exactly verified frozen test seed."""
from __future__ import annotations

import hashlib
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

from experiment import D, Methods, WINDOW

ID = "strong_positive-00"
DATA = STAGE / "results" / "confirmation" / f"{ID}.json"
REGISTRATION = STAGE / "registration.json"
FIGURE_STEM = "state_error_and_events"

BLUE = "#1F4E79"
RED = "#B03A2E"
GREY = "#626b73"
DARK = "#222222"
plt.rcParams.update({
    "font.family": "SimSun",
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
    methods = Methods(D(str(registration["strong"])), registration["threshold"])
    response = np.zeros(2)
    hashes = {name: hashlib.sha256() for name in ("M2", "M3")}
    cumulative = dict.fromkeys(hashes, 0.0)
    rows = []
    for frame in frozen["public"]:
        t, sent, _, _ = frame
        actions, _, gain, transition = methods.step(frame)
        response = transition @ response
        if sent and t >= registration["onset"]:
            response += gain
        bias = amplitude * response
        row = {"t": t, "sent": int(sent), "M0_cm": np.linalg.norm(bias)}
        for name in hashes:
            action = np.asarray(actions[name][0], dtype=float)
            hashes[name].update(action.astype(">f8").tobytes())
            row[name + "_cm"] = np.linalg.norm(bias - action)
            if t in WINDOW:
                cumulative[name] += row["M0_cm"]**2 - row[name + "_cm"]**2
        rows.append(row)
    for name in hashes:
        assert hashes[name].hexdigest() == frozen["actions_sha256"][name]
        np.testing.assert_allclose(cumulative[name], frozen["metrics"][name]["conditional"],
                                   rtol=0, atol=1e-12)
    with (HERE / f"{FIGURE_STEM}.csv").open("w", newline="", encoding="utf8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    fig, (upper, lower) = plt.subplots(2, 1, sharex=True, figsize=(6.85, 2.45),
                                      gridspec_kw={"height_ratios": [3, 1]}, layout="constrained")
    for name, color, style, label in [
        ("M0", GREY, ":", "M0 未补偿"), ("M2", RED, "--", "M2 半空间法"),
        ("M3", BLUE, "-", "M3 区间法")]:
        upper.plot([r["t"] for r in rows], [r[name + "_cm"] for r in rows],
                   color=color, ls=style, lw=1.5, label=label)
    upper.legend(loc="lower center", bbox_to_anchor=(.5, 1.0), ncol=3, frameon=False)
    upper.set_ylabel("残余偏置范数 / cm")
    upper.grid(axis="y", linestyle="--", alpha=.25)
    lower.vlines([r["t"] for r in rows if r["sent"]], 0, 1, color=GREY)
    lower.set(yticks=[], ylabel="发送事件", xlabel="采样时刻 $t$", xlim=(375,561),
              xticks=[375,383,410,435,460,485,511,530,561])
    for ax in (upper, lower):
        for stamp in (383,511):
            ax.axvline(stamp, lw=.8, ls="-.", color=GREY)
    for ext in ("pdf","png"):
        fig.savefig(HERE / f"{FIGURE_STEM}.{ext}", dpi=600, bbox_inches="tight", pad_inches=.08)
    plt.close(fig)
    print(cumulative)


if __name__ == "__main__":
    main()
