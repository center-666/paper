"""Summarize the immutable eight-seed, finite-action recovery probe."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

BASE=Path(__file__).resolve().parents[1]
SIM_ID="2026-11-13_g4_recovery_budget_r01"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_json(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8",newline="\n")


def main(run_id):
    source=BASE/"results"/SIM_ID
    out=BASE/"results"/run_id
    out.mkdir(parents=True,exist_ok=False)
    fingerprints={p.name:sha(p) for p in source.iterdir() if p.is_file()}
    with (source/"selected_policy_seed_metrics.csv").open(encoding="utf-8",newline="") as f:
        rows=list(csv.DictReader(f))
    with (source/"all_schedule_seed_metrics.csv").open(encoding="utf-8",newline="") as f:
        all_rows=list(csv.DictReader(f))
    aggregates=[]
    keys=sorted(set((r["method"],r["selector"],r["policy"]) for r in rows))
    for method,selector,policy in keys:
        group=[r for r in rows if (r["method"],r["selector"],r["policy"])==(method,selector,policy)]
        passive=[r for r in rows if (r["method"],r["selector"],r["policy"])==(method,selector,"passive")]
        avg=lambda field:float(np.mean([float(r[field]) for r in group]))
        normal=avg("network_passive_healthy_loss")
        baseline=float(np.mean([float(r["network_cumulative_mse"]) for r in passive]))
        receiver_base=float(np.mean([float(r["receiver_cumulative_mse"]) for r in passive]))
        gain=avg("network_reduction_vs_passive")
        clean_cost=avg("normal_false_activation_network_cost")
        a={"method":method,"selector":selector,"policy":policy,"seed_count":len(group),
            "network_passive_cumulative_mse":baseline,"receiver_passive_cumulative_mse":receiver_base,
            "network_cumulative_mse":avg("network_cumulative_mse"),"receiver_cumulative_mse":avg("receiver_cumulative_mse"),
            "network_reduction_percent":100*gain/baseline,
            "receiver_reduction_percent":100*avg("receiver_reduction_vs_passive")/receiver_base,
            "network_reduction_absolute":gain,"normal_cost_absolute":clean_cost,
            "normal_cost_percent":100*clean_cost/normal,
            "attack_specific_excess_reduction":gain+clean_cost,
            "attack_specific_excess_reduction_percent_total_loss":100*(gain+clean_cost)/baseline,
            "extra_payload_bytes_mean":avg("extra_payload_bytes"),
            "first_tolerance_return_steps_mean":avg("first_tolerance_return_steps"),
            "return_right_censored_fraction":avg("return_right_censored"),
            "positive_network_gain_seeds":sum(float(r["network_reduction_vs_passive"])>1e-12 for r in group),
            "min_seed_normal_cost":min(float(r["normal_false_activation_network_cost"]) for r in group),
            "max_seed_normal_cost":max(float(r["normal_false_activation_network_cost"]) for r in group)}
        aggregates.append(a)
    with (out/"aggregate_metrics.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(aggregates[0]),lineterminator="\n");w.writeheader();w.writerows(aggregates)
    lookup={(a["method"],a["selector"],a["policy"]):a for a in aggregates}
    gate=[]
    for method in ("cap_only","spatial_hard","zhou_random"):
        rules=[]
        for selector in ("fixed_lag8","nearest_current"):
            oracle=lookup[method,selector,"oracle_network_at_most_2"]
            simple=[lookup[method,selector,p] for p in ("fixed_frequency_2","uniform_random_2_exact_expectation")]
            rules.append(oracle["network_reduction_percent"]>=10 and any(a["network_reduction_percent"]>=5 and a["normal_cost_percent"]<=2 for a in simple))
        gate.append({"method":method,"both_rules_pass":all(rules)})
    assert not any(g["both_rules_pass"] for g in gate)
    doc=["# B：有限额外通信的最小恢复价值检验", "",
         f"基准提交 `ce5923164aee083769eb5f5b2bfb8af1c4585124`。仿真Run：`{SIM_ID}`；只读分析Run：`{run_id}`。", "",
         "## 结论", "",
         "**EXPERIMENTAL：当前五节点满秩模型、两条Replay规则、64字节额外状态载荷预算和预先限定动作集内，未显示值得开发新恢复调度器的收益。停止本轮B实际调度候选开发。** 这个停止决定只针对该实例；未证明更大预算、其他网络或所有主动恢复无价值。没有通过扩大预算、时隙、攻击强度或修改拓扑寻找有利结果。", "",
         "理想动作在强保护下约1.7%—1.9%的网络累计MSE下降，大部分也出现在相同动作的健康运行中。固定/均匀随机发送平均低于0.5%。这支持‘已有保护后可恢复余量较少’，不能证明一种新恢复算法。", "",
         "## 固定设置与权限", "",
         "仅复用原G2前8个测试seed（9500000—9500007），不是独立新确认数据。动力学、H、Q/R、拓扑、K、cap及门控参数均来自原v3，不拟合或调参。外生发送不变，攻击仍为0→1、tick200—249、14次实际替换。两条规则为固定滞后8个已发送包、最近邻真实历史包。", "",
         "允许额外发送只在tick250、254、258的原本静默节点：共11个广播机会；枚举空动作、11个单广播和55个双广播，共67个日程。每广播送两条出边，每边2个float64，共32状态载荷字节；预算最多2次广播，即64字节、4条额外边消息。三时隙均早于恢复窗结束，额外发送不会改变过去的攻击包或攻击次数。", "",
         "新包始终是当时sender的真实当前估计，**允许它仍受历史反馈污染**。没有获取未篡改原始攻击包，没有重置真实状态/缓存/协方差，没有假定新包健康。原engine直接执行所有日程，67个日程在状态0—250的估计一致；8个方法×攻击组合的被动receiver误差平方时间序列与已保存G2全时域逐点一致（最大误差0）。新增只读核查另验证network在状态250—400的被动误差平方序列；这些核查不等于已比较所有节点状态向量。", "",
         "恢复启动tick250和攻击停止已知是本轮oracle假设。64字节仅为新增状态载荷下界；终止通知、请求和协议头未计为0，而是尚未建模。固定频率动作预先固定为sender0在254、258广播；随机动作在55个双广播日程中均匀抽取，随机种子与系统噪声独立。另利用完整枚举给出其精确混合期望，不增加独立随机样本。", "",
         "oracle逐seed读取未来真实MSE，只是离线理想上包络，不是部署策略。它是**本动作集内**的最优，不是所有时刻/更大预算/所有算法的全局上界。‘同8seed最佳固定日程’也仅是样本内优化，不是泛化结果。", "",
         "## 真实恢复损失与通信预算", "",
         "主目标为状态251—300的网络平均平方误差之和；接收节点累计误差另列。下面改善均为种子均值的比，不平均逐seed比值。没有用67个日程或50个时刻冒充独立样本，没有作显著性或1%改善功效主张。", "",
         "|基线|Replay|被动网络累计MSE|固定2广播改善|均匀随机2广播改善|网络oracle≤2广播改善|同oracle接收者改善|额外载荷|",
         "|---|---|---:|---:|---:|---:|---:|---:|"]
    for method in ("raw_yang","cap_only","spatial_hard","zhou_random"):
        for selector in ("fixed_lag8","nearest_current"):
            oracle=lookup[method,selector,"oracle_network_at_most_2"]
            fixed=lookup[method,selector,"fixed_frequency_2"]
            random=lookup[method,selector,"uniform_random_2_exact_expectation"]
            doc.append(f"|{method}|{selector}|{oracle['network_passive_cumulative_mse']:.6f}|{fixed['network_reduction_percent']:.3f}%|{random['network_reduction_percent']:.3f}%|{oracle['network_reduction_percent']:.3f}%|{oracle['receiver_reduction_percent']:.3f}%|{oracle['extra_payload_bytes_mean']:.0f}字节|")
    doc += ["", "原始无保护Yang固定滞后损失很大，但相同预算oracle改善也只有3.62%；不能以其大MSE本身证明通信恢复值得立项。三个强保护下oracle均远低于本轮预先登记10%探索门槛，固定/随机也未达到5%。该门槛是内部筛选标准，不是期刊要求或普遍安全界。", "",
            "## 区分攻击恢复与普通健康估计收益", "",
            "设A_u为受攻累计MSE，H_u为同seed、同日程健康累计MSE。真实损失改善G=A_0−A_u；误触发正常代价N=H_u−H_0。消除攻击超额的量为(A_0−H_0)−(A_u−H_u)=G+N。不能把G全当成历史污染修正。", "",
            "|强基线/Replay|oracle真实损失下降G|同动作正常代价N|攻击超额减少G+N|正常代价/健康MSE|",
            "|---|---:|---:|---:|---:|"]
    for method in ("cap_only","spatial_hard","zhou_random"):
        for selector in ("fixed_lag8","nearest_current"):
            a=lookup[method,selector,"oracle_network_at_most_2"]
            doc.append(f"|{method}/{selector}|{a['network_reduction_absolute']:.6f}|{a['normal_cost_absolute']:.6f}|{a['attack_specific_excess_reduction']:.6f}|{a['normal_cost_percent']:.3f}%|")
    doc += ["", "负正常代价表示同动作恰好改善健康估计；这些oracle日程是根据受攻未来误差挑出的，不能据此声称健康场景普遍无风险。逐seed正常代价可正可负，完整结果保留。此处只给‘一次误启动条件下’的损失和字节，不假定已知误触发率，也不估算长期无条件正常开销。", "",
            "## 被动自然恢复与额外发送后的返回时间", "",
            "保持G2容差范式并修正搜索起点：从状态251起，连续5状态满足受攻误差范数≤被动健康误差范数+0.1，记录首次窗口起点距251的步数。未满足记右删失，不记0；它不是永久恢复，也不是与健康轨迹完全相等。所有主动方法使用同一个被动健康参考，避免因改变参考而制造‘恢复’。", "",
            "|基线/Replay|被动首次返回均值|固定发送|随机发送混合期望|网络oracle|被动/Oracle右删失比例|",
            "|---|---:|---:|---:|---:|---:|"]
    for method in ("raw_yang","cap_only","spatial_hard","zhou_random"):
        for selector in ("fixed_lag8","nearest_current"):
            a=lookup[method,selector,"passive"]; b=lookup[method,selector,"fixed_frequency_2"]
            c=lookup[method,selector,"uniform_random_2_exact_expectation"];d=lookup[method,selector,"oracle_network_at_most_2"]
            doc.append(f"|{method}/{selector}|{a['first_tolerance_return_steps_mean']:.3f}|{b['first_tolerance_return_steps_mean']:.3f}|{c['first_tolerance_return_steps_mean']:.3f}|{d['first_tolerance_return_steps_mean']:.3f}|{a['return_right_censored_fraction']:.3f}/{d['return_right_censored_fraction']:.3f}|")
    doc += ["", "## 理论、竞争与下一步决定", "",
            "DERIVED/STANDARD：额外广播把边缓存误差由b_old换为e_sender，单步MSE差含2E[e_passᵀεA(e_sender−b_old)]和平方项；其符号可正可负。固定模式传播及cost-to-go矩阵是标准工具。可证明的不劣化鲁棒调度证书必须先能从合法信息得到足够紧的后攻击误差二阶矩集；本轮没有做到，也没有将其包装为新定理。证明和解析反例见03。", "",
            "Nasiri2026的恢复批优化、Xu2026的重传/回滚、Soleymani的VoI最优通信已是直接竞争。架构差异不构成新意。原文证据及下载状态见01。", "",
            "**行动：停止这个实例中的残差主动调度开发，不做RL、不添加检测器、不增加预算搜索。** 只有外部新增证据（独立系统中强防御后仍存在显著可恢复损失、经完整日程优化给出更大收益、或合法预算信息结构使现成调度不可替代）才重开。不能用目前67日程结果否定全部主动恢复，也不能以理论可证挽救负性能筛选。", "",
            f"复现：先用新Run ID执行`code/recovery_budget_probe.py`；本分析只读原Run，以`code/analyze_recovery_budget.py --run-id 新分析ID`复算。详见`results/{SIM_ID}/preregistration.json`及`results/{run_id}/aggregate_metrics.csv`。原G1/G1-R/G2代码与结果均保留；新执行G3的结果单独归档，不借此更改其门槛。", ""]
    (BASE/"04_minimal_value_of_recovery.md").write_text("\n".join(doc),encoding="utf-8",newline="\n")
    write_json(out/"analysis.json",{"source_run":SIM_ID,"independent_seed_count":8,"gate_by_method":gate,
        "all_failed":not any(g["both_rules_pass"] for g in gate),"no_new_scheduler_developed":True,
        "source_hashes":fingerprints,"analysis_source_sha256":sha(Path(__file__)),
        "report_sha256":sha(BASE/"04_minimal_value_of_recovery.md")})
    assert fingerprints=={p.name:sha(p) for p in source.iterdir() if p.is_file()}
    print(json.dumps({"analysis_run":run_id,"completed":True,"aggregate_rows":len(aggregates),"decision":"STOP current instance, not all active recovery"}))


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--run-id",default="2026-11-13_g4_recovery_analysis_r01")
    args=parser.parse_args()
    if Path(args.run_id).name!=args.run_id:raise ValueError("Invalid Run ID")
    main(args.run_id)
