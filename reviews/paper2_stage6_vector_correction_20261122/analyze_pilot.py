"""Low-sample feasibility report; preserve failures and paired uncertainty."""
from pathlib import Path
import json,csv,math
import numpy as np
from scipy.stats import beta,t as student

HERE=Path(__file__).resolve().parent


def moment(values):
    a=np.asarray(values,float);n=len(a)
    mean=float(np.mean(a));se=float(np.std(a,ddof=1)/math.sqrt(n)) if n>1 else 0.
    half=float(student.ppf(.975,n-1))*se if n>1 else None
    return {"n":n,"mean":mean,"se":se,"student_95_low":mean-half if half is not None else None,
            "student_95_high":mean+half if half is not None else None}


def proportion(k,n):
    return {"k":k,"n":n,"rate":k/n,
            "CP95_low":0. if k==0 else float(beta.ppf(.025,k,n-k+1)),
            "CP95_high":1. if k==n else float(beta.ppf(.975,k+1,n-k))}


def main():
    p=json.loads((HERE/"pilot_protocol.json").read_text(encoding="utf8"))
    allrows=[];summary=[]
    for stage in ("screen","final"):
        n=p[stage+"_episodes_per_case"]
        completed=json.loads((HERE/"results_v2"/stage/"completion.json").read_text(encoding="utf8"))
        assert completed["episodes"]==3*n
        for b in p["attack_strengths"]:
            episodes=[json.loads((HERE/"results_v2"/stage/f"b{b:g}_episode{i:03d}.json").read_text(encoding="utf8"))
                      for i in range(n)]
            for ep in episodes:
                for H,s in ep["snapshots"].items():
                    allrows.append({"stage":stage,"b":b,"episode":ep["episode"],"H":int(H),
                        "monitor_MSE":s["monitor"],"point_MSE":s["point"],"certified_MSE":s["certified"],
                        "oracle_MSE":s["oracle"],"point_gain":s["point_gain"],
                        "certificate_gain":s["certified_gain"],"conditional_gain":s["conditional_certified_gain"],
                        "squared_actions":s["squared_actions"],"current_action_norm":s["current_certified_action_norm"],
                        "first_useful":s["first_useful"],"first_nonzero":s["first_nonzero"],
                        "coverage_violating_steps":s["coverage_violating_steps"],
                        "negative_conditional_gain_steps":s["negative_conditional_gain_steps"],
                        "total_run_seconds":ep["total_seconds"],
                        **{"time_"+k:v for k,v in ep["timing"].items()}})
            if stage!="final":continue
            for H in p["evaluation_windows"]:
                s=[ep["snapshots"][str(H)] for ep in episodes]
                entry={"b":b,"H":H,"n":n,
                    "current_certificate_at_least_z":proportion(sum(x["current_certified_action_norm"]>=p["primary_useful_level"]-1e-12 for x in s),n),
                    "ever_useful_by_endpoint":proportion(sum(x["first_useful"] is not None and x["first_useful"]<=p["attack_start"]+H-1 for x in s),n),
                    "coverage_violation_episode":proportion(sum(x["coverage_violating_steps"]>0 for x in s),n),
                    "conditional_worsening_episode":proportion(sum(x["negative_conditional_gain_steps"]>0 for x in s),n)}
                for key in ("monitor","point","certified","oracle","point_gain","certified_gain",
                            "conditional_certified_gain","squared_actions"):
                    entry[key]=moment([x[key] for x in s])
                entry["cost"]={key:moment([ep["timing"][key] for ep in episodes]) for key in episodes[0]["timing"]}
                entry["total_run_seconds"]=moment([ep["total_seconds"] for ep in episodes])
                summary.append(entry)
    folder=HERE/"analysis";folder.mkdir(exist_ok=True)
    with (folder/"per_episode.csv").open("w",encoding="utf8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(allrows[0]),lineterminator="\n")
        writer.writeheader();writer.writerows(allrows)
    (folder/"summary.json").write_text(json.dumps({"status":"COMPLETE","rows":summary,
        "statistics":"CP exact binomial intervals and descriptive paired Student-t intervals, n=12 per final case",
        "no_certification_of_0.1pct_failure_rate_from_small_samples":True},indent=2)+"\n",encoding="utf8",newline="\n")
    lines=["# 二维方向证书校正：小规模冻结试验","",
        "**阶段判断：二维模型的遗忘与投影风险理论通过核查，但当前方向证书原型尚未验证出可靠的实际降损优势，计算成本也未达在线要求。**",
        "",
        "本轮按用户后续指示优先完成二维模型、向量遗忘和安全方向理论，并在端到端成本预检后进行"
        "有限计算可行性试验。3组各4条初筛、各12条独立确认，总计48个episode。"
        "没有根据初筛调参，全部失败/零校正轨迹保留；该样本规模不支持验证0.1%的置信失效频率。","",
        "## 512拍累计MSE与配对改善","",
        "改进为monitor平方误差减校正输出平方误差，正值有利。"
        "以下均为相同轨迹配对；括号为描述性的95% Student-t区间，低样本下不作强分布无关结论。"
        "不同幅值行使用独立随机流，不能把行间monitor差直接当成攻击损伤。","",
        "| b | monitor累计MSE | 点估计补偿累计MSE | 证书校正累计MSE | 证书实际改善 [区间] | 点估计实际改善 [区间] |",
        "|---:|---:|---:|---:|---:|---:|"]
    for row in summary:
        if row["H"]!=512:continue
        display=lambda key:f"{row[key]['mean']:.4f} [{row[key]['student_95_low']:.4f}, {row[key]['student_95_high']:.4f}]"
        lines.append(f"| {row['b']:.2f} | {row['monitor']['mean']:.4f} | {row['point']['mean']:.4f} | "
                     f"{row['certified']['mean']:.4f} | {display('certified_gain')} | {display('point_gain')} |")
    lines+=["","## 有用证书","",
        "预先固定有用Euclidean校正范数z=.025。瞬时指标P(||c||≥z)与此前任一时刻达到该值分开列。"
        "没有把检测报警计作恢复成功。未检测/未认证不从分母删除。","",
        "| b | H | 终点有用证书/12 [CP95%] | 曾达到有用证书/12 | 覆盖违反episode |",
        "|---:|---:|---:|---:|---:|"]
    for row in summary:
        rate=row["current_certificate_at_least_z"];ever=row["ever_useful_by_endpoint"];fail=row["coverage_violation_episode"]
        lines.append(f"| {row['b']:.2f} | {row['H']} | {rate['k']}/{rate['n']} "
                     f"[{100*rate['CP95_low']:.1f}%, {100*rate['CP95_high']:.1f}%] | {ever['k']}/12 | {fail['k']}/12 |")
    lines+=["","## 完整计算成本","",
        "以下每个episode共562拍。维护成本包含参考混合、全部精确起点缓存以及区间计算；"
        "另列点估计评分、认证搜索和逐拍半空间传播。未把仅评分加速当成全部成本。","",
        "| b | 维护秒 | 点估计评分秒 | 认证搜索秒 | 传播秒 | 总秒/episode | 平均总毫秒/拍 |",
        "|---:|---:|---:|---:|---:|---:|---:|"]
    for row in summary:
        if row["H"]!=512:continue
        c=row["cost"];total=row["total_run_seconds"]["mean"]
        lines.append(f"| {row['b']:.2f} | {c['maintenance']['mean']:.3f} | {c['point_scoring']['mean']:.3f} | "
                     f"{c['certificate_search']['mean']:.3f} | {c['transport']['mean']:.3f} | {total:.3f} | {1000*total/562:.3f} |")
    budget=json.loads((HERE/"risk_budget.json").read_text(encoding="utf8"))
    lines+=["","## 条件风险与期望风险预算","",
        "覆盖时的条件风险改善与单条轨迹的实际平方误差改善不是同一指标。"
        "以下并列报告它们；不从某个正的条件风险值直接宣布总体MSE已显著降低。","",
        "| b | 512拍条件风险改善和 | 实际平方误差改善和 | 已认证平方动作和 | 通用期望预算下界 |",
        "|---:|---:|---:|---:|---:|"]
    for row in summary:
        if row["H"]!=512:continue
        bound=row["squared_actions"]["mean"]-budget["window_penalties"]["512"]
        lines.append(f"| {row['b']:.2f} | {row['conditional_certified_gain']['mean']:.6f} | "
                     f"{row['certified_gain']['mean']:.6f} | {row['squared_actions']['mean']:.6f} | {bound:.4f} |")
    lines+=["","预算列将样本平方动作均值代入理论充分式，只作规模诊断，不是总体期望的置信下界。"
        f"当前最坏历史污染范数包络为{budget['true_pollution_norm_bound']:.3f}，校正范数上限为1，"
        f"512拍失效惩罚为{budget['window_penalties']['512']:.3f}；它相当保守。"
        "若该诊断为负，只表示此统一充分界尚不能证明收益，不说明真实期望一定恶化。"]
    lines+=["","## 模型与计算限制","",
        "认证只在固定日历时刻127、255、383、511尝试，间隔中传播半空间。"
        "这是预定有限计算日程，不是每拍重新求完整凸包；半空间传播可能迅速衰减并返回零。"
        "点估计在同样时刻重估，其余时刻传播所选幅值，但没有覆盖保证。","",
        "第一次运行在第一发送载荷处因NumPy标量repr不是合法Decimal文本而退出，未产出完整性能轨迹。"
        "仅将输入转换为built-in float后repr，保存原freeze/start及修复记录，使用同种子在results_v2重跑，"
        "未改变模型、候选、阈值或统计方案。","",
        "理论证明使用连续高斯模型与精确记录。仿真噪声/物理误差使用float64，接收记录以其表示值的十进制文本送入"
        "区间似然；这不构成实际有限位通信概率模型的证明。"
        "也未验证模型失配、多个传感器或分布式融合。","",
        "当前实际收益结论只限这个小样本原型；若区间不排除零、证书频率低或完整计算昂贵，应据实保留，"
        "不能以理论覆盖替代工程有效性。"
        "二维协方差上解和任意历史矩阵收缩证书是独立的解析结果，不依赖此试验是否成功。"]
    strong=next(row for row in summary if row["b"]==.25 and row["H"]==512)
    gains=strong["certified_gain"]
    lines+=["","## 下一步应解决的具体瓶颈","",
        f"强档证书实际改善均值{gains['mean']:.4f}，描述性区间[{gains['student_95_low']:.4f}, "
        f"{gains['student_95_high']:.4f}]包含0。健康和中档均为零证书动作。"
        "强档点估计补偿的样本收益更大，但在健康样本中带来明显额外风险；本轮没有证明任何一方全面占优。","",
        "需要改进的是保持覆盖前提下的参数集合表示与区间排除成本，而非继续提高检测率。"
        "当前单半空间传播将后续输入放宽到[0,bmax]，丢弃了既有证据对恒定幅值的约束。"
        "新增[幅值下界保留推导](08_certificate_transport_information_loss.md)给出一种后续可检验的改进，"
        "但没有用于本次冻结试验，不将其潜在收益算入结果。",
        "",
        "完整凸包投影目前只实现并验证了有限外包端点的精确几何计算；"
        "尚未在性能试验中构造所有连续置信区间后做全投影。四维物理模型与多传感器扩展同样未运行。"]
    (HERE/"07_pilot_results.md").write_text("\n".join(lines)+"\n",encoding="utf8",newline="\n")
    print(json.dumps({"status":"ANALYZED","episodes":len(allrows)//3,"summary_rows":len(summary)}))


if __name__=="__main__":main()
