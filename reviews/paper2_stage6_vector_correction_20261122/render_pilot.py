"""Plot all three final pilot settings; no new random inputs."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
data=json.loads((HERE/"analysis/summary.json").read_text(encoding="utf8"))
rows=sorted([r for r in data["rows"] if r["H"]==512],key=lambda r:r["b"])
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"pdf.fonttype":42,
                     "axes.spines.top":False,"axes.spines.right":False})
fig,axes=plt.subplots(1,2,figsize=(11,4.5),constrained_layout=True)
x=np.arange(3);width=.32
for offset,key,color,label in ((-.5,"point_gain","#df8b2a","Point-estimate compensation"),
                              (.5,"certified_gain","#2679a9","Directional certificate")):
    values=np.array([r[key]["mean"] for r in rows])
    low=np.array([r[key]["student_95_low"] for r in rows])
    high=np.array([r[key]["student_95_high"] for r in rows])
    axes[0].bar(x+offset*width,values,width,yerr=[values-low,high-values],color=color,
                label=label,capsize=4,alpha=.85)
axes[0].axhline(0,color="black",linewidth=.7)
axes[0].set_xticks(x,["Healthy","b=0.10","b=0.25"])
axes[0].set(title="Actual 512-step paired MSE improvement",
            ylabel="Monitor loss minus corrected loss")
axes[0].legend(fontsize=8)
bottom=np.zeros(3)
for key,color,label in (("maintenance","#4682b4","All-onset cache + reference"),
                        ("point_scoring","#c1ad46","Point scoring"),
                        ("certificate_search","#df8b2a","Continuous certificate search"),
                        ("transport","#648c5a","Halfspace propagation")):
    vals=np.array([r["cost"][key]["mean"] for r in rows])
    axes[1].bar(x,vals,bottom=bottom,color=color,label=label)
    bottom+=vals
rest=np.maximum(0,np.array([r["total_run_seconds"]["mean"] for r in rows])-bottom)
axes[1].bar(x,rest,bottom=bottom,color=".7",label="Remaining simulation overhead")
axes[1].set_xticks(x,["Healthy","b=0.10","b=0.25"])
axes[1].set(title="End-to-end cost per 562-step episode",ylabel="Wall-clock seconds")
axes[1].legend(fontsize=7,loc="upper left")
fig.suptitle("Small frozen feasibility pilot: 12 independent final episodes per setting\n"
             "Error bars are descriptive 95% paired Student-t intervals")
for ext in ("png","pdf"):
    fig.savefig(HERE/"figures"/("03_pilot_gain_and_cost."+ext),dpi=180)
plt.close(fig)
print("Pilot gain/cost figure rendered.")
