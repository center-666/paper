"""Rebuild the three article figures and their paired numerical evidence."""
from pathlib import Path
import csv
import json

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, Rectangle
import numpy as np
from scipy.stats import t as t_dist

HERE = Path(__file__).resolve().parent
STAGE = HERE.parents[1]
ROBUST = STAGE / "robustness_exploration"
ETA = 1 / 1600
BLUE, RED, DARK = "#124c70", "#923d30", "#1b1b1b"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":8,"axes.titlesize":9,
                     "axes.labelsize":8,"axes.linewidth":0.8,"legend.fontsize":7.4,
                     "pdf.fonttype":42,"axes.spines.top":False,"axes.spines.right":False})


def load(path):
    return json.loads(path.read_text(encoding="utf8"))


def write_csv(name, rows):
    with (HERE/name).open("w", newline="", encoding="utf8") as f:
        writer = csv.DictWriter(f, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def save(fig, name):
    for fmt in ("pdf", "png"):
        fig.savefig(HERE/f"{name}.{fmt}", dpi=410, facecolor="white", bbox_inches="tight",
                    pad_inches=.035, metadata={"Creator":"Stage 8 figure reconstruction"})
    plt.close(fig)


def architecture():
    fig, ax = plt.subplots(figsize=(7.25, 2.20))
    ax.set(xlim=(0,12), ylim=(0,3.60))
    ax.axis("off")
    width, height, y = 2.86, 1.02, 1.44
    boxes = [(0.14,"Sensor & trigger",r"Input  $y_t$"),
             (4.56,"Nominal monitor",r"Estimate  $m_t^M$"),
             (9.00,"Output correction",r"$m_t^R=m_t^M-a_t$")]
    for x, title, detail in boxes:
        ax.add_patch(Rectangle((x,y),width,height,facecolor="#f1f4f5",edgecolor=DARK,lw=1))
        ax.text(x+width/2,y+.69,title,ha="center",va="center",fontsize=9.4,fontweight="bold")
        ax.text(x+width/2,y+.32,detail,ha="center",va="center",fontsize=8.2)
    def arrow(a,b):
        ax.add_patch(FancyArrowPatch(a,b,arrowstyle="-|>",mutation_scale=10.2,
                                     color=DARK,lw=1.0,shrinkA=0,shrinkB=0))
    upper, lower, middle = 3.04,.52,y+height/2
    xs = [x+width/2 for x, *_ in boxes]
    ax.plot([xs[1], xs[1], xs[0]],[y+height,upper,upper],color=DARK,lw=1)
    arrow((xs[0],upper),(xs[0],y+height))
    ax.text((xs[0]+xs[1])/2,upper+.16,r"Shared prediction centre  $c_t$",ha="center")
    arrow((boxes[0][0]+width,middle),(boxes[1][0],middle))
    ax.text(3.77,middle+.15,r"$\gamma_t,\ z_t^{*}$",ha="center",fontsize=10)
    arrow((boxes[1][0]+width,middle),(boxes[2][0],middle))
    ax.text(8.19,middle+.15,r"$m_t^M$",ha="center",fontsize=10)
    ax.plot([xs[1],xs[1],xs[2]],[y,lower,lower],color=DARK,lw=1)
    arrow((xs[2],lower),(xs[2],y))
    ax.text((xs[1]+xs[2])/2,lower-.11,r"Recorded history  $(c,\gamma,z^{*})_{0:t}$",ha="center",va="top")
    ax.text(boxes[0][0],.04,r"$^{*}$Payload available only upon transmission.",fontsize=7.4)
    save(fig,"architecture")


def find_split(record):
    events = record["public"]
    bounds = record["bounds"]
    queries = {item["time"] for item in record["queries"]}
    for t in range(51,562):
        if (t not in queries and events[t][1] and bounds[t-1][0]>=ETA
                and bounds[t][0]==0 and bounds[t][1]>=ETA):
            end = t
            while end <= 561 and end not in queries and bounds[end][0]==0 and bounds[end][1]>=ETA:
                end += 1
            return t, end-1
    return None


def separation():
    fig, axes = plt.subplots(1,2,figsize=(7.25,2.78),layout="constrained")
    groups, samples, summary = ["strong_positive","strong_negative"], [], []
    for ax, group, sign in zip(axes, groups, ["+","−"]):
        paths=sorted((STAGE/"results/confirmation").glob(group+"-*.json"))
        records=list(map(load, paths))
        trace=records[0]
        t,end = find_split(trace)
        stamp=max(item["time"] for item in trace["queries"] if item["time"]<t)
        lo, hi = stamp-2, min(561,end+4)
        times=np.arange(lo,hi+1)
        a=np.array(trace["bounds"])[times,:]*1000
        ax.axvspan(t-.5,end+.5,facecolor="#e7ecef",edgecolor="none")
        ax.axhline(ETA*1000,color=DARK,ls=":",lw=1.1)
        ax.plot(times,a[:,1],color=BLUE,lw=1.45,marker="o",markersize=2.5,markevery=3)
        ax.plot(times,a[:,0],color=RED,lw=1.3,ls="--",marker="s",markersize=2.4,markevery=4)
        ax.axvline(t,ls="-.",lw=.9,color=DARK)
        ax.set_title(f"{sign}0.35 cm   ·   record 00",loc="left")
        ax.text(.98,.94,f"Send at {t}\n{t}–{end} ({end-t+1} steps)",ha="right",va="top",transform=ax.transAxes,
                bbox=dict(facecolor="white",edgecolor="none",alpha=.86,pad=1.5))
        ax.set(xlabel="Time step",xlim=(lo,hi))
        ax.set_ylim(-.92,max(a.max()*1.13,33))
        ax.grid(axis="y",color="#dddddd",linewidth=.55)
        if group==groups[0]:
            ax.set_ylabel(r"Published bound ($10^{-3}$ cm$^2$)")
        sends={t0 for t0,sent,*_ in trace["public"] if sent}
        for i in range(lo,hi+1):
            samples.append(dict(id=trace["id"],t=i,sent=int(i in sends),M2=trace["bounds"][i][0],
                                M3=trace["bounds"][i][1],eta=ETA))
        summary.append(dict(group=group,n=len(records),qualifying=sum(find_split(r) is not None for r in records),
                            record=trace["id"],last_query=stamp,first_split=t,last_contiguous=end,
                            duration=end-t+1,previous_M2=trace["bounds"][t-1][0],
                            split_M2=trace["bounds"][t][0],split_M3=trace["bounds"][t][1]))
    legend = [Line2D([],[],color=RED,ls="--",marker="s",ms=3,label="M2"),
              Line2D([],[],color=BLUE,marker="o",ms=3,label="M3"),
              Line2D([],[],color=DARK,ls=":",label=r"Useful threshold $\eta$")]
    fig.legend(handles=legend,loc="outside lower center",ncol=3,frameon=False)
    write_csv("separation_points.csv",samples)
    write_csv("separation_cases.csv",summary)
    save(fig,"separation")


def describe(group,baseline):
    ids=sorted(group)
    assert ids == sorted(baseline) == list(range(12))
    assert all(group[i]["seed"]==baseline[i]["seed"] and group[i]["seed_group_index"]==baseline[i]["seed_group_index"] for i in ids)
    m3=[group[i]["metrics"]["M3"] for i in ids]
    delta=np.array([m3[i]["useful_steps"]-baseline[i]["metrics"]["M3"]["useful_steps"] for i in ids],float)
    mean=float(np.mean(delta))
    half=t_dist.ppf(.975,11)*np.std(delta,ddof=1)/np.sqrt(12)
    return dict(n=len(ids),mean_useful=float(np.mean([m["useful_steps"] for m in m3])),
                paired_change=mean,paired_t95_low=mean-half,paired_t95_high=mean+half,
                risk_violations=sum(m["risk_violations"] for m in m3),
                certificate_checks=sum(m["certificate_checks"] for m in m3),
                trajectories_with_violation=sum(m["risk_violations"]>0 for m in m3),
                trajectories_with_action=sum(m["nonzero_steps"]>0 for m in m3))


def cohort(path,scenario,group):
    rows=[load(p) for p in sorted(path.glob(f"{scenario}_{group}_*.json"))]
    assert len(rows)==12 and all(not r.get("aliased_identical_bias_path") for r in rows)
    return {r["index"]:r for r in rows}


def sensitivity():
    fig,axes=plt.subplots(1,2,figsize=(7.25,2.82),layout="constrained")
    rows=[]
    quant=ROBUST/"data/quantization"
    bit_levels=["continuous","12bit","10bit","8bit"]
    for group,fmt,label,color in [("strong_positive","o-","+0.35 cm",BLUE),("strong_negative","s--","−0.35 cm",RED),("health",None,None,None)]:
        ref=cohort(quant,bit_levels[0],group)
        series=[]
        for scenario in bit_levels:
            row=dict(experiment="quantization",scenario=scenario,group=group,**describe(cohort(quant,scenario,group),ref))
            rows.append(row)
            series.append(row["mean_useful"])
        if fmt:
            axes[0].plot(range(len(series)),series,fmt,color=color,label=label,lw=1.4,ms=4)
    axes[0].set_xticks(range(4),["Continuous","12","10","8"])
    axes[0].set(xlabel="Payload precision (bits)",ylabel="M3 useful steps (mean)",ylim=(0,52))
    axes[0].set_title("(a) Payload quantization",loc="left")
    axes[0].legend(frameon=False,loc="lower left")
    drift=ROBUST/"data_v2/drift"
    decay=[0,5,10,20,35,50]
    ref=cohort(drift,"decay_00","strong_positive")
    values=[]
    for pct in decay:
        scenario=f"decay_{pct:02d}"
        row=dict(experiment="drift",scenario=scenario,group="strong_positive",**describe(cohort(drift,scenario,"strong_positive"),ref))
        rows.append(row)
        values.append(row["mean_useful"])
    axes[1].plot(decay,values,"o-",color=BLUE,lw=1.4,ms=4)
    axes[1].set_xticks([0,10,20,35,50])
    axes[1].set(xlabel="Bias decrease over 511 steps (%)",ylim=(0,52))
    axes[1].set_title("(b) Decay from +0.35 cm",loc="left")
    endrow=rows[-1]
    axes[1].annotate(f"{endrow['risk_violations']}/{endrow['certificate_checks']:,} proxy\nviolations",xy=(49,values[-1]),
                     xytext=(25,6),arrowprops=dict(arrowstyle="->",color=DARK,lw=.7),
                     ha="center",va="center",fontsize=7.4)
    for ax in axes:
        ax.grid(axis="y",color="#dddddd",lw=.55)
    write_csv("sensitivity_pairs.csv",rows)
    save(fig,"sensitivity")


if __name__ == "__main__":
    architecture()
    separation()
    sensitivity()
