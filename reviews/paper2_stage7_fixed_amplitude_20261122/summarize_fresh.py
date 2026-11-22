"""Summarize the locked independent-seed full-search confirmation."""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
from scipy.stats import beta, t as student

HERE=Path(__file__).resolve().parent
OUT=HERE/"analysis"
OUT.mkdir(exist_ok=True)


def moment(values):
    x=np.asarray(values,dtype=float);n=len(x);m=float(x.mean())
    se=float(x.std(ddof=1)/math.sqrt(n)) if n>1 else 0.
    half=float(student.ppf(.975,n-1)*se) if n>1 else None
    return {"n":n,"mean":m,"se":se,
            "student_95_low":m-half if half is not None else None,
            "student_95_high":m+half if half is not None else None}


def proportion(k,n):
    return {"k":k,"n":n,"rate":k/n if n else None,
            "CP95_low":0. if k==0 else float(beta.ppf(.025,k,n-k+1)),
            "CP95_high":1. if k==n else float(beta.ppf(.975,k+1,n-k))}


def main():
    completion=json.loads((HERE/"results"/"fresh_confirmation_completion.json").read_text(encoding="utf8"))
    assert completion["status"]=="PASS" and completion["episodes"]==36
    rows=[json.loads(p.read_text(encoding="utf8")) for p in sorted((HERE/"results"/"fresh_confirmation").glob("b*_episode*.json"))]
    protocol=json.loads((HERE/"fresh_protocol.json").read_text(encoding="utf8"))
    cases={}
    for b in protocol["attack_strengths"]:
        eps=[x for x in rows if x["b"]==b]
        case={"b":b,"n":len(eps),"successful_certificate_episodes":proportion(
            sum(bool(e["successful_certificates"]) for e in eps),len(eps)),
            "mean_successful_certificates":moment([len(e["successful_certificates"]) for e in eps]),
            "coverage_violation_episode":proportion(sum(e["coverage_violations"]>0 for e in eps),len(eps)),
            "old_support_violation_episode":proportion(sum(e["old_support_violations"]>0 for e in eps),len(eps)),
            "bound_monotonicity_violation_episode":proportion(sum(e["bound_monotonicity_violations"]>0 for e in eps),len(eps)),
            "runtime_seconds":moment([e["total_seconds"] for e in eps]),
            "timing":{key:moment([e["timing"][key] for e in eps]) for key in eps[0]["timing"]},
            "windows":[]}
        for H in protocol["evaluation_windows"]:
            ss=[e["snapshots"][str(H)] for e in eps]
            metrics={
                "monitor_mse":[s["monitor"] for s in ss],
                "old_mse":[s["old"] for s in ss],
                "new_mse":[s["new"] for s in ss],
                "old_gain":[s["old_gain"] for s in ss],
                "new_gain":[s["new_gain"] for s in ss],
                "new_minus_old_gain":[s["new_gain"]-s["old_gain"] for s in ss],
                "old_conditional_gain":[s["old_conditional"] for s in ss],
                "new_conditional_gain":[s["new_conditional"] for s in ss],
                "old_gcert":[s["old_gcert"] for s in ss],
                "new_gcert":[s["new_gcert"] for s in ss],
            }
            case["windows"].append({"H":H,
                "old_useful_endpoint":proportion(sum(s["old_current_action_norm"]>=.025-1e-12 for s in ss),len(ss)),
                "new_useful_endpoint":proportion(sum(s["new_current_action_norm"]>=.025-1e-12 for s in ss),len(ss)),
                "old_ever_useful":proportion(sum(s["first_old_useful"] is not None for s in ss),len(ss)),
                "new_ever_useful":proportion(sum(s["first_new_useful"] is not None for s in ss),len(ss)),
                "metrics":{key:moment(value) for key,value in metrics.items()}})
        lag_summary={}
        for lag in (0,1,10,25,50):
            useful_new=useful_old=0
            new_norms=[];old_norms=[];gain=[];obs=0
            for e in eps:
                vals=[x for x in e["lag_snapshots"].values() if x.get("lag")==lag and "new_action_norm" in x]
                useful_new+=int(any(x["new_action_norm"]>=.025-1e-12 for x in vals))
                useful_old+=int(any(x["old_action_norm"]>=.025-1e-12 for x in vals))
                new_norms.extend(x["new_action_norm"] for x in vals)
                old_norms.extend(x["old_action_norm"] for x in vals)
                gain.extend(x["new_bound"]-x["old_bound"] for x in vals)
                obs+=len(vals)
            lag_summary[str(lag)]={"new_useful_episode_rate":proportion(useful_new,len(eps)),
                "old_useful_episode_rate":proportion(useful_old,len(eps)),
                "new_action_norm":moment(new_norms) if new_norms else None,
                "old_action_norm":moment(old_norms) if old_norms else None,
                "new_minus_old_gcert":moment(gain) if gain else None,
                "certificate_lag_observations":obs}
        case["lag_summary"]=lag_summary
        cases[str(b)]=case
    summary={"status":"PASS","seed":protocol["seed"],"fresh_independent_episodes":len(rows),
        "full_certificate_search":True,"protocol_frozen_before_samples":True,
        "confidence_intervals":"descriptive paired Student-t 95%; CP exact intervals for proportions",
        "cases":cases,"limitations":[
            "Twelve episodes per case do not establish a 0.1% confidence failure rate.",
            "The model assumes exact process/measurement noise parameters, event bit, reconstructed center, and continuous payload.",
            "The study is centralized, two-state, one scalar sensor and does not validate finite-word-length deployment."]}
    (OUT/"fresh_confirmation_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf8",newline="\n")
    lines=["# 阶段七：独立种子完整认证确认", "",
        f"协议种子 {protocol['seed']}，健康、弱攻击和强攻击各12条；逐条执行完整连续幅值认证搜索。认证时刻、门限、风险预算、方向生成和节点预算沿用冻结协议。区间为每组12条的描述性Student-t 95%区间；比例给Clopper–Pearson 95%区间。", "",
        "## 认证持续性", "",
        "| 攻击幅值 | 成功认证 | lag 50有用旧/新 | 512拍终点有用旧/新 | 覆盖/支持/非退化违反 |", "|---:|---:|---:|---:|---:|"]
    for b in protocol["attack_strengths"]:
        c=cases[str(b)];l=c["lag_summary"]["50"];w=c["windows"][-1]
        lines.append(f"| {b:.2f} | {c['successful_certificate_episodes']['k']}/12 | "
            f"{l['old_useful_episode_rate']['k']}/12, {l['new_useful_episode_rate']['k']}/12 | "
            f"{w['old_useful_endpoint']['k']}/12, {w['new_useful_endpoint']['k']}/12 | "
            f"{c['coverage_violation_episode']['k']}/12, "
            f"{c['old_support_violation_episode']['k']}/12, {c['bound_monotonicity_violation_episode']['k']}/12 |")
    lines += ["", "## 512拍配对累计MSE", "",
        "改善定义为monitor累计平方误差减估计输出累计平方误差，正值表示降低。", "",
        "| 攻击幅值 | 旧改善 | 新改善 | 新减旧改善 |", "|---:|---:|---:|---:|"]
    for b in protocol["attack_strengths"]:
        m=cases[str(b)]["windows"][-1]["metrics"]
        def fmt(key):
            x=m[key];return f"{x['mean']:.4f} [{x['student_95_low']:.4f}, {x['student_95_high']:.4f}]"
        lines.append(f"| {b:.2f} | {fmt('old_gain')} | {fmt('new_gain')} | {fmt('new_minus_old_gain')} |")
    lines += ["", "## 认证改善量与条件风险", "",
        "G_cert是可由算法输出的平方动作下界累计；G_cond用真实污染离线计算；G_sample是上一表的实际配对MSE差。", "",
        "| 攻击幅值 | 旧G_cert | 新G_cert | 旧G_cond | 新G_cond | 完整运行秒数 | 认证搜索秒数 |", "|---:|---:|---:|---:|---:|---:|---:|"]
    for b in protocol["attack_strengths"]:
        c=cases[str(b)];m=c["windows"][-1]["metrics"]
        lines.append(f"| {b:.2f} | {m['old_gcert']['mean']:.6g} | {m['new_gcert']['mean']:.6g} | "
            f"{m['old_conditional_gain']['mean']:.6g} | {m['new_conditional_gain']['mean']:.6g} | "
            f"{c['runtime_seconds']['mean']:.2f} | {c['timing']['certificate_search']['mean']:.2f} |")
    lines += ["", "## 解释边界", "",
        "该独立组在同一轨迹内并行计算旧半空间与新固定幅值传播，monitor、事件和载荷完全相同。成功/未决/失败认证均保留在分母中。零覆盖违反和不退化违反只表明本批实现自检通过，不证明失效率低于0.1%。强攻击的独立配对MSE区间决定恢复收益能否从阶段六消融推进为可重复证据；结果必须与G_cert、G_cond分开解读。", "",
        "端到端耗时包含完整方向提议、连续幅值置信搜索、维护、传播和输出校正。当前实现重复维护似然记录与响应缓存，耗时是保守原型的真实成本，不应按缓存回放时间替代。"]
    (HERE/"08_fresh_confirmation_results.md").write_text("\n".join(lines)+"\n",encoding="utf8",newline="\n")
    print(json.dumps({"status":"PASS","strong_success":cases["0.25"]["successful_certificate_episodes"],
        "strong_lag50_new":cases["0.25"]["lag_summary"]["50"]["new_useful_episode_rate"],
        "strong_gain512":cases["0.25"]["windows"][-1]["metrics"]["new_minus_old_gain"]},indent=2))


if __name__=="__main__":main()
