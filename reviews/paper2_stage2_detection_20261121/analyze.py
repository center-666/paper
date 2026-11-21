"""Offline reporting from frozen output moments; no random samples generated."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import beta
from information_upper_bounds import infer_event_power_upper
from run_experiment import NAMES, METHODS, sha, write, check_frozen

HERE = Path(__file__).resolve().parent


def cp_interval(k, n, level=.95):
    eta = 1 - level
    lo = 0. if k == 0 else float(beta.ppf(eta / 2, k, n - k + 1))
    hi = 1. if k == n else float(beta.ppf(1 - eta / 2, k + 1, n - k))
    return lo, hi


def binary_cell(moment):
    n, k = moment["n"], int(round(moment["sum"]))
    lo, hi = cp_interval(k, n)
    return k, n, lo, hi


def load_cases(stage, protocol):
    rows = []
    for model in protocol["models"]:
        for b in protocol["attack_strengths"]:
            for onset in protocol["onsets"]:
                p = HERE / "results" / stage / f"{model['id']}_b{b:g}_onset{onset}.json"
                row = json.loads(p.read_text(encoding="utf8"))
                if row["n"] != protocol["final_episodes_per_case" if stage == "final" else "screen_episodes_per_case"]:
                    raise AssertionError("Unexpected sample size")
                rows.append(row)
    return rows


def make_figures(cases, information):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "pdf.fonttype": 42, "svg.fonttype": "none"})
    folder = HERE / "figures"
    folder.mkdir(exist_ok=True)
    labels = ("D0 Azuma", "D1 fixed LR", "D2 amplitude mix", "D3 double mix",
              "D4 CUSUM", "Matched oracle LR")
    colors = plt.get_cmap("tab10").colors
    fixed = [r for r in cases if r["onset"] == 200]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for ax, model in zip(axes, ("S1", "U1")):
        data = sorted([r for r in fixed if r["model"]["id"] == model], key=lambda r:r["strength"])
        for j, name in enumerate(METHODS):
            x = [r["strength"] for r in data]
            y = [r["statistics"]["2048"][name + "/restricted_delay_eligible"]["mean"] for r in data]
            ax.plot(x, y, marker=("o","s","^","D","v","x")[j], color=colors[j],
                    label=labels[j], alpha=.8)
        ax.set(title=model + ": onset 200, horizon 2048", xlabel="Attack magnitude b",
               ylabel="Restricted mean delay (steps)")
        ax.set_ylim(0, 2150)
        ax.axhline(2048, color=".5", linestyle=":", label="Censoring horizon")
    axes[1].legend(fontsize=8, loc="best")
    for ext in ("pdf", "png"):
        fig.savefig(folder / ("01_magnitude_delay." + ext), dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    target_kl = .8 * np.log(.8 / .01) + .2 * np.log(.2 / .99)
    for ax, model in zip(axes, ("S1","U1")):
        for j, b in enumerate((.05,.1,.25)):
            data = sorted([r for r in information if r["model"]==model and
                           r["attack_strength"]==b and r["onset"]==200], key=lambda r:r["horizon"])
            x = [r["horizon"] for r in data]
            y = [r["sample_mean_conditional_KL_sum"] for r in data]
            upper = [r["population_event_record_KL_upper"] for r in data]
            ax.plot(x, y, "o-", color=colors[j], label=f"b={b:g}, mean KL")
            ax.fill_between(x, y, upper, color=colors[j], alpha=.15)
        ax.axhline(target_kl, color="black", linestyle="--",
                   label="Necessary KL: 80% unconditional power, 1% FPR")
        ax.set(yscale="log", title=model + ": full event record", xlabel="Post-onset events",
               ylabel="KL divergence (nats)")
        ax.legend(fontsize=7)
    for ext in ("pdf","png"):
        fig.savefig(folder / ("02_information_budget." + ext), dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for ax, model in zip(axes, ("S1","U1")):
        case = next(r for r in fixed if r["model"]["id"]==model and r["strength"]==.25)
        for j, name in enumerate(METHODS):
            x = [case["statistics"][str(H)][name + "/restricted_delay_eligible"]["mean"]
                 for H in (512,1024,2048)]
            y = [case["statistics"][str(H)][name + "/pre_MSE_eligible"]["mean"]
                 for H in (512,1024,2048)]
            ax.plot(x, y, "o-", color=colors[j], label=labels[j], alpha=.8)
        ax.set(title=model + ": b=0.25, onset 200; own survivors",
               xlabel="Restricted mean delay (steps)",
               ylabel="Pre-alarm cumulative MSE (no recovery)")
        ax.legend(fontsize=7)
    for ext in ("pdf","png"):
        fig.savefig(folder / ("03_delay_pre_alarm_loss." + ext), dpi=180)
    plt.close(fig)


def main():
    check_frozen()
    p = json.loads((HERE / "protocol.json").read_text(encoding="utf8"))
    final = load_cases("final", p)
    screen = load_cases("screen", p)
    output = HERE / "analysis"
    output.mkdir(exist_ok=True)
    rows, info = [], []
    for case in final:
        for H in p["horizons_after_onset"]:
            stat = case["statistics"][str(H)]
            bound = infer_event_power_upper(stat["oracle_conditional_KL"], case["model"],
                                           case["strength"], H, p["alpha"], .05 / 72)
            bound["onset"] = case["onset"]
            bound["eligible_power_upper"] = min(
                1., bound["binary_data_processing_detection_probability_upper"] / (1-p["alpha"]))
            info.append(bound)
            for name in METHODS:
                k, n, lo, hi = binary_cell(stat[name + "/detection_eligible"])
                rows.append({
                    "model": case["model"]["id"], "b": case["strength"], "onset": case["onset"],
                    "horizon": H, "method": name,
                    "detected": k, "eligible_n": n, "detection_rate": k / n,
                    "CP_lower95": lo, "CP_upper95": hi,
                    "pre_onset_alarms": int(round(stat[name + "/pre_onset_alarm"]["sum"])),
                    "restricted_delay": stat[name + "/restricted_delay_eligible"]["mean"],
                    "pre_MSE": stat[name + "/pre_MSE_eligible"]["mean"],
                    "pre_MSE_se": stat[name + "/pre_MSE_eligible"]["se"],
                    "pre_bias_energy_unconditional": stat[name + "/pre_bias_energy"]["mean"],
                    "full_MSE": stat["monitor_total_MSE"]["mean"] / H,
                    "full_MSE_excess": stat["monitor_total_MSE_excess"]["mean"] / H,
                })
    with (output / "all_detection_metrics.csv").open("w", encoding="utf8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    distributions=[]
    for case in final:
        for name in METHODS:
            s=case["statistics"]
            n=s["2048"][name+"/detection_eligible"]["n"]
            cumulative=[int(round(s[str(H)][name+"/detection_eligible"]["sum"]))
                        for H in (512,1024,2048)]
            distributions.append({
                "model":case["model"]["id"],"b":case["strength"],"onset":case["onset"],
                "method":name,"eligible_n":n,
                "pre_onset_alarm_n":case["n"]-n,
                "detected_steps_1_512":cumulative[0],
                "detected_steps_513_1024":cumulative[1]-cumulative[0],
                "detected_steps_1025_2048":cumulative[2]-cumulative[1],
                "not_detected_by_2048":n-cumulative[2]})
    with (output/"delay_distribution_bins.csv").open("w",encoding="utf8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(distributions[0]))
        writer.writeheader()
        writer.writerows(distributions)
    write(output / "information_power_bounds.json", info)
    primary = next(r for r in rows if r["model"]=="S1" and r["b"]==.25 and
                   r["onset"]==200 and r["horizon"]==2048 and r["method"]==NAMES[3])
    gate = (primary["CP_lower95"] >= .8 and primary["restricted_delay"] <= 1024)
    write(output / "engineering_gate.json", {
        "result": "PASS" if gate else "FAIL", "primary": primary,
        "frozen_gate": p["primary_gate"], "parameters_retuned": False,
        "theory_or_code_failure": False})
    make_figures(final, info)
    lines = [
        "# 阶段 2：最终独立确认结果",
        "",
        "本包按冻结方案完成24组初筛（每组20,000条）及24组独立确认（每组50,000条），"
        "另有两模型的8192拍健康长测试。最终比较不复用初筛样本，也未据初筛调参。"
        "三个评价时域512/1024/2048是同一episode上的嵌套观察。",
        "",
        "## 2048 拍检测功效",
        "",
        "以下是攻击前未误报轨迹中的条件检出率；完整计数、Clopper–Pearson区间、攻击前误报、"
        "删失延迟与损伤统计见 [CSV](analysis/all_detection_metrics.csv)。"
        "每种方法分别具有1%误报预算，不把五方法报警并集视为仍有1%保证。",
        "比较使用相同的理论误报上限，并非相同的实测误报率。D4是本轮有限时域保守校准版本；"
        "其结果不代表所有CUSUM校准方法的最佳功效。",
        "区间为逐格95%区间，不是全表同时区间。延迟分为1–512、513–1024、1025–2048和"
        "[超过2048仍未检出四档](analysis/delay_distribution_bins.csv)，没有删去未检出样本。",
        "",
        "| 模型 | b | 真实起点（仅离线） | D0 | D1 | D2 | D3 | D4 | 已知起点和幅值的匹配LR |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for case in final:
        stat = case["statistics"]["2048"]
        vals = [100 * stat[name + "/detection_eligible"]["mean"] for name in METHODS]
        lines.append(f"| {case['model']['id']} | {case['strength']:.2f} | {case['onset']} | " +
                     " | ".join(f"{x:.3f}%" for x in vals) + " |")
    lines.extend([
        "",
        f"预先制定的主工程门结果：**{'PASS' if gate else 'FAIL'}**。S1、b=0.25、起点200时，"
        f"D3检出 {primary['detected']}/{primary['eligible_n']}，95%区间为"
        f"[{100*primary['CP_lower95']:.4f}%, {100*primary['CP_upper95']:.4f}%]；"
        f"受限平均延迟 {primary['restricted_delay']:.2f} 拍。目标是检出率下界80%、受限平均延迟不超过1024拍。",
        "",
        "D3在静默动作之后不积累证据，也忽略发送前的残留偏差；这是有保证的保守实现，"
        "不能把其低功效单独当作所有事件型方法的上限。匹配LR使用真实起点与幅值，"
        "只是离线强参照，不能用于部署或冒称未知攻击参数已识别。",
        "",
        "## 超出具体检测器的信息限制",
        "",
        "相位平均事件概率关于偏差是偶函数，弱攻击的一阶变化消失。"
        "结合持续同向攻击的全历史偏差不变区间，得到每拍事件KL至多 C b⁴；"
        "任何只读取事件历史、误报不超过1%的方法，都受该信息限制。"
        "最终样本再用有界经验Bernstein和二元数据处理收紧总体KL上界，"
        "同时覆盖全部24×3格的置信度为95%。这项信息分析在初筛启动后推导、"
        "最终确认前固定，不是原附件的性能指标。",
        "",
        "下面取固定起点200、2048拍。上界为无条件检出概率；"
        "条件于攻击前未误报时，最多除以0.99。",
        "",
        "| 模型 | b | 事件记录KL样本均值 | KL总体上置信界 | 任意事件型检测器功效上界 |",
        "|---|---:|---:|---:|---:|",
    ])
    for r in info:
        if r["onset"]==200 and r["horizon"]==2048:
            lines.append(f"| {r['model']} | {r['attack_strength']:.2f} | "
                         f"{r['sample_mean_conditional_KL_sum']:.6g} | "
                         f"{r['population_event_record_KL_upper']:.6g} | "
                         f"{100*r['binary_data_processing_detection_probability_upper']:.2f}% |")
    lines.extend([
        "",
        "这些限制只适用于事件串和由事件确定的协方差标签。连续载荷、相位、码字或主动增加的"
        "可信测量不在上界的信息集内。不能外推为整个系统无法检测或无法恢复。",
        "",
        "## 健康长时间运行",
        "",
        "每模型独立确认50,000条8192拍轨迹。D1/D2/D3策略原样延长；"
        "D0/D4重新使用预先声明的8192拍有限预算，不能叫2248配置的无修改延长。",
        "",
        "| 模型 | 方法 | 报警数/50,000 | 比例 | 95% CP区间 |",
        "|---|---|---:|---:|---:|",
    ])
    for model in p["models"]:
        health = json.loads((HERE / "results" / "health_final" / f"{model['id']}.json").read_text(encoding="utf8"))
        for name in NAMES:
            k,n,lo,hi = binary_cell(health["statistics"]["8192"][name+"/healthy_alarm"])
            lines.append(f"| {model['id']} | {name} | {k}/{n} | {100*k/n:.4f}% | "
                         f"[{100*lo:.4f}%, {100*hi:.4f}%] |")
    lines.extend([
        "",
        "有限健康测试没有报警不等于全时域误报为零；全时域控制来自鞅证明。"
        "原量化连续相位与参数模型正确性是证明前提，模型失配尚未纳入。",
        "",
        "## 报警前损伤与总 MSE",
        "",
        "本轮未实现恢复，所有方法共用同一monitor输出，总MSE逐路径相同。"
        "提前截止的报警前MSE只能解释为停止前暴露，不能当作实际降损。图03显示各方法自身"
        "幸存集合上的条件均值；配对比较以表中共同幸存轨迹的D3−D0为准。",
        "",
        "| 模型 | b | H | 总MSE/拍 | 相对健康MSE增量/拍 | D0报警前累计MSE | D3报警前累计MSE | D3−D0（共同幸存轨迹，均值±1.96SE） |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for case in final:
        if case["onset"] != 200 or case["strength"] != .25:
            continue
        for H in p["horizons_after_onset"]:
            s=case["statistics"][str(H)]
            difference=s["D3_minus_D0_pre_MSE_common_eligible"]
            lines.append(f"| {case['model']['id']} | .25 | {H} | "
                         f"{s['monitor_total_MSE']['mean']/H:.6f} | "
                         f"{s['monitor_total_MSE_excess']['mean']/H:.6f} | "
                         f"{s[NAMES[0]+'/pre_MSE_eligible']['mean']:.3f} | "
                         f"{s[NAMES[3]+'/pre_MSE_eligible']['mean']:.3f} | "
                         f"{difference['mean']:.4g} ± {1.96*difference['se']:.3g} |")
    lines.extend([
        "",
        "## 研究决定",
        "",
        "本轮新检测器未通过预先制定的工程目标。保留其正确的误报/能量理论，"
        "不再把继续增加事件-only检测器复杂度作为主攻方向。优先研究现有载荷、相位或新增可信信息"
        "如何改变信息量与损伤关系；"
        "任何利用相位、连续载荷或主动反馈的新方案都必须重新计入健康MSE和通信成本。"
        "不能靠更复杂的混合统计量越过已经证明的信息限制。",
        "下一项最小工程验证应比较“事件＋已有连续载荷／已知相位的联合证据”与标准创新残差基线，"
        "先证明新增信息确实提高有限时域功效，再进入新鲜可信检查点恢复。该联合方法尚未实现或验证，"
        "不能用本轮结果提前宣布有效。量化或随机化本身也不单列为原创算法。",
        "",
        "三张图：[幅值—受限延迟](figures/01_magnitude_delay.pdf)、"
        "[事件KL与必要检测信息](figures/02_information_budget.pdf)、"
        "[延迟—报警前损失](figures/03_delay_pre_alarm_loss.pdf)。",
        "",
        "确定性枚举、误差坐标等价检查、冻结记录和独立确认数据均保留。"
        "无正式论文改动；新增理论仍需直接近邻全文排重，标准e-process/CUSUM不单列为创新。",
    ])
    (HERE / "05_results_and_decision.md").write_text("\n".join(lines)+"\n", encoding="utf8", newline="\n")
    write(output / "analysis_manifest.json", {
        "final_cases":len(final),"screen_cases":len(screen),
        "final_attack_episodes":sum(r["n"] for r in final),
        "screen_attack_episodes":sum(r["n"] for r in screen),
        "confidence_family_cells":72,"confidence_family_failure":.05,
        "frozen_inputs_sha256":sha(HERE/"freeze.json"),
        "analysis_source_sha256":sha(Path(__file__)),
        "results_report_sha256":sha(HERE/"05_results_and_decision.md"),
        "new_random_samples_generated":False})
    print(json.dumps({"status":"ANALYZED","gate":gate,"primary":primary}, ensure_ascii=False))


if __name__ == "__main__":
    main()
