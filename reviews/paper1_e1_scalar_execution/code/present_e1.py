"""Publication layout only: read frozen audited summaries, no numerical reruns."""
from pathlib import Path
import argparse
import json
import hashlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FixedFormatter, NullLocator


def main():
    ap=argparse.ArgumentParser();ap.add_argument("run");args=ap.parse_args()
    run=Path(args.run).resolve();data=run/"analysis/summary.json"
    assert json.loads((run/"analysis/analysis_validation.json").read_text())["status"]=="PASS"
    out=run/"presentation_v1"
    if out.exists():raise SystemExit("Presentation output already exists.")
    out.mkdir()
    rows=json.loads(data.read_text(encoding="utf-8"))["cases"]
    plt.rcParams.update({"font.size":9,"axes.labelsize":9,"legend.fontsize":8})
    fig,axes=plt.subplots(2,2,figsize=(9.2,6.4),layout="constrained")
    keys=["J_paired","J_over_delta_squared","clean_mse","clean_send_rate"]
    labels=["Witness damage J (not a worst-case value)",r"$J/\delta^2$",
            "Healthy target MSE (own protocol)","Healthy uplink fraction (t=0..5)"]
    for mid,color in [("S1","#2166ac"),("U1","#b2182b")]:
        for protocol,marker,ls in [("A","s","--"),("B","o","-")]:
            cell=[r for r in rows if r["model"]==mid and r["protocol"]==protocol]
            x=[r["delta"] for r in cell]
            for ax,key in zip(axes.ravel(),keys):
                y=[r["statistics"][key]["mean"] for r in cell]
                ci=np.array([r["statistics"][key]["bootstrap_percentile_95"] for r in cell])
                ax.plot(x,y,color=color,marker=marker,linestyle=ls,label=f"{mid} {protocol}",markersize=4)
                ax.fill_between(x,ci[:,0],ci[:,1],color=color,alpha=.08)
    for ax,label in zip(axes.ravel(),labels):
        ax.set_xscale("log")
        ax.xaxis.set_major_locator(FixedLocator([.003,.006,.012,.024]))
        ax.xaxis.set_major_formatter(FixedFormatter(["0.003","0.006","0.012","0.024"]))
        ax.xaxis.set_minor_locator(NullLocator())
        ax.set_xlabel(r"$\delta$ (A: common dose label; B: feedback precision)")
        ax.set_ylabel(label);ax.grid(alpha=.22)
    axes[0,0].set_yscale("log");axes[0,0].legend(ncol=2)
    fig.suptitle("Frozen scalar E1: k=4, b=0.1, N=2048 independent base samples/model\n"
                 "Bands: 1000 paired-base bootstrap replicates; precision-dominated region only",fontsize=10)
    for ext in ["png","pdf"]:fig.savefig(out/("e1_mechanism."+ext),dpi=200)
    plt.close(fig)
    (out/"manifest.json").write_text(json.dumps({
        "input_summary_sha256":hashlib.sha256(data.read_bytes()).hexdigest(),
        "purpose":"Layout refinement: fixed x tick labels; all curves/intervals unchanged.",
        "new_numerical_results":False,"original_plot_retained":"../analysis/e1_mechanism.pdf",
        "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "files":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.suffix in (".png",".pdf")},
    },indent=2),encoding="utf-8")


if __name__=="__main__":
    main()
