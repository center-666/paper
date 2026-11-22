"""Standalone geometry/dynamics illustrations, not statistical performance."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from projection import weighted_projection

HERE=Path(__file__).resolve().parent
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"pdf.fonttype":42,
                     "axes.spines.top":False,"axes.spines.right":False})
folder=HERE/"figures";folder.mkdir(exist_ok=True)
fig,axes=plt.subplots(1,2,figsize=(10,4.2),constrained_layout=True)
sets=[[(.2,.1),(.2,-.1)],[(.2,.1),(-.2,-.1)]]
titles=["A common safe direction exists","Nonzero candidates, zero in convex hull"]
for ax,pts,title in zip(axes,sets,titles):
    result=weighted_projection([[str(x) for x in p] for p in pts],[[1,0],[0,1]])
    p=np.array([float(x) for x in result["point"]]);v=np.array(pts)
    ax.plot(v[:,0],v[:,1],color="#2679a9",linewidth=5,alpha=.6)
    ax.scatter(v[:,0],v[:,1],color="#2679a9",label="Plausible contamination endpoints")
    ax.scatter([0],[0],color="black",marker="+",s=70,label="Origin")
    ax.scatter([p[0]],[p[1]],color="#d75136",s=70,label="Certified minimax correction")
    ax.annotate("",xy=p,xytext=(0,0),arrowprops={"color":"#d75136","arrowstyle":"->","lw":2})
    ax.axhline(0,color=".8",linewidth=.5);ax.axvline(0,color=".8",linewidth=.5)
    ax.set(title=title,xlabel="State 1 contamination",ylabel="State 2 contamination",
           xlim=(-.25,.3),ylim=(-.17,.17),aspect="equal")
    ax.text(.02,.98,f"Guaranteed improvement: {float(result['guaranteed_gain']):.3f}",
            transform=ax.transAxes,va="top",fontsize=9)
axes[0].legend(fontsize=7,loc="lower left")
fig.suptitle("Weighted projection, W=I: exact geometric examples")
for ext in ("pdf","png"):fig.savefig(folder/("01_projection_geometry."+ext),dpi=180)
plt.close(fig)

model=json.loads((HERE/"model.json").read_text(encoding="utf8"))
A=np.array(model["A"],float);C=np.array(model["C"],float);P=np.array(model["P0_prior"],float)
Q=np.array(model["Q"],float);R=float(model["R"]);H=np.zeros(2);values=[]
for t in range(80):
    K=(P@C.T/(C@P@C.T+R)).ravel();T=np.eye(2)-np.outer(K,C)
    H=T@A@H+K;values.append(H.copy());P=A@(T@P)@A.T+Q
values=np.array(values)
fig,ax=plt.subplots(figsize=(7,4),constrained_layout=True)
ax.plot(values[:,0],label="State 1 unit-amplitude response")
ax.plot(values[:,1],label="State 2 unit-amplitude response")
ax.axhline(0,color="black",linewidth=.7)
ax.set(title="Deterministic all-send path: vector pollution can change sign",
       xlabel="Observation time",ylabel="H(k=0,t), per unit positive input")
ax.legend()
for ext in ("pdf","png"):fig.savefig(folder/("02_signed_pollution_response."+ext),dpi=180)
plt.close(fig)
print("Two deterministic figures rendered.")
