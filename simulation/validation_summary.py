from __future__ import annotations
import csv
import json
from pathlib import Path
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from run_study import paired_interval, write_json, write_csv


def read_rows(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))


def holm(pvalues):
    order=np.argsort(pvalues);adjusted=np.empty(len(order));maximum=0.0
    for rank,idx in enumerate(order):
        maximum=max(maximum,(len(order)-rank)*pvalues[idx]);adjusted[idx]=min(1.0,maximum)
    return adjusted


def paired_p(margin):
    margin=np.asarray(margin)
    if np.std(margin,ddof=1)<1e-15:return 0.0 if margin.mean()<0 else 1.0
    return float(stats.ttest_1samp(margin,0,alternative="less").pvalue)


def summarize(out):
    out=Path(out);plan=json.loads((out/"plan.json").read_text(encoding="utf-8"))
    rows=read_rows(out/"per_seed_metrics.csv");wr=read_rows(out/"window_metrics.csv")
    seeds=sorted({int(r["seed"]) for r in rows});n=len(seeds)
    index={(r["setting"],r["method"],r["scenario"],int(r["seed"])):r for r in rows}
    wi={(r["setting"],r["method"],r["scenario"],int(r["seed"]),r["window"]):r for r in wr}
    def values(setting,method,scenario,metric):return np.asarray([float(index[setting,method,scenario,s][metric]) for s in seeds])
    def window_values(setting,method,window,metric):return np.asarray([float(wi[setting,method,"clean",s,window][metric]) for s in seeds])
    tests=[];secondary=[];performance=[]
    candidate=plan["primary_comparison"]["candidate"];baseline=plan["primary_comparison"]["baseline"]
    practical=plan["primary_comparison"]["practical_relative_gain"]
    normal={}
    for regime in plan["regimes"]:
        setting=regime["id"]
        normal_loss=values(setting,candidate,"clean","mse_all").mean()/values(setting,baseline,"clean","mse_all").mean()-1
        low_diff=abs(window_values(setting,candidate,"attack","low_weight_rate").mean()-window_values(setting,baseline,"attack","low_weight_rate").mean())
        weight_diff=abs(window_values(setting,candidate,"attack","mean_new_weight").mean()-window_values(setting,baseline,"attack","mean_new_weight").mean())
        normal[setting]={"relative_normal_mse_degradation":float(normal_loss),"attack_window_normal_low_weight_gap":float(low_diff),"attack_window_normal_mean_weight_gap":float(weight_diff),
            "passes":bool(normal_loss<=plan["normal_acceptance"]["maximum_relative_mse_degradation"] and low_diff<=plan["normal_acceptance"]["maximum_attack_window_low_weight_rate_difference"] and weight_diff<=plan["normal_acceptance"]["maximum_mean_weight_difference"])}
        scenarios=plan["common_scenarios"]+(plan["extra_repeated_scenarios"] if setting=="repeated_gaps" else [])
        for scenario in scenarios:
            for method in plan["methods"]:
                metrics={key:float(np.nanmean(values(setting,method,scenario,key))) if any(np.isfinite(values(setting,method,scenario,key))) else None
                         for key in ("mse_all","mse_attack_window","mse_recovery","edge_messages","received_low_weight_rate","mean_received_weight","clip_fraction")}
                excess=values(setting,method,scenario,"mse_attack_window")-values(setting,method,"clean","mse_attack_window")
                performance.append({"setting":setting,"method":method,"scenario":scenario,**metrics,"attack_excess_loss":float(excess.mean())})
            for method in dict.fromkeys(m for m in (candidate,"interval_tail") if m in plan["methods"]):
                a=values(setting,method,scenario,"mse_attack_window");b=values(setting,baseline,scenario,"mse_attack_window")
                d=a-b;mean,lo,hi=paired_interval(d)
                excess=d-(values(setting,method,"clean","mse_attack_window")-values(setting,baseline,"clean","mse_attack_window"))
                em,el,eh=paired_interval(excess)
                margin=a-(1-practical)*b
                se=np.std(margin,ddof=1)/np.sqrt(n)
                margin_low=margin.mean()-stats.t.ppf(.975,n-1)*se
                row={"setting":setting,"scenario":scenario,"candidate":method,"baseline":baseline,"seeds":n,
                    "mean_mse_difference":mean,"bootstrap95_low":lo,"bootstrap95_high":hi,
                    "relative_gain":float(-mean/b.mean()),"paired_excess_difference":em,"paired_excess95_low":el,"paired_excess95_high":eh,
                    "practical_margin_mean":float(margin.mean()),"practical_margin95_low":float(margin_low),"practical_gain_excluded_at95":bool(margin_low>0),
                    "p_one_sided_practical":paired_p(margin),"normal_acceptance":normal[setting]["passes"] if method==candidate else None}
                # Simultaneous conservative lower bound for the 9 primary margins.
                family_low=margin.mean()-stats.t.ppf(1-.05/(2*9),n-1)*se
                row["practical_margin_family95_low"]=float(family_low)
                row["practical_gain_excluded_family95"]=bool(family_low>0)
                if method==candidate and regime["primary"] and scenario in plan["primary_comparison"]["scenarios"]:tests.append(row)
                else:secondary.append(row)
    assert len(tests)==9
    adjusted=holm([r["p_one_sided_practical"] for r in tests])
    for row,p in zip(tests,adjusted):
        row["holm_p"]=float(p);row["passes"]=bool(p<plan["primary_comparison"]["family_alpha"] and row["normal_acceptance"] and row["relative_gain"]>=practical)
    counts={s:sum(r["passes"] for r in tests if r["scenario"]==s) for s in plan["primary_comparison"]["scenarios"]}
    gate=sum(v>=2 for v in counts.values())>=2
    write_csv(out/"primary_tests.csv",tests);write_csv(out/"secondary_comparisons.csv",secondary)
    write_json(out/"performance_summary.json",performance);write_csv(out/"performance_summary.csv",performance)
    write_json(out/"normal_acceptance.json",normal)
    write_json(out/"contribution_gate.json",{"passed":gate,"primary_cases":len(tests),"passed_cases":sum(r["passes"] for r in tests),
        "attack_types_passing_in_at_least_two_regimes":sum(v>=2 for v in counts.values()),"passed_cases_per_attack":counts,
        "cases_excluding_1pct_gain_at95":sum(r["practical_gain_excluded_at95"] for r in tests),
        "cases_excluding_1pct_gain_family95":sum(r["practical_gain_excluded_family95"] for r in tests),
        "scope":"Conditional on one full-local-observability model and fitted calibrations; no global impossibility conclusion"})
    plots=out/"figures";plots.mkdir(exist_ok=True)
    fig,ax=plt.subplots(figsize=(9,5))
    labels=[r["setting"]+" / "+r["scenario"] for r in tests]
    for j,row in enumerate(tests):
        b=values(row["setting"],baseline,row["scenario"],"mse_attack_window").mean()
        mean=100*row["mean_mse_difference"]/b;lo=100*row["bootstrap95_low"]/b;hi=100*row["bootstrap95_high"]/b
        ax.errorbar(mean,j,xerr=[[mean-lo],[hi-mean]],fmt="o",color="tab:blue",capsize=3)
    ax.axvline(0,color="gray",lw=1);ax.axvline(-100*practical,color="tab:red",ls="--",label="Predeclared -1% practical margin")
    ax.set_yticks(range(len(labels)),labels);ax.invert_yaxis();ax.set_xlabel("(Shared-scale tail MSE - scale-only MSE) / baseline (%)")
    ax.set_title("128 paired test seeds; bootstrap intervals are unadjusted displays")
    ax.legend(fontsize=8);ax.grid(axis="x",alpha=.2);fig.tight_layout()
    for suffix in ("png","pdf"):fig.savefig(plots/("primary_effects."+suffix),dpi=160,bbox_inches="tight")
    plt.close(fig)
    fig,axs=plt.subplots(2,2,figsize=(12,7))
    windows=list(plan["time_windows"])
    for ax,regime in zip(axs.ravel(),plan["regimes"]):
        setting=regime["id"]
        for method in (m for m in ("pooled",baseline,candidate) if m in plan["methods"]):
            yy=[100*np.nanmean(window_values(setting,method,w,"low_weight_rate")) for w in windows]
            ax.plot(range(len(windows)),yy,marker="o",label=method)
        ax.set_xticks(range(len(windows)),windows,rotation=20);ax.set_title(setting);ax.axhline(5,color="gray",ls="--",lw=1)
        ax.set_ylabel("Normal received packets with w<0.5 (%)");ax.grid(alpha=.2)
    axs[0,0].legend(fontsize=8);fig.tight_layout()
    for suffix in ("png","pdf"):fig.savefig(plots/("normal_calibration_by_time."+suffix),dpi=160,bbox_inches="tight")
    plt.close(fig)
    lines=["# 复查后验证结果","",f"预先登记计划：{plan['plan_id']}。所有设置已执行，未用本轮测试数据调参。独立测试种子 {n} 个，跨方法/场景配对。",
        "",f"**主要贡献门槛：{'通过' if gate else '未通过'}。9 项主要比较中 {sum(r['passes'] for r in tests)} 项满足预设实用改善、Holm 校正与正常代价要求。**",
        "","## 主要结果","","主对照为共享全部空间统计与时间尺度、只改变时间尾部分位数的版本对 interval_scale。权重控制参数仅在正常验证集上匹配。正的收益表示候选MSE更小；区间为未校正展示，正式门槛用Holm单侧实用差异检验。","",
        "| 日程 | 攻击 | 相对MSE改善 | MSE配对差95%区间 | Holm p | 正常代价合格 | 达到门槛 |","|---|---|---:|---|---:|---|---|"]
    for r in tests:lines.append(f"| {r['setting']} | {r['scenario']} | {100*r['relative_gain']:+.4f}% | [{r['bootstrap95_low']:+.7f}, {r['bootstrap95_high']:+.7f}] | {r['holm_p']:.4g} | {r['normal_acceptance']} | {r['passes']} |")
    lines += ["","## 正常代价审查","","| 日程 | 正常全窗MSE相对变化 | 正常攻击时窗低权重率差 | 正常攻击时窗平均权重差 | 合格 |","|---|---:|---:|---:|---|"]
    for setting,r in normal.items():lines.append(f"| {setting} | {100*r['relative_normal_mse_degradation']:+.4f}% | {100*r['attack_window_normal_low_weight_gap']:.4f}个百分点 | {r['attack_window_normal_mean_weight_gap']:.5f} | {r['passes']} |")
    lines += ["","## 低幅与匹配Replay边界（探索性）","","| 日程 | 场景 | 共享尺度尾部相对MSE改善 | MSE配对差95%区间 |","|---|---|---:|---|"]
    for r in secondary:
        if r["candidate"]==candidate and (r["scenario"]=="low_step" or r["scenario"]=="replay_matched"):
            lines.append(f"| {r['setting']} | {r['scenario']} | {100*r['relative_gain']:+.4f}% | [{r['bootstrap95_low']:+.7f}, {r['bootstrap95_high']:+.7f}] |")
    lines += ["","## 范围与复核","",
        "- 仅改变发送压力和预先指定攻击工况，模型仍为各节点满秩本地量测的对称二维系统；不能外推所有拓扑或局部不可观测情况。",
        f"- 本轮 {len(plan['methods'])} 个预设方法/消融、三种正常参考日程与一种重复不规则日程；所有通信方法共享日程。具体方法及前序关系见 plan.json。",
        "- 只匹配低权重比例不能完全匹配信息损失，另保存分时间窗新包平均权重及缓存权重损失。有限正常重标定也不保证闭环固定点。",
        "- Replay匹配的是实际发送历史包的时刻差，不假定数据内容仍正常或永远不可检出；起始切换仍可能异常。",
        "- 主要置信判断以种子为单位，条件于已拟合标定集；未包含重新采集标定数据的方差。正常代价为点估计筛查，不是统计非劣证明。排除实用收益另保存9项Bonferroni同时下界，不能把未校正单项95%区间称为家族保证。",
        "- 不把原32种子与本轮128种子合并形成选择后的显著性结论。原结果只用于提出此次事先固定的验证问题。",
        "","[主要效果图](figures/primary_effects.png) · [分时间窗正常校准](figures/normal_calibration_by_time.png)",
        "","原始资料：plan.json、preregistration.json、sources/、per_seed_metrics.csv、window_metrics.csv、normal_group_metrics.csv、primary_tests.csv、secondary_comparisons.csv、run_audit.json、各设置完整NPZ轨迹和控制参数。"]
    (out/"REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"primary_gate":gate,"passed_cases":sum(r["passes"] for r in tests),"excluded_practical_gain_cases":sum(r["practical_gain_excluded_at95"] for r in tests)}),flush=True)


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("folder");args=p.parse_args();summarize(args.folder)
