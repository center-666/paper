"""Rebuild the Chinese report, paired data, booktabs tables and figures."""
import csv
import math
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.stats import beta, t as student
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from experiment import ROOT,read,save,digest

OUT=ROOT/"reports"
NAMES=dict(strong_positive="强正",strong_negative="强负",weak_positive="弱正",
           weak_negative="弱负",health="健康")
EN=["Strong +","Strong −","Weak +","Weak −","Healthy"]
METHODS=("M1","M2","M3")

def table(path,rows):
    with path.open("w",encoding="utf8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

def report_text(path,lines):
    path.write_text("\n".join(lines)+"\n",encoding="utf8",newline="\n")

def compare(x):
    mean=np.mean(x)
    half=student.ppf(.975,len(x)-1)*np.std(x,ddof=1)/math.sqrt(len(x))
    return [float(v) for v in (mean,mean-half,mean+half)]

def figures(episodes,rows):
    path=OUT/"figures"
    path.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size":9,"pdf.fonttype":42})
    fig,axes=plt.subplots(1,2,figsize=(8,3.4),layout="constrained")
    for ax,g in zip(axes,list(NAMES)[:2]):
        cohort=[v for v in episodes if v["group"]==g]
        chosen=next((v for v in cohort if v["metrics"]["M3"]["first"] is not None),cohort[0])
        first=next((q["time"] for q in chosen["queries"] if any(l["certified"] for l in q["levels"])),None)
        if first is not None:
            stop=next((q["time"] for q in chosen["queries"] if q["time"]>first),562)
            bounds=np.array(chosen["bounds"])[first:stop]
            for j,m in enumerate(("M2","M3")):
                ax.plot(np.arange(len(bounds)),bounds[:,j],label=m)
            ax.axhline(.000625,color=".4",ls=":",label="Useful threshold")
            ax.set_title(f"{chosen['id'].replace('_',' ')}  (t = {first})")
        else:
            ax.set_title("No positive certificate")
        ax.set(xlabel="Steps since first certificate",ylabel="Audited improvement bound (cm²)")
        ax.legend()
    export(fig,path/"persistence")
    fig,axes=plt.subplots(2,1,figsize=(7,5.3),layout="constrained",sharex=True)
    x=np.arange(5)
    for j,m in enumerate(METHODS):
        entries=[r for r in rows if r["method"]==m]
        xpos=x+(j-1)*.24
        axes[0].bar(xpos,[r["gain"] for r in entries],.23,label=m)
        axes[1].bar(xpos,[100*r["negative"]/r["n"] for r in entries],.23,label=m)
    axes[0].axhline(0,color=".3",lw=.7)
    axes[0].set_ylabel("Mean cumulative gain (cm²)")
    axes[1].set_ylabel("Episodes with loss increase (%)")
    axes[1].set_xticks(x,EN)
    axes[0].legend(ncol=3)
    export(fig,path/"gain_and_harm")

def export(fig,path):
    fig.savefig(path.with_suffix(".pdf"),metadata={"CreationDate":None,"ModDate":None})
    fig.savefig(path.with_suffix(".png"),dpi=320)
    plt.close(fig)

def main():
    reg=read(ROOT/"registration.json")
    paths=sorted((ROOT/"results/confirmation").glob("*.json"))
    ids={f"{g}-{i:02d}" for g,n in reg["groups"].items() for i in range(n)}
    assert {p.stem for p in paths}==ids and len(ids)==92
    episodes=[read(p) for p in paths]
    expected_hash=digest(ROOT/"registration.json")
    assert all(r["id"]==p.stem and r["registration"]==expected_hash and
               [q["time"] for q in r["queries"]]==reg["query_times"] and len(r["public"])==608
               for p,r in zip(paths,episodes))
    OUT.mkdir(exist_ok=True)
    summary=[]; individual=[]; paired={}
    for g in NAMES:
        cohort=[r for r in episodes if r["group"]==g]
        n=len(cohort)
        assert len({r["index"] for r in cohort})==n
        for r in cohort:
            baseline=r["metrics"]["M0"]["loss"]
            denom=r["metrics"]["Oracle"]["conditional"]
            for m,v in r["metrics"].items():
                individual.append(dict(id=r["id"],group=g,b=r["b"],method=m,M0_loss=baseline,
                    loss=v["loss"],gain=baseline-v["loss"],conditional=v["conditional"],
                    oracle_opportunity=denom,lower_bound=v["bound"] if m in ("M2","M3") else None,
                    active_or_useful_steps=v["useful"],endpoint=v["end"],first=v["first"],
                    nonzero_608=v["nonzero"],runtime_s=r["cpu"],risk_violations_joint=r["violations"]))
        paired[g]={m:compare([r["metrics"][m]["loss"]-r["metrics"]["M3"]["loss"] for r in cohort])
                   for m in ("M1","M2")}
        for m in METHODS:
            obs=[r for r in individual if r["group"]==g and r["method"]==m]
            num=sum(r["conditional"] for r in obs)
            den=sum(r["oracle_opportunity"] for r in obs)
            delays=[r["first"]-reg["onset"] for r in obs if r["first"] is not None]
            gains=np.array([r["gain"] for r in obs])
            summary.append(dict(group=g,method=m,n=n,gain=float(gains.mean()),conditional_sum=num,
                  opportunity_sum=den,share=num/den if den else None,
                  useful=np.mean([r["active_or_useful_steps"] for r in obs]),endpoint=sum(r["endpoint"] for r in obs),
                  started=len(delays),delay=float(np.median(delays)) if delays else None,
                  negative=int((gains<0).sum()),negative_cond=sum(r["conditional"]<0 for r in obs),
                  any_action=sum(r["nonzero_608"]>0 for r in obs)))
    table(OUT/"paired_trajectories.csv",individual)
    table(OUT/"summary.csv",summary)
    figures(episodes,summary)
    timing=read(ROOT/"results/timing.json")
    assert len(timing)==8 and all(r["identical"] for r in timing)
    stats={}
    for m in ("M1","M3"):
        runs=[r for r in timing if r["method"]==m]
        q=np.array([v for r in runs for v in r["query_seconds"]])
        stats[m]=[float(np.mean([r["seconds"] for r in runs])),*map(float,np.quantile(q,[.5,.95]))]
    target=OUT/"tables"
    target.mkdir(exist_ok=True)
    header=["工况","算法","平均降损","份额","拍数","期末","首动延迟","负降损","负条件改善"]
    tex=[r"\begin{tabular}{llrrrrrrr}",r"\toprule"," & ".join(header)+r" \\",r"\midrule"]
    md=["# 双容液位单节点确认实验","",
        f"完成 {len(episodes)} 条、每条 608 拍，窗口为 50–561 拍。强档 ±{reg['strong']} cm，弱档 ±{reg['weak']} cm。"
        f"M1 门限 {float(reg['threshold']):.6f}，取 {reg['calibration_n']} 条独立健康开发轨迹的第 199 顺序统计量。"
        "两种认证法共享证据。下表降损为每条轨迹相对 M0 的 512 拍累计平方误差减少量（cm²）。",
        "","| "+" | ".join(header)+" |","|"+"---|"*len(header)]
    for r in summary:
        if r["group"]=="health" or r["delay"] is None:
            delay="—"
        else:
            delay=f"{r['delay']:g}"
        entries=[NAMES[r["group"]],r["method"],f"{r['gain']:.4f}",
                 f"{100*r['share']:.1f}%" if r["share"] is not None else "—",
                 f"{r['useful']:.1f}",f"{r['endpoint']}/{r['n']}",
                 delay,f"{r['negative']}/{r['n']}",f"{r['negative_cond']}/{r['n']}"]
        md.append("| "+" | ".join(entries)+" |")
        tex.append(" & ".join(x.replace("%",r"\%") for x in entries)+r" \\")
    report_text(target/"performance.tex",tex+[r"\bottomrule",r"\end{tabular}"])
    md+=["","份额为组内离线条件改善之和除以 Oracle 机会量之和。健康组分母为零。M1 计非零出手，M2/M3 计实际发布下界至少 0.000625 cm² 的拍数。首动延迟仅在窗口内成功者中取中位数，期末比例和平均时长包含全部轨迹。",
        "","| 工况 | M3 相对 M2 平均增量 [配对 95% t 区间] | M3 相对 M1 平均增量 [配对 95% t 区间] |",
        "|---|---:|---:|"]
    for g in NAMES:
        fmt=lambda v:f"{v[0]:.4f} [{v[1]:.4f}, {v[2]:.4f}]"
        md.append(f"| {NAMES[g]} | {fmt(paired[g]['M2'])} | {fmt(paired[g]['M1'])} |")
    md+=["","| 单独在线回放 | 秒/608 拍 | 查询 P50 秒 | 查询 P95 秒 |","|---|---:|---:|---:|"]
    tex=[r"\begin{tabular}{lrrr}",r"\toprule",r"算法 & 秒/轨迹 & 查询 P50（秒） & 查询 P95（秒） \\",r"\midrule"]
    for m,val in stats.items():
        md.append(f"| {m} | "+" | ".join(f"{x:.4f}" for x in val)+" |")
        tex.append(m+" & "+" & ".join(f"{x:.4f}" for x in val)+r" \\")
    report_text(target/"timing.tex",tex+[r"\bottomrule",r"\end{tabular}"])
    totals={k:sum(r[k] for r in episodes) for k in ("violations","checked","miss","cap_bad")}
    maxerr=max(r["max_error"] for r in episodes)
    cal=read(ROOT/"results/calibration.json")
    ladder=read(ROOT/"results/development_ladder.json")
    weak=read(ROOT/"results/development_weak.json")
    hours=sum(r["cpu"] for r in episodes)/3600
    devcpu=(sum(r["cpu"] for step in ladder for r in step["rows"])+sum(r["cpu"] for r in weak+cal["rows"]))/3600
    hr=[r for r in summary if r["group"]=="health"]
    md+=["","四条强档记录各符号两条，四个工作进程，各方法独立回放相同前缀；所有逐拍发布位移的哈希均与配对运行一致。每个方法 4 条轨迹、16 个查询。耗时受计算机与进程调度影响。",
        "",f"覆盖未命中 {totals['miss']}/{608*len(episodes)} 拍。真参数保留且非零发布的 {totals['checked']} 个 M2/M3 动作中，条件改善低于认证下界超过 1e-10 的次数为 {totals['violations']}。上限违反 {totals['cap_bad']} 次。直接滤波与 bH 最大绝对差 {maxerr:.3g}。该统计只针对本批轨迹。",
        "",f"健康组 608 拍内任意非零出手为 M1/M2/M3 各 "+"/".join(str(r["any_action"]) for r in hr)+
        f" 条（各 36 条）。零次事件对应的双侧 95% Clopper–Pearson 上限为 {100*beta.ppf(.975,1,36):.2f}%。",
        "",f"开发强度阶梯的有用启动数（正/负各 4 条）为 "+
        "、".join(f"{s['cap']} cm {s['counts'][0]}/{s['counts'][1]}" for s in ladder)+
        f"。测量噪声标准差为 {math.sqrt(.02):.3f} cm，弱/强的标准化幅值为 {reg['weak']/math.sqrt(.02):.2f}/{float(reg['strong'])/math.sqrt(.02):.2f}。原 V2 对应约 0.22/0.56；双容强档为满足开发启动标准采用了更高的相对幅值。该差异限定跨对象比较。",
        "",f"有效开发记录用时 {devcpu:.3f} 核时，确认 {hours:.3f} 核时，独立计时回放 {sum(r['cpu'] for r in timing)/3600:.3f} 核时。早期排错运行另计，未计入实验样本。",
        "","![有用下界的共同首证后衰减](figures/persistence.png)","","![累计降损与负降损轨迹比例](figures/gain_and_harm.png)",
        "","[预注册](../registration.json) · [逐轨迹配对数据](paired_trajectories.csv) · [三线表](tables/performance.tex) · [计时表](tables/timing.tex)"]
    report_text(OUT/"acceptance.md",md)
    save(OUT/"audit.json",dict(**totals,max_error=maxerr,confirmation_hours=hours,
           valid_dev_hours=devcpu,replay_hours=sum(r["cpu"] for r in timing)/3600,timing=stats))
    print("validated",len(episodes),"episodes,",len(individual),"method rows;",totals)
if __name__=="__main__":
    main()
