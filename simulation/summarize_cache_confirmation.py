from __future__ import annotations
import csv,json
from pathlib import Path
import numpy as np
from scipy import stats
from run_study import write_csv,write_json,paired_interval
from validation_summary import holm


def main(folder):
    folder=Path(folder);plan=json.loads((folder/"plan.json").read_text(encoding="utf-8"))
    with (folder/"per_seed_metrics.csv").open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
    ix={(r["model"],r["method"],r["scenario"],int(r["seed"])):r for r in rows};seeds=sorted({int(r["seed"]) for r in rows})
    def arr(model,method,scenario,key):return np.asarray([float(ix[model,method,scenario,s][key]) for s in seeds])
    comparisons=[];tests=[];means=[]
    for model in plan["models"]:
        for method in plan["methods"]:
            for scenario in plan["scenarios"]:
                means.append({"model":model,"method":method,"scenario":scenario,
                    **{key:float(np.mean(arr(model,method,scenario,key))) for key in ("mse_all","mse_attack_window","receiver_attack_mse","mean_received_weight","episode_alarm_rate_batch")}})
        for scenario in plan["scenarios"]:
            if scenario=="clean":continue
            for candidate in ("gls_cache","mean_cache"):
                for baseline in ("instant_cache","mean_cache","joint_cache","age_decay","fresh_only_cap"):
                    if candidate==baseline:continue
                    a=arr(model,candidate,scenario,"receiver_attack_mse");b=arr(model,baseline,scenario,"receiver_attack_mse")
                    ac=arr(model,candidate,"clean","receiver_attack_mse");bc=arr(model,baseline,"clean","receiver_attack_mse")
                    d=(a-ac)-(b-bc);mu,lo,hi=paired_interval(d)
                    neta=arr(model,candidate,scenario,"mse_attack_window");netb=arr(model,baseline,scenario,"mse_attack_window")
                    normal=arr(model,candidate,"clean","mse_all").mean()/arr(model,baseline,"clean","mse_all").mean()-1
                    row={"model":model,"candidate":candidate,"baseline":baseline,"scenario":scenario,
                        "network_total_relative_gain":float(1-neta.mean()/netb.mean()),"receiver_total_relative_gain":float(1-a.mean()/b.mean()),
                        "receiver_paired_excess_difference":mu,"receiver_excess95_low":lo,"receiver_excess95_high":hi,
                        "receiver_excess_gain_over_clean":float(-mu/bc.mean()),"normal_network_relative_cost":float(normal)}
                    comparisons.append(row)
                    if model==plan["primary_model"] and candidate=="gls_cache" and scenario in plan["primary_scenarios"] and baseline in plan["primary_baselines"]:
                        margin=d+.05*bc
                        p=float(stats.ttest_1samp(margin,0,alternative="less").pvalue)
                        tests.append({**row,"p_value":p,"margin_mean":float(margin.mean()),"normal_episodeFPR":float(arr(model,candidate,"clean","episode_alarm_rate_batch").mean())})
    ps=holm([r["p_value"] for r in tests]);assert len(tests)==4
    for r,p in zip(tests,ps):r.update(holm_p=float(p),passed=bool(p<.05 and r["normal_network_relative_cost"]<=.02 and r["normal_episodeFPR"]<=.06))
    write_csv(folder/"paired_comparisons.csv",comparisons);write_csv(folder/"primary_tests.csv",tests);write_csv(folder/"summary.csv",means)
    write_json(folder/"gate.json",{"primary_cases":4,"passed":all(r["passed"] for r in tests),"passed_cases":sum(r["passed"] for r in tests),"hypothesis":"GLS practical improvement over BOTH instantaneous and covariance-corrected arithmetic mean; fixed normal calibration"})
    lines=["# 缓存驻留证据：强简单基准确认","",f"新128测试种子；GLS相对瞬时与正确协方差均值的4项预设主比较，通过 {sum(r['passed'] for r in tests)}/4。复用前轮已提出问题，参数只由全新正常开发集选择。",
        "","## 主要对照","","| 场景 | 基准 | 接收节点攻击超额改善/基准正常MSE | 网络总MSE改善 | 正常MSE代价 | Holm p | 通过 |","|---|---|---:|---:|---:|---:|---|"]
    for r in tests:lines.append(f"| {r['scenario']} | {r['baseline']} | {100*r['receiver_excess_gain_over_clean']:+.3f}% | {100*r['network_total_relative_gain']:+.3f}% | {100*r['normal_network_relative_cost']:+.3f}% | {r['holm_p']:.4g} | {r['passed']} |")
    lines += ["","## 更简单的均值检验对瞬时检验（探索性）","","| 模型 | 场景 | 接收节点超额改善/正常MSE | 配对超额差95%区间 | 网络总MSE改善 |","|---|---|---:|---|---:|"]
    for r in comparisons:
        if r["candidate"]=="mean_cache" and r["baseline"]=="instant_cache":lines.append(f"| {r['model']} | {r['scenario']} | {100*r['receiver_excess_gain_over_clean']:+.3f}% | [{r['receiver_excess95_low']:+.6f}, {r['receiver_excess95_high']:+.6f}] | {100*r['network_total_relative_gain']:+.3f}% |")
    lines += ["","## 边界","","- GLS和均值累计都是标准统计工具；即使胜过单步检验也不自动构成新颖性。",
        "- 均值使用完整联合协方差的均值协方差，不把相关残差错误当独立，因此是有效强简单对照。",
        "- 计划检验针对GLS独立增量；不能把均值的个别探索性正面行偷换为原门槛通过。",
        "- 训练/标定包含初始化与末尾截断episode，整体周期误报预算不等于任意起始条件均满足。",
        "- 正常最小MSE选factor，且周期误报必须≤6%；age-only不作为检测器被强迫匹配5%误报。",
        "- 仍仅两个自行设定全秩本地量测模型、一个固定日程和一个攻击边，未证明一般稳健性或出版贡献。",
        "","材料：plan.json、registration.json、normal_validation.csv、per_seed_metrics.csv、各模型完整轨迹与正常校准episode、统计模型及source快照。"]
    (folder/"REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(tests))


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("folder");a=p.parse_args();main(a.folder)
