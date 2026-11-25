"""Rebuild all supplementary statistics from independently identified rows."""
import csv
import hashlib
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
SUP = Path(__file__).resolve().parents[1]
TASK = SUP.parent
sys.path.insert(0, str(TASK/"code"))
from experiment import read, save, digest
import numpy as np
from scipy.stats import t, beta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = SUP/"reports"
GROUPS = dict(strong_positive="强正", strong_negative="强负",
              transition_positive="过渡正", transition_negative="过渡负",
              weak_positive="弱正", weak_negative="弱负", health="健康")
EN = ["Strong +","Strong −","Transition +","Transition −","Weak +","Weak −","Healthy"]


def csv_table(name, rows):
    with (OUT/(name+".csv")).open("w", encoding="utf8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def interval(x):
    x = np.array(x, float)
    mean = float(x.mean())
    half = float(t.ppf(.975,len(x)-1)*x.std(ddof=1)/math.sqrt(len(x)))
    return mean, mean-half, mean+half


def export(fig, name):
    p = OUT/"figures"
    p.mkdir(exist_ok=True)
    fig.savefig(p/(name+".pdf"), metadata={"CreationDate":None,"ModDate":None})
    fig.savefig(p/(name+".png"), dpi=320)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    reg = read(SUP/"registration.json")
    base = read(TASK/"registration.json")
    old = sorted((TASK/"results/confirmation").glob("*.json"))
    new = sorted((SUP/"results/transition").glob("*.json"))
    ladder = sorted((SUP/"results/ladder").glob("*.json"))
    old_ids = {f"{g}-{i:02d}" for g,n in base["groups"].items() for i in range(n)}
    new_ids = {f"{g}-{i:02d}" for g,v in reg["transition_groups"].items() for i in range(v["count"])}
    assert {p.stem for p in old} == old_ids
    assert {p.stem for p in new} == new_ids
    assert {p.stem for p in ladder} == old_ids|new_ids
    rows = {r["id"]:r for r in map(read,old+new)}
    gates = {r["id"]:r for r in map(read,ladder)}
    identity = digest(SUP/"registration.json")
    assert all(r["supplement_registration"]==identity for r in gates.values())
    assert all(r["supplement_registration"]==identity for r in map(read,new))
    assert all(r["original_M1_identical"] for r in gates.values())
    summary, individual, contrasts, rates = [],[],[],[]
    for g in GROUPS:
        selected = [r for r in rows.values() if r["group"]==g]
        n = len(selected)
        sent = sum(frame[1] for r in selected for frame in r["public"])
        rates.append(dict(group=g,Z=2,n=n,sent=sent,steps=608*n,rate=sent/(608*n),
                          cohort="new" if g.startswith("transition") else "original"))
        for m in ("h0","q95","M1","M2","M3"):
            obs = []
            for r in selected:
                v = gates[r["id"]]["metrics"][m] if m in ("h0","q95","M1") else r["metrics"][m]
                row = dict(id=r["id"],group=g,b=r["b"],method=m,
                    evidence="supplement" if r["id"] in new_ids else "original-replay",
                    loss=v["loss"],gain=r["metrics"]["M0"]["loss"]-v["loss"],
                    conditional=v["conditional"],opportunity=r["metrics"]["Oracle"]["conditional"],
                    active_or_useful=v.get("active_steps",v.get("useful")),
                    first=v["first"],endpoint=v["end"],nonzero_608=v["nonzero"],
                    lower_bound=v.get("bound") if m in ("M2","M3") else None)
                obs.append(row)
                individual.append(row)
            mean,lo,hi = interval([r["gain"] for r in obs])
            numerator = sum(r["conditional"] for r in obs)
            denominator = sum(r["opportunity"] for r in obs)
            delays = [r["first"]-50 for r in obs if r["first"] is not None]
            summary.append(dict(group=g,method=m,n=n,gain=mean,low=lo,high=hi,
                conditional=numerator/n,conditional_sum=numerator,opportunity_sum=denominator,
                share=numerator/denominator if denominator else None,
                active_or_useful=float(np.mean([r["active_or_useful"] for r in obs])),
                started=len(delays),endpoint=sum(r["endpoint"] for r in obs),
                success_delay_median=float(np.median(delays)) if delays else None,
                any_action=sum(r["nonzero_608"]>0 for r in obs),
                negative_gain=sum(r["gain"]<0 for r in obs),
                negative_conditional=sum(r["conditional"]<0 for r in obs)))
        for m in ("M2","M1"):
            mean,lo,hi = interval([r["metrics"][m]["loss"]-r["metrics"]["M3"]["loss"] for r in selected])
            contrasts.append(dict(group=g,comparison="M3_vs_"+m,n=n,mean=mean,low=lo,high=hi))
    diag = read(SUP/"results/trigger_diagnostic.json")
    for z in reg["Z_health_diagnostics"]:
        selected = [r for r in diag if r["Z"]==z]
        assert len(selected)==reg["diagnostic_count_per_Z"]
        sent = sum(r["sent"] for r in selected)
        rates.append(dict(group="health-diagnostic",Z=z,n=len(selected),sent=sent,
                          steps=608*len(selected),rate=sent/(608*len(selected)),cohort="paired-diagnostic"))
    for name,data in (("paired_trajectories",individual),("method_summary",summary),
                      ("paired_comparisons",contrasts),("transmission_rate",rates)):
        csv_table(name,data)
    audit = {k:sum(rows[p.stem][k] for p in new) for k in ("violations","checked","miss","cap_bad")}
    audit.update(new_n=24,replayed_n=116,original_replayed_n=92,
        max_direct_error=max(rows[p.stem]["max_error"] for p in new),
        new_cpu_hours=sum(rows[p.stem]["cpu"] for p in new)/3600,
        replay_cpu_hours=sum(r["cpu"] for r in gates.values())/3600,
        original_M1_hashes_verified=116,registration=identity)
    save(OUT/"audit.json",audit)
    text = ["# 双容液位补充实验","",
        "新增 ±0.25 cm 各 12 条、起点 50 的过渡偏置轨迹。原 92 条与新 24 条分别登记。"
        "共 116 条公共前缀的门限回放使用同一组已冻结健康开发门限，全部 M1 动作哈希与原记录一致。",
        "",f"h0/q95/M1 门限分别为 0、{float(reg['thresholds']['q95']):.6f}、"
        f"{float(reg['thresholds']['M1']):.6f}。q95 采用原 200 条开发路径第 190 秩。"
        "确认参数仍为 Z=2、先验幅值 ±0.35 cm、四个固定查询时刻。",
        "","| 工况 | 方法 | n | 平均降损 | 条件改善均值 | 启动/全部 | 平均有效拍 | 期末 | 负条件改善 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in summary:
        text.append(f"| {GROUPS[r['group']]} | {r['method']} | {r['n']} | {r['gain']:.4f} | "
            f"{r['conditional']:.4f} | {r['started']}/{r['n']} | {r['active_or_useful']:.1f} | "
            f"{r['endpoint']}/{r['n']} | {r['negative_conditional']}/{r['n']} |")
    text += ["","h0/q95/M1 计非零动作，M2/M3 计实际发布下界至少 0.000625 的动作。"
        "实际负降损与离线负条件改善分别计数，完整字段见 CSV。首动中位延迟只针对窗内成功轨迹。",
        "","| 过渡组 | M3-M2 配对差 [描述性95%区间] | M3-M1 配对差 [描述性95%区间] |",
        "|---|---:|---:|"]
    for g in reg["transition_groups"]:
        entries = [next(r for r in contrasts if r["group"]==g and r["comparison"]=="M3_vs_"+m) for m in ("M2","M1")]
        text.append("| "+GROUPS[g]+" | "+" | ".join(f"{r['mean']:.4f} [{r['low']:.4f}, {r['high']:.4f}]" for r in entries)+" |")
    text += ["","| 健康门限 | 全608拍任意动作 | 平均条件改善 |","|---|---:|---:|"]
    for r in summary:
        if r["group"]=="health":
            text.append(f"| {r['method']} | {r['any_action']}/36 | {r['conditional']:.4f} |")
    text += ["",f"0/36 对应的双侧 95% 精确上限为 {100*beta.ppf(.975,1,36):.2f}%。",
        "","| 发送率口径 | Z | n | 总发送/总拍数 | 发送率 |","|---|---:|---:|---:|---:|"]
    for r in rates:
        if r["group"] in ("health","health-diagnostic"):
            text.append(f"| {r['group']} | {r['Z']} | {r['n']} | {r['sent']}/{r['steps']} | {100*r['rate']:.2f}% |")
    text += ["","Z=20 的独立健康诊断未达到建议的 35%–60% 范围。诊断只改变触发参数，"
        "其结果用于说明原协议的稀疏通信边界。确认结果按原 Z=2 归档。",
        "",f"新增覆盖遗漏 {audit['miss']}/14592 拍；{audit['checked']} 个真参数保留的非零有证动作中，"
        f"风险下界违反 {audit['violations']} 次（容差 1e-10），上限违反 {audit['cap_bad']} 次。"
        f"最大直接滤波差 {audit['max_direct_error']:.3g}。"
        f"新增试验与门限回放分别耗费 {audit['new_cpu_hours']:.3f}、{audit['replay_cpu_hours']:.3f} 核时。",
        "","![强弱及过渡档收益](figures/gain.png)","",
        "![门限与条件改善](figures/gates.png)","",
        "[逐轨迹数据](paired_trajectories.csv) · [完整指标](method_summary.csv) · [发送率](transmission_rate.csv)"]
    (OUT/"acceptance.md").write_text("\n".join(text)+"\n",encoding="utf8",newline="\n")
    tables = OUT/"tables"
    tables.mkdir(exist_ok=True)
    tex = [r"\begin{tabular}{llrrrrr}",r"\toprule",
           r"工况 & 方法 & 实际降损 & 条件改善 & 有效拍 & 期末 & 负条件改善 \\",r"\midrule"]
    for r in summary:
        tex.append(f"{GROUPS[r['group']]} & {r['method']} & {r['gain']:.4f} & {r['conditional']:.4f}"
            f" & {r['active_or_useful']:.1f} & {r['endpoint']}/{r['n']} & {r['negative_conditional']}/{r['n']}"+r" \\")
    (tables/"supplement.tex").write_text("\n".join(tex+[r"\bottomrule",r"\end{tabular}"])+"\n",encoding="utf8",newline="\n")
    plt.rcParams.update({"font.size":9,"pdf.fonttype":42})
    fig,ax = plt.subplots(figsize=(8,3.7),layout="constrained")
    for i,m in enumerate(("M1","M2","M3")):
        values = [next(r for r in summary if r["group"]==g and r["method"]==m) for g in GROUPS]
        ax.bar(np.arange(7)+(i-1)*.23,[r["gain"] for r in values],.22,label=m,
               yerr=[[max(0,r["gain"]-r["low"]) for r in values],
                     [max(0,r["high"]-r["gain"]) for r in values]],capsize=2)
    ax.set_xticks(np.arange(7),EN)
    ax.set_ylabel("512-step realized loss reduction (cm²)")
    ax.axhline(0,lw=.7,color=".3")
    ax.legend(ncol=3)
    export(fig,"gain")
    fig,axes = plt.subplots(1,2,figsize=(8,3.4),layout="constrained")
    for ax,g in zip(axes,("transition_positive","transition_negative")):
        for m in ("h0","q95","M1"):
            h = next(r for r in summary if r["group"]=="health" and r["method"]==m)
            r = next(r for r in summary if r["group"]==g and r["method"]==m)
            ax.scatter(100*h["any_action"]/36,r["conditional"],label=m)
        ax.axhline(0,lw=.7,color=".3")
        ax.set_title(g.replace("_"," "))
        ax.set(xlabel="Healthy any-action episodes (%)",ylabel="Mean conditional improvement (cm²)")
        ax.legend()
    export(fig,"gates")
    files = {p.relative_to(SUP).as_posix():digest(p) for p in sorted(SUP.rglob("*"))
             if p.is_file() and p.suffix in (".py",".csv",".md",".json",".tex") and p.name!="manifest.json"}
    files.update({p.relative_to(SUP).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in OUT.rglob("*") if p.suffix in (".pdf",".png")})
    save(SUP/"manifest.json",dict(text="UTF-8 LF SHA-256",binary="raw SHA-256",files=files))
    print("Supplement complete",len(new),"new;",len(ladder),"replayed;",audit)


if __name__=="__main__":
    main()
