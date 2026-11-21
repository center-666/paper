"""Final independent data analysis; confidence intervals use episode units."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import numpy as np
from scipy.stats import beta
from core import NAMES
from run_experiment import HERE,METHODS,sha,write,check_frozen

SHORT={"E0_previous_event_mixture":"E0 event","E1_phase_event_mixture":"E1 phase event",
       "R0_selected_innovation_mixture":"R0 innovation","R1_biasaware_innovation_mixture":"R1 aware innovation",
       "P1_conditional_payload_mixture":"P1 selected payload","J1_joint_mixture":"J1 joint",
       "J0_joint_from_start":"J0 fixed start","oracle_joint":"Oracle joint"}


def cp(k,n):
    return (0. if k==0 else float(beta.ppf(.025,k,n-k+1)),
            1. if k==n else float(beta.ppf(.975,k+1,n-k)))


def load_cases(stage,p):
    cases=[]
    for model in p["models"]:
        for b in p["offgrid_strengths"] if stage=="offgrid" else p["attack_strengths"]:
            for onset in [p["offgrid_onset"]] if stage=="offgrid" else p["onsets"]:
                path=HERE/"results"/stage/f"{model['id']}_b{b:g}_onset{onset}.json"
                case=json.loads(path.read_text(encoding="utf8"))
                assert case["n"]==p[stage+"_episodes"] and case["frozen_hash"]==sha(HERE/"freeze.json")
                cases.append(case)
    return cases


def metric_rows(cases):
    rows=[]
    for case in cases:
        for H,s in case["statistics"].items():
            for name in METHODS:
                metric=s[name+"/detection_eligible"]
                n=metric["n"];k=int(round(metric["sum"]))
                lower,upper=cp(k,n)
                rows.append({
                    "stage":case["stage"],"model":case["model"]["id"],"b":case["strength"],
                    "onset":case["onset"],"H":int(H),"method":name,
                    "detected":k,"eligible_n":n,"power":k/n,"CP_lower95":lower,"CP_upper95":upper,
                    "pre_attack_alarm_n":int(round(s[name+"/pre_attack_alarm"]["sum"])),
                    "restricted_delay":s[name+"/restricted_delay_eligible"]["mean"],
                    "delay_detected_only":s[name+"/delay_detected"]["mean"],
                    "pre_MSE_eligible":s[name+"/pre_MSE_eligible"]["mean"],
                    "pre_bias_energy_eligible":s[name+"/pre_bias_eligible"]["mean"],
                    "monitor_MSE_per_step":s["monitor_MSE"]["mean"]/int(H),
                    "paired_MSE_excess_per_step":s["MSE_excess"]["mean"]/int(H)})
    return rows


def csvwrite(path,rows):
    with path.open("w",encoding="utf8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n")
        w.writeheader();w.writerows(rows)


def plots(cases):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"pdf.fonttype":42,
                         "axes.spines.top":False,"axes.spines.right":False})
    folder=HERE/"figures";folder.mkdir(exist_ok=True)
    methods=("E0_previous_event_mixture","R1_biasaware_innovation_mixture",
             "P1_conditional_payload_mixture","J1_joint_mixture","oracle_joint")
    colors=plt.get_cmap("tab10").colors
    fig,axes=plt.subplots(2,3,figsize=(12,7),sharex=True,sharey=True,constrained_layout=True)
    for i,model in enumerate(("S1","U1")):
        for j,b in enumerate((.05,.1,.25)):
            ax=axes[i,j]
            case=next(c for c in cases if c["model"]["id"]==model and c["strength"]==b and c["onset"]==200)
            for k,name in enumerate(methods):
                H=sorted(map(int,case["statistics"]))
                y=[case["statistics"][str(h)][name+"/detection_eligible"]["mean"] for h in H]
                ax.plot(H,y,marker=("o","s","^","D","x")[k],label=SHORT[name],color=colors[k],alpha=.85)
            ax.set(title=f"{model}, b={b:g}, onset 200",ylim=(-.02,1.02),xscale="log",xticks=[128,512,1024,2048])
            ax.set_xticklabels(["128","512","1024","2048"])
            if j==0:ax.set_ylabel("Detection probability (own survivors)")
            if i==1:ax.set_xlabel("Post-onset observations")
    axes[0,0].legend(fontsize=7)
    for ext in ("pdf","png"):fig.savefig(folder/("01_power_vs_horizon."+ext),dpi=180)
    plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
    for ax,model in zip(axes,("S1","U1")):
        data=sorted([c for c in cases if c["model"]["id"]==model and c["onset"]==200],key=lambda c:c["strength"])
        for k,name in enumerate(methods):
            ax.plot([c["strength"] for c in data],
                    [c["statistics"]["2048"][name+"/restricted_delay_eligible"]["mean"] for c in data],
                    marker="o",label=SHORT[name],color=colors[k])
        ax.set(title=model+": unknown onset 200",xlabel="Attack magnitude b",
               ylabel="Restricted mean delay (2048-step censoring)",ylim=(0,2150))
        ax.legend(fontsize=7)
    for ext in ("pdf","png"):fig.savefig(folder/("02_delay_by_magnitude."+ext),dpi=180)
    plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
    for ax,model in zip(axes,("S1","U1")):
        case=next(c for c in cases if c["model"]["id"]==model and c["onset"]==200 and c["strength"]==.25)
        names=methods[:-1]
        x=np.arange(len(names));s=case["statistics"]["512"]
        means=[s[name+"/pre_MSE_eligible"]["mean"] for name in names]
        ses=[s[name+"/pre_MSE_eligible"]["se"] for name in names]
        ax.bar(x,means,yerr=1.96*np.array(ses),color=colors[:len(names)],alpha=.85)
        ax.set_xticks(x,[SHORT[name] for name in names],rotation=18)
        ax.axhline(s["monitor_MSE"]["mean"],color="black",linestyle="--",label="Unconditional total MSE: same monitor")
        ax.set(title=model+": b=.25; bars use own survivors",
               ylabel="Cumulative pre-alarm MSE (no recovery)")
        ax.legend(fontsize=7)
    for ext in ("pdf","png"):fig.savefig(folder/("03_pre_alarm_exposure."+ext),dpi=180)
    plt.close(fig)


def main():
    check_frozen()
    p=json.loads((HERE/"protocol.json").read_text(encoding="utf8"))
    final=load_cases("final",p);screen=load_cases("screen",p);offgrid=load_cases("offgrid",p)
    folder=HERE/"analysis";folder.mkdir(exist_ok=True)
    rows=metric_rows(final);stress=metric_rows(offgrid)
    csvwrite(folder/"final_metrics.csv",rows)
    csvwrite(folder/"offgrid_metrics.csv",stress)
    bins=[]
    for case in final+offgrid:
        for name in METHODS:
            H=sorted(map(int,case["statistics"]))
            counts=[int(round(case["statistics"][str(h)][name+"/detection_eligible"]["sum"])) for h in H]
            n=case["statistics"][str(H[-1])][name+"/detection_eligible"]["n"]
            bins.append({"stage":case["stage"],"model":case["model"]["id"],"b":case["strength"],
                         "onset":case["onset"],"method":name,"eligible_n":n,
                         "1_128":counts[0],"129_512":counts[1]-counts[0],
                         "513_1024":counts[2]-counts[1],"1025_2048":counts[3]-counts[2],
                         "not_detected_2048":n-counts[3]})
    csvwrite(folder/"delay_bins.csv",bins)
    primary=[r for r in rows if r["b"]==.25 and r["onset"]==200 and r["H"]==512
             and r["method"]=="J1_joint_mixture"]
    gates=[{"model":r["model"],"pass":r["CP_lower95"]>=.8 and r["restricted_delay"]<=256,"metrics":r}
           for r in primary]
    write(folder/"engineering_gates.json",{"primary":gates,"all_pass":all(x["pass"] for x in gates),
                                           "frozen_gate":p["primary_gate"],"parameters_retuned":False})
    info=[]
    for case in final:
        for H,s in case["statistics"].items():
            for name in ("oracle_joint_log_LR","oracle_phase_event_log_LR","oracle_conditional_payload_log_LR"):
                m=s[name]
                info.append({"model":case["model"]["id"],"b":case["strength"],"onset":case["onset"],
                             "H":int(H),"contribution":name,"mean":m["mean"],"se":m["se"],
                             "n":m["n"],"interpretation":"Monte Carlo log-density contribution; mean targets KL, not a certified upper confidence bound"})
    csvwrite(folder/"matched_information.csv",info)
    paired_rows=[]
    for case in final:
        for H,s in case["statistics"].items():
            for key,m in s.items():
                if key.startswith("J1_minus_"):
                    paired_rows.append({"model":case["model"]["id"],"b":case["strength"],
                                        "onset":case["onset"],"H":int(H),"comparison":key,
                                        "n":m["n"],"mean":m["mean"],"se":m["se"]})
    csvwrite(folder/"paired_comparisons.csv",paired_rows)
    false_rows=[]
    for case in final:
        for name in METHODS:
            m=case["statistics"]["2048"][name+"/pre_attack_alarm"]
            k=int(round(m["sum"]));n=m["n"];lower,upper=cp(k,n)
            false_rows.append({"model":case["model"]["id"],"b":case["strength"],"onset":case["onset"],
                               "method":name,"n":n,"pre_attack_alarms":k,
                               "rate":k/n,"CP_lower95":lower,"CP_upper95":upper})
    csvwrite(folder/"pre_attack_false_alarms.csv",false_rows)
    plots(final)
    lines=[
        "# 阶段 3：事件—载荷联合检测独立确认报告","",
        "本轮完成24组×5,000条初筛、24组×50,000条独立确认、4组×20,000条网格外压力测试，"
        "以及两模型各5,000/50,000条8192拍健康筛查/确认。共1,510,000个独立episode单位。"
        "每条轨迹内的四个时域是嵌套记录，配对健康轨道不重复计数。","",
        "## 主工程门","",
        "预定目标：b=0.25、未知起点200、512个攻击后观测，J1条件检出概率95%下界至少80%，"
        "受限平均延迟至多256拍。所有检测器从时刻0运行，不在真实起点重置。","",
        "| 模型 | 结果 | 检出/幸存样本 | 条件检出率 [95% CP] | 受限平均延迟 |",
        "|---|---|---:|---:|---:|"]
    for entry in gates:
        r=entry["metrics"]
        lines.append(f"| {r['model']} | {'PASS' if entry['pass'] else 'FAIL'} | {r['detected']}/{r['eligible_n']} | "
                     f"{100*r['power']:.2f}% [{100*r['CP_lower95']:.2f}, {100*r['CP_upper95']:.2f}] | {r['restricted_delay']:.2f} |")
    lines+=["","## 信息与算法消融","","下表固定起点200、512观测；比例以各方法攻击前未报警轨迹为分母。"
             "区间和完整24组/四时域统计在 [final_metrics.csv](analysis/final_metrics.csv)。","",
             "| 模型 | b | E0旧事件 | E1相位事件 | R0校正创新 | R1偏差校正创新 | P1条件载荷 | J1联合 | J0固定起点 | Oracle联合 |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for case in final:
        if case["onset"]!=200:continue
        s=case["statistics"]["512"]
        values=[100*s[name+"/detection_eligible"]["mean"] for name in METHODS]
        lines.append(f"| {case['model']['id']} | {case['strength']:.2f} | "+" | ".join(f"{v:.2f}%" for v in values)+" |")
    lines+=["","联合方法通过主工程门不等于所有组件都有显著增量。"
             "特别要区分相对创新倾斜的提升与相对条件载荷P1的提升，后者可能很小。"
             "下面按共同幸存轨迹报告配对差，正的检出率差有利于J1，负的延迟和损失差有利于J1。"
             "完整逐设置配对数据见 [paired_comparisons.csv](analysis/paired_comparisons.csv)。"
             "误差栏为1.96个跨episode标准误，属于大样本描述，不是全表同时有限样本保证。","",
             "| 模型 | 对照 | 512拍检出率差（百分点） | 受限延迟差 | 报警前累计MSE差 |",
             "|---|---|---:|---:|---:|"]
    for case in final:
        if case["strength"]!=.25 or case["onset"]!=200:continue
        s=case["statistics"]["512"]
        for baseline in ("R1_biasaware_innovation_mixture","P1_conditional_payload_mixture"):
            metrics=[s["J1_minus_"+baseline+"/"+m+"_common_eligible"] for m in ("detection","delay","pre_MSE")]
            desc=[f"{scale*m['mean']:.4g} ± {scale*1.96*m['se']:.3g}" for scale,m in zip((100,1,1),metrics)]
            lines.append(f"| {case['model']['id']} | {SHORT[baseline]} | "+" | ".join(desc)+" |")
    lines+=["","## 未知起点和网格外幅值","","所有24个最终设置完整保留，没有按初筛效果选择。"
             "未知起点通过检验过程混合处理，候选状态从时刻0维护，属于正规化检验核，"
             "并非每个物理起点单独重置的精确似然。对网格内匹配幅值有有限初始化失配预算；"
             "网格外无相同有限总失配保证。以下压力测试在起点137、每组20,000条独立轨迹上进行。","",
             "| 模型 | b（不在候选网格） | H | J1检出率 [95% CP] | J1受限延迟 | P1检出率 |",
             "|---|---:|---:|---:|---:|---:|"]
    for r in stress:
        if r["method"]!="J1_joint_mixture" or r["H"] not in (512,2048):continue
        peer=next(x for x in stress if x["model"]==r["model"] and x["b"]==r["b"]
                  and x["H"]==r["H"] and x["method"]=="P1_conditional_payload_mixture")
        lines.append(f"| {r['model']} | {r['b']:.3f} | {r['H']} | {100*r['power']:.2f}% "
                     f"[{100*r['CP_lower95']:.2f}, {100*r['CP_upper95']:.2f}] | "
                     f"{r['restricted_delay']:.2f} | {100*peer['power']:.2f}% |")
    lines+=["","## 8192 拍健康误报","","每方法分别有1%的理想模型全时域误报保证。以下是独立健康确认的有限时域实测值，"
             "不是把实测误报校准到同一个数值，也不通过降低阈值追求更高检出。","",
             "| 模型 | 方法 | 报警/50,000 | 比例 [95% CP] |","|---|---|---:|---:|"]
    for model in p["models"]:
        health=json.loads((HERE/"results/health_final"/(model["id"]+".json")).read_text(encoding="utf8"))
        for name in NAMES:
            m=health["statistics"]["8192"][name+"/healthy_alarm"];k=int(round(m["sum"]));n=m["n"]
            lo,hi=cp(k,n)
            lines.append(f"| {model['id']} | {SHORT[name]} | {k}/{n} | {100*k/n:.3f}% [{100*lo:.3f}, {100*hi:.3f}] |")
    lines+=["","密度零点使联合倍率可能具有重尾；本包依赖条件归一化证明误报，而不是用样本平均倍率接近1来证明。"
             "所有CP区间是逐格区间，未把全表当作同时95%覆盖。","",
             "## 估计损伤与信息解释","","本轮检测不改变monitor输出，所有方法的总MSE逐路径相同。"
             "报警前MSE排除报警当拍，只代表假设当拍提交前可门控的暴露指标，不能叫已经实现的恢复收益。"
             "总MSE是全体episode无条件均值，报警前各方法列是自身幸存集合上的条件均值；"
             "不同集合的视觉差不能代替上面的共同幸存配对差。","",
             "| 模型 | 强攻击512拍总MSE/拍 | 相对健康增量/拍 | R1报警前MSE | P1报警前MSE | J1报警前MSE |",
             "|---|---:|---:|---:|---:|---:|"]
    for case in final:
        if case["strength"]!=.25 or case["onset"]!=200:continue
        s=case["statistics"]["512"]
        vals=[s[name+"/pre_MSE_eligible"]["mean"] for name in ("R1_biasaware_innovation_mixture","P1_conditional_payload_mixture","J1_joint_mixture")]
        lines.append(f"| {case['model']['id']} | {s['monitor_MSE']['mean']/512:.6f} | "
                     f"{s['MSE_excess']['mean']/512:.6f} | "+" | ".join(f"{v:.3f}" for v in vals)+" |")
    lines+=["","匹配联合对数似然严格分解为相位条件事件部分与条件载荷部分；"
             "其跨episode平均是总体KL的Monte Carlo估计，见 [matched_information.csv](analysis/matched_information.csv)。"
             "联合对数增量无界，这里的标准误不能冒称为上一阶段有界经验Bernstein置信界。","",
             "| 模型 | b | H | 联合logLR均值±1.96SE | 事件贡献 | 条件载荷贡献 |",
             "|---|---:|---:|---:|---:|---:|"]
    for case in final:
        if case["onset"]!=200:continue
        s=case["statistics"]["512"]
        terms=[s[key] for key in ("oracle_joint_log_LR","oracle_phase_event_log_LR","oracle_conditional_payload_log_LR")]
        descriptions=[f"{m['mean']:.5g} ± {1.96*m['se']:.3g}" for m in terms]
        lines.append(f"| {case['model']['id']} | {case['strength']:.2f} | 512 | "+" | ".join(descriptions)+" |")
    lines+=["",
             "## 范围、成本与研究决定","","每个部署通道以3个候选强度维护O(J)状态和当拍更新，不保存所有起点。"
             "接收端读取已有发送载荷、事件和精确反馈中心残差 r=c−m，未新增传感器测量或上行报文；"
             "因此性能结果对应精确中心可见接口，检测器没有读取原始相位phi。"
             "若实际日志仅保留整数码字索引，必须改用相位区间混合核重验证；当前数值不能直接沿用，"
             "见[相位可见性理论补充](11_phase_visibility_addendum.md)。"
             "精确中心结合已知预测值可以恢复规范化相位，因此该接口统计上并未隐藏相位。"
             "若审计器在外部，日志访问/传输成本另算。未测硬件实时延迟、有限字长、饱和或模型失配。"
             "文件中的运行秒数来自多核向量化模拟，不能当作在线单设备延迟。"
             "独立[接收端原型微基准](receiver_benchmark.json)使用固定输入，"
             "本机中位CPU时间约70–78微秒/拍；三候选四个持久数值数组共96字节，"
             "不含Python对象与估计器状态，且不是硬件最坏执行时间保证。","",
             "收益不能全部归因于随机量化：条件核对固定已知中心也成立。"
             "R0/R1是本轮预先固定的选择校正创新倾斜，不是QUICKDET的忠实复现，"
             "也未对倾斜参数作全局最优设计；当前实测优势只针对这些明确的对照。"
             "不把标准混合e-process或选后似然本身作为原创，也不把阶段2只读事件记录的限制"
             "外推到当前联合记录。是否需要完整联合通道，应根据P1对照作最终选择。"
             "恢复仍待新鲜可信信息和实际生产更新规则验证。","",
             "图：[功效—时域](figures/01_power_vs_horizon.pdf)、"
             "[幅值—受限延迟](figures/02_delay_by_magnitude.pdf)、"
             "[报警前暴露](figures/03_pre_alarm_exposure.pdf)。"
             "另有[固定历史的局部信息阶数检查](figures/04_local_information_scaling.pdf)，"
             "它是确定性核积分，不是额外检测性能样本。"
             "报告保留全部失败/弱攻击/网格外情况，正式论文未修改。"
             "近邻公式级定位见 [08号报告](08_novelty_boundary.md)，全球创新性仍未通过完整核查。"]
    (HERE/"07_results_and_decision.md").write_text("\n".join(lines)+"\n",encoding="utf8",newline="\n")
    write(folder/"analysis_manifest.json",{"final_cases":len(final),"screen_cases":len(screen),"offgrid_cases":len(offgrid),
          "source_sha256":sha(Path(__file__)),"report_sha256":sha(HERE/"07_results_and_decision.md"),
          "new_random_samples":False,"primary_gates":gates})
    print(json.dumps({"status":"ANALYZED","primary_gates":gates},ensure_ascii=False))


if __name__=="__main__":
    main()
