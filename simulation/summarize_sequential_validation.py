"""Frozen-output analysis for phase-separated sequential baseline comparisons."""
from __future__ import annotations
import csv,json
from pathlib import Path
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from run_study import paired_interval,write_json,write_csv
from validation_summary import holm
from sequential_cache import DETECTORS,PHASES

LABELS={"local":"Local", "age_only":"Age-only", "instant":"Instant cache gate", "mean":"Covariance-corrected mean",
        "white_window":"Whitened window", "white_cusum":"Whitened energy CUSUM", "white_signed_cusum":"Whitened two-sided CUSUM"}


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))


def p_less(values):
    values=np.asarray(values,float)
    if np.std(values,ddof=1)<1e-15:return float(0 if values.mean()<0 else 1)
    return float(stats.ttest_1samp(values,0,alternative="less").pvalue)


def summarize(folder):
    folder=Path(folder);plan=json.loads((folder/"plan.json").read_text(encoding="utf-8"))
    records=read_csv(folder/"per_seed_metrics.csv");phase_rows=read_csv(folder/"per_seed_phase_rates.csv")
    index={(r["schedule"],r["edge_label"],r["method"],r["scenario"],int(r["seed"])):r for r in records}
    seeds=sorted({int(r["seed"]) for r in records});N=len(seeds)
    assert len(index)==len(records)
    def vals(schedule,edge,method,scenario,key):return np.array([float(index[schedule,edge,method,scenario,s][key]) for s in seeds])
    rate_data={}
    for r in phase_rows:
        if r["scenario"]!="clean":continue
        k=("test",r["schedule"],r["edge_label"],r["method"],r["phase"])
        rate_data.setdefault(k,[]).append((int(r["seed"]),int(r["alarm_episodes"]),int(r["complete_episodes"])))
    for schedule in plan["schedules"]:
        for r in read_csv(folder/schedule/"normal_audit_rates.csv"):
            for edge in plan["attack_edges"]:
                k=("normal_audit",schedule,edge,r["method"],r["phase"])
                rate_data.setdefault(k,[]).append((int(r["seed"]),int(r["alarm_episodes"]),int(r["complete_episodes"])))
    rates={};rate_summary=[]
    rng=np.random.default_rng(283119)
    for key,z in rate_data.items():
        z=sorted(z);alarms=np.array([v[1] for v in z]);totals=np.array([v[2] for v in z]);rate=float(alarms.sum()/totals.sum())
        indices=rng.integers(0,len(z),size=(2000,len(z)))
        boot=alarms[indices].sum(axis=1)/totals[indices].sum(axis=1)
        rates[key]=rate
        rate_summary.append(dict(zip(("split","schedule","edge_label","method","phase"),key))|
            {"episode_count":int(totals.sum()),"alarm_count":int(alarms.sum()),"rate":rate,
             "cluster_bootstrap95_low":float(np.quantile(boot,.025)),"cluster_bootstrap95_high":float(np.quantile(boot,.975))})
    write_csv(folder/"phase_rate_summary.csv",rate_summary)
    acceptance=plan["normal_acceptance"]
    primary=[];all_comparisons=[];summary=[]
    baselines=("instant","white_window","white_cusum","white_signed_cusum","age_only","local")
    for schedule in plan["schedules"]:
        for edge in plan["attack_edges"]:
            for method in plan["methods"]:
                for scenario in plan["scenarios"]:
                    d={"schedule":schedule,"edge_label":edge,"method":method,"scenario":scenario}
                    for key in ("mse_all","mse_attack_window","receiver_attack_mse","receiver_recovery_mse","edge_messages","cache_weight_loss"):
                        d[key]=float(vals(schedule,edge,method,scenario,key).mean())
                    d["receiver_attack_excess"]=float((vals(schedule,edge,method,scenario,"receiver_attack_mse")-vals(schedule,edge,method,"clean","receiver_attack_mse")).mean())
                    summary.append(d)
            for scenario in plan["scenarios"]:
                if scenario=="clean":continue
                for baseline in baselines:
                    a=vals(schedule,edge,"mean",scenario,"receiver_attack_mse");b=vals(schedule,edge,baseline,scenario,"receiver_attack_mse")
                    d=a-b;mu,lo,hi=paired_interval(d)
                    ac=vals(schedule,edge,"mean","clean","receiver_attack_mse");bc=vals(schedule,edge,baseline,"clean","receiver_attack_mse")
                    exmu,exlo,exhi=paired_interval(d-(ac-bc))
                    network_cost=vals(schedule,edge,"mean","clean","mse_all").mean()/vals(schedule,edge,baseline,"clean","mse_all").mean()-1
                    receiver_cost=vals(schedule,edge,"mean","clean","receiver_normal_full_mse").mean()/vals(schedule,edge,baseline,"clean","receiver_normal_full_mse").mean()-1
                    pair_rates={};fair=True
                    if baseline in DETECTORS:
                        for split in ("normal_audit","test"):
                            ra=rates[split,schedule,edge,"mean","steady"];rb=rates[split,schedule,edge,baseline,"steady"]
                            pair_rates[split+"_candidate_fpr"]=ra;pair_rates[split+"_baseline_fpr"]=rb
                            lower,upper=acceptance["target_steady_fpr_range"]
                            fair&=(lower<=ra<=upper and lower<=rb<=upper and abs(ra-rb)<=acceptance["max_steady_fpr_difference"])
                    else:fair=False
                    margin=a-.99*b;se=np.std(margin,ddof=1)/np.sqrt(N)
                    one={"schedule":schedule,"edge_label":edge,"scenario":scenario,"candidate":"mean","baseline":baseline,
                        "receiver_relative_gain":float(-mu/b.mean()),"paired_difference":mu,"bootstrap95_low":lo,"bootstrap95_high":hi,
                        "paired_excess_difference":exmu,"excess95_low":exlo,"excess95_high":exhi,
                        "normal_network_cost":float(network_cost),"normal_receiver_cost":float(receiver_cost),
                        "normal_fpr_comparable":bool(fair),**pair_rates,
                        "practical_margin_mean":float(margin.mean()),"practical_p":p_less(margin),
                        "family95_lower_practical_margin":float(margin.mean()-stats.t.ppf(1-.05/(2*12),N-1)*se)}
                    all_comparisons.append(one)
                    if edge=="primary" and scenario in {"step","half_step"} and baseline.startswith("white_"):primary.append(one.copy())
    assert len(primary)==12
    ps=holm([r["practical_p"] for r in primary])
    cells=[]
    for r,p in zip(primary,ps):
        r["holm_p"]=float(p)
        r["normal_acceptable"]=bool(r["normal_fpr_comparable"] and r["normal_network_cost"]<=acceptance["max_network_mse_increase"] and r["normal_receiver_cost"]<=acceptance["max_receiver_clean_mse_increase"])
        r["passes"]=bool(p<.05 and r["normal_acceptable"] and r["receiver_relative_gain"]>=.01)
    for schedule in plan["schedules"]:
        for scenario in ("step","half_step"):
            selected=[r for r in primary if r["schedule"]==schedule and r["scenario"]==scenario]
            ext=[r for r in all_comparisons if r["schedule"]==schedule and r["scenario"]==scenario and r["edge_label"]=="external_reversed_sensitivity" and r["baseline"].startswith("white_")]
            external_ok=all(r["receiver_relative_gain"]>=-.02 for r in ext)
            cells.append({"schedule":schedule,"scenario":scenario,"primary_all_three":all(r["passes"] for r in selected),
                          "external_no_gt2pct_degradation":external_ok,"passes":all(r["passes"] for r in selected) and external_ok})
    gate={"passed":sum(r["passes"] for r in cells)>=2,"primary_comparisons":12,"passed_primary_comparisons":sum(r["passes"] for r in primary),
          "cells":cells,"passed_cells":sum(r["passes"] for r in cells),"family95_cases_excluding_1pct_gain":sum(r["family95_lower_practical_margin"]>0 for r in primary),
          "inference_scope":"one fixed heterogeneous full-local-observability model; fixed learned moments; point-estimate normal acceptance; paired seed-level tests"}
    write_json(folder/"contribution_gate.json",gate);write_csv(folder/"primary_tests.csv",primary)
    write_csv(folder/"all_comparisons.csv",all_comparisons);write_csv(folder/"performance_summary.csv",summary)
    figures=folder/"figures";figures.mkdir(exist_ok=True)
    fig,ax=plt.subplots(figsize=(11,6))
    for j,r in enumerate(primary):
        b=vals(r["schedule"],"primary",r["baseline"],r["scenario"],"receiver_attack_mse").mean()
        center=100*r["paired_difference"]/b;left=100*r["bootstrap95_low"]/b;right=100*r["bootstrap95_high"]/b
        ax.errorbar(center,j,xerr=[[center-left],[right-center]],fmt="o",capsize=3,color="tab:blue" if r["normal_acceptable"] else "tab:orange")
    ax.axvline(0,color="gray");ax.axvline(-1,color="tab:red",linestyle="--",label="-1% practical margin")
    ax.set_yticks(range(len(primary)),[r["schedule"]+" / "+r["scenario"]+" / "+r["baseline"] for r in primary]);ax.invert_yaxis()
    ax.set_xlabel("(Mean detector - baseline) / baseline receiver MSE (%)")
    ax.set_title("192 paired holdout seeds; display intervals unadjusted; gate uses Holm12")
    ax.legend();ax.grid(axis="x",alpha=.2);fig.tight_layout()
    for ext in ("png","pdf"):fig.savefig(figures/("primary_comparisons."+ext),dpi=160,bbox_inches="tight")
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for ax,schedule in zip(axes,plan["schedules"]):
        for d in DETECTORS:
            yy=[100*rates["test",schedule,"primary",d,ph] for ph in PHASES]
            ax.plot(range(3),yy,marker="o",label=LABELS[d])
        ax.axhline(5,color="gray",linestyle="--");ax.set_xticks(range(3),PHASES)
        ax.set_ylabel("Normal complete-episode false isolation (%)");ax.set_title(schedule);ax.grid(alpha=.2)
    axes[1].legend(fontsize=8);fig.tight_layout()
    for ext in ("png","pdf"):fig.savefig(figures/("phase_false_isolation."+ext),dpi=160,bbox_inches="tight")
    plt.close(fig)
    lines=["# 分阶段校准与序贯强基准：验证结果","",f"计划：{plan['id']}；最终测试192个全新种子。每个日程/攻击边/方法/场景都运行并保留，不依据测试结果调参。",
        "",f"**完整贡献门槛：{'通过' if gate['passed'] else '未通过'}。主要12项对照通过{gate['passed_primary_comparisons']}项，满足全部三基准且外部边无明显退化的场景单元{gate['passed_cells']}/4。**",
        "","## 实验的实际变化","",
        "- 正常缓存周期按起始时刻分为initial、transient、steady，分别拟合；仿真末尾未结束的周期不用于阈值与误隔离率分母。",
        "- 五种检测器共享年龄权重和正常联合协方差。白化窗口、能量CUSUM及双侧分量CUSUM只使用当前/历史合法残差；过去的白化增量不因未来样本到来而回写。",
        "- 各检测器用正常tune数据固定四轮调整至相同5%目标，另用normal_audit和test实测。不是声称任意时间/任意分布都有严格5%保证。",
        "- 核心比较是原攻击边全幅/半幅FDI下mean对三序贯基准；外部边、低幅、Replay和瞬时对照均额外报告，不能替代未通过主要门槛。",
        "","## 主要效果","","正值表示mean更好。Holm p检验至少1%改善，正常代价/误隔离匹配为预设点估计筛查。","",
        "| 日程 | 攻击 | 基准 | 接收节点MSE改善 | Holm p | 正常代价合格 | 门槛 |","|---|---|---|---:|---:|---|---|"]
    for r in primary:lines.append(f"| {r['schedule']} | {r['scenario']} | {r['baseline']} | {100*r['receiver_relative_gain']:+.3f}% | {r['holm_p']:.4g} | {r['normal_acceptable']} | {r['passes']} |")
    lines += ["","## 正常误隔离率：审计与最终测试","","不使用审计/测试结果再次调门限。以下是整条缓存驻留周期首次误隔离率，分母仅为完整周期。","",
        "| 日程 | 方法 | 审计稳态 | 测试初始 | 测试过渡 | 测试稳态 |","|---|---|---:|---:|---:|---:|"]
    for schedule in plan["schedules"]:
        for method in DETECTORS:
            rr=[rates["normal_audit",schedule,"primary",method,"steady"]]+[rates["test",schedule,"primary",method,p] for p in PHASES]
            lines.append(f"| {schedule} | {method} | "+" | ".join(f"{100*v:.3f}%" for v in rr)+" |")
    lines += ["","## 外部攻击边的结果","","| 日程 | 攻击 | 基准 | mean接收节点MSE改善 |","|---|---|---|---:|"]
    for r in all_comparisons:
        if r["edge_label"]=="external_reversed_sensitivity" and r["scenario"] in {"step","half_step"} and r["baseline"].startswith("white_"):
            lines.append(f"| {r['schedule']} | {r['scenario']} | {r['baseline']} | {100*r['receiver_relative_gain']:+.3f}% |")
    lines += ["","## 解释限制与复核入口","",
        "- 协方差来自共同正常age-only运行；实际非线性防御下分布可能变化，正常门限调节只作有限迭代。",
        "- 白化为估计条件矩下的因果变换，不保证实际运行创新严格独立高斯；门限由正常周期最大值经验校准，不使用错误独立卡方假设。",
        "- 统计独立单位是192种子，不是26,880条方法轨迹；结果条件于拟合的正常参数，不包含训练数据重采样不确定性。",
        "- 正常MSE代价和FPR匹配是点估计接受条件，不是非劣性证明；per_seed_phase_rates按轨迹保存，区间按轨迹聚类bootstrap。",
        "- 这是同一研究架构中的CUSUM/窗口机制对照，不是Tunga2018闭环控制系统完整复现，也不意味着穷尽所有CUSUM参数。",
        "- 初始化初始周期短、样本有限，单独报告后不能与稳态混为一个全时误隔离保证。",
        "","[主要效果图](figures/primary_comparisons.png) · [分阶段误隔离率图](figures/phase_false_isolation.png)",
        "","数据：plan.json、registration.json、sources/、phase_sample_counts.csv、frozen_controls.json、normal_audit_rates.csv、per_seed_metrics.csv、per_seed_phase_rates.csv、primary_tests.csv、all_comparisons.csv、各方法轨迹NPZ及逐周期CSV。"]
    (folder/"REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(gate),flush=True)


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("folder");args=parser.parse_args();summarize(args.folder)
