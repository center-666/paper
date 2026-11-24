"""Render the preregistered Oracle gate metrics from stored results only."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE / "results" / "oracle_v1"


def main():
    report = json.loads((ROOT/"summary.json").read_text(encoding="utf8"))
    rows = report["attack/0/stop64"]["cells"]
    with (ROOT/"example.csv").open(encoding="utf8") as stream:
        example = list(csv.DictReader(stream))
    fig, axes = plt.subplots(2, 2, figsize=(10.2, 7.2), layout="constrained")
    ax = axes[0, 0]
    labels = []
    for index, cell in enumerate(rows.values()):
        stats = cell["M4_gain"]
        mean = stats["mean"]
        lo, hi = stats["t95"]
        labels.append(f"{cell['b']:+.2f} / {cell['duration']}")
        ax.errorbar(mean, index, xerr=[[mean-lo], [hi-mean]], fmt="o", capsize=3, color="#116562")
    ax.set_yticks(range(len(labels)), labels)
    ax.invert_yaxis()
    ax.axvline(0, color="0.45", linewidth=.8)
    ax.set(xlabel="Monitor minus TRSR loss (64 steps)", ylabel="Bias / duration",
           title="A   Paired effects and 95% intervals")
    ax = axes[0, 1]
    delays = [0, 5, 20, 60, 128]
    ideal = report["attack/0/stop64"]["overall"]["M5"]["conditional"]["mean"]
    for method, label, color in [("M5","Direct oracle","#343951"),("M4","TRSR oracle","#116562")]:
        vals = [report[f"attack/{d}/stop64"]["overall"][method]["conditional"]["mean"]/ideal*100 for d in delays]
        ax.plot(range(len(delays)), vals, "o-", label=label, color=color)
    ax.set_xticks(range(len(delays)), delays)
    ax.set(xlabel="Delay after stop (steps)", ylabel="% of zero-delay direct-oracle energy",
           title="B   Recoverable conditional gain")
    ax.legend(frameon=False)
    relative = np.array([int(r["t"])-int(r["stop"]) for r in example])
    use = (relative >= -20) & (relative < 40)
    ax = axes[1, 0]
    for method, label, color in [("M0","Monitor","#818799"),("M2","Hard replay","#c07643"),("M4","TRSR oracle","#116562")]:
        err = np.array([float(r[method+"_x0"])-float(r["truth0"]) for r in example])
        ax.plot(relative[use], err[use], label=label, color=color, linewidth=1.3)
    ax.axvline(0,color="0.35",linestyle=":")
    ax.set(xlabel="Step relative to stop", ylabel="First-state error", title="C   Prespecified example (cell 7, episode 0)")
    ax.legend(frameon=False,fontsize=8)
    ax = axes[1, 1]
    weights = np.array([float(r["lambda"]) for r in example])
    ax.step(relative[use], weights[use], where="mid",color="#116562")
    ax.axvline(0,color="0.35",linestyle=":")
    ax.set(xlabel="Step relative to stop", ylabel="Recovery weight", ylim=(-.05,1.05),
           title="D   Weight for the same episode")
    for ax in axes.flat:
        ax.spines[["right","top"]].set_visible(False)
    fig.savefig(ROOT/"oracle_gate.pdf", metadata={"CreationDate":None,"ModDate":None})
    plt.close(fig)


if __name__ == "__main__":
    main()
