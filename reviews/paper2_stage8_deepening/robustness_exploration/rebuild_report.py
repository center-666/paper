from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
from scipy.stats import t as student_t

TASK = Path(__file__).resolve().parent
DATA = TASK / "data"
FIG = TASK / "figures"
REPORT = TASK / "robustness_report.md"
METHODS = ("M0", "M1_h0", "M1_q95", "M1", "M2", "M3", "M3_rho")
MAIN_METHODS = ("M0", "M1", "M2", "M3")
QUANT_ORDER = ("continuous", "12bit", "10bit", "8bit", "6bit", "4bit")
DRIFT_ORDER = tuple(f"decay_{x:02d}" for x in (0, 5, 10, 20, 35, 50)) + tuple(
    f"enhance_{x:02d}" for x in (5, 10, 20, 35, 50)
)
EPS_ORDER = tuple(f"eps_{x:+.2%}" for x in (0, .01, -.01, .02, -.02, .05, -.05))


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def data_rows():
    rows = []
    for experiment in ("quantization", "drift", "model_mismatch"):
        for path in sorted((DATA / experiment).glob("*.json")):
            if path.parent.name == "errors":
                continue
            rows.append(read(path))
    return rows


def paired_interval(values):
    values = np.asarray(values, dtype=float)
    if len(values) < 2:
        return float(values.mean()) if len(values) else 0.0, None, None
    mean = float(values.mean())
    half = float(student_t.ppf(.975, len(values) - 1) * values.std(ddof=1) / np.sqrt(len(values)))
    return mean, mean - half, mean + half


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["experiment"], row["scenario"], row["group"])].append(row)
    output = []
    detail = []
    for (experiment, scenario, group), cohort in sorted(groups.items()):
        by_index = {int(row["index"]): row for row in cohort}
        method_names = sorted({name for row in cohort for name in row["metrics"]})
        paired_by_method = {}
        if "M2" in method_names:
            for paired_method in method_names:
                if paired_method == "M2":
                    continue
                differences = [
                    by_index[i]["metrics"][paired_method]["actual_gain"]
                    - by_index[i]["metrics"]["M2"]["actual_gain"]
                    for i in sorted(by_index)
                ]
                paired_by_method[paired_method] = paired_interval(differences)
        transmission_rate = sum(row["transmissions"] for row in cohort) / sum(
            row["horizon"] for row in cohort
        )
        alias = all(row.get("aliased_identical_bias_path", False) for row in cohort)
        for method in method_names:
            values = [row["metrics"][method] for row in cohort]
            n = len(values)
            checks = sum(item["certificate_checks"] for item in values)
            violations = sum(item["risk_violations"] for item in values)
            conditional = np.asarray([item["conditional_gain"] for item in values], dtype=float)
            first = [item["first_useful"] for item in values if item["first_useful"] is not None]
            method_pair = paired_by_method.get(method)
            row_out = dict(
                experiment=experiment,
                scenario=scenario,
                group=group,
                method=method,
                n=n,
                transmission_rate=transmission_rate,
                actual_gain_mean=float(np.mean([item["actual_gain"] for item in values])),
                conditional_gain_mean=float(conditional.mean()),
                conditional_negative_trajectories=int((conditional < 0).sum()),
                conditional_negative_steps=sum(item["conditional_negative_steps"] for item in values),
                useful_steps_mean=float(np.mean([item["useful_steps"] for item in values])),
                useful_endpoint=int(sum(item["endpoint_useful"] for item in values)),
                first_useful_count=len(first),
                first_useful_median=float(np.median(first)) if first else None,
                false_action_trajectories=int(sum(item["false_action"] for item in values)),
                certificate_checks=checks,
                risk_violations=violations,
                risk_violation_rate=violations / checks if checks else None,
                paired_method_minus_M2_mean=method_pair[0] if method_pair else None,
                paired_method_minus_M2_t95_low=method_pair[1] if method_pair else None,
                paired_method_minus_M2_t95_high=method_pair[2] if method_pair else None,
                aliased_identical_bias_path=alias,
                cpu_seconds_sum=sum(row["cpu_seconds"] for row in cohort if not row.get("aliased_identical_bias_path")) if method == "M0" else None,
            )
            output.append(row_out)
            for trace in cohort:
                metric = trace["metrics"][method]
                detail.append(dict(
                    experiment=experiment,
                    scenario=scenario,
                    group=group,
                    index=trace["index"],
                    seed=trace["seed"],
                    method=method,
                    transmissions=trace["transmissions"],
                    transmission_rate=trace["transmissions"] / trace["horizon"],
                    actual_gain=metric["actual_gain"],
                    conditional_gain=metric["conditional_gain"],
                    conditional_negative_steps=metric["conditional_negative_steps"],
                    useful_steps=metric["useful_steps"],
                    first_useful=metric["first_useful"],
                    endpoint_useful=metric["endpoint_useful"],
                    false_action=metric["false_action"],
                    certificate_checks=metric["certificate_checks"],
                    risk_violations=metric["risk_violations"],
                    max_nominal_filter_error=trace["max_nominal_filter_error"],
                    spectral_radius_A_plant=trace["spectral_radius_A_plant"],
                    aliased_identical_bias_path=trace.get("aliased_identical_bias_path", False),
                ))
    return output, detail


def ordered_summary(summary, experiment):
    rows = [row for row in summary if row["experiment"] == experiment]
    if experiment == "quantization":
        order = {name: i for i, name in enumerate(QUANT_ORDER)}
    elif experiment == "drift":
        order = {name: i for i, name in enumerate(DRIFT_ORDER)}
    else:
        order = {name: i for i, name in enumerate(EPS_ORDER)}
    rows.sort(key=lambda row: (order.get(row["scenario"], 99), row["group"], row["method"]))
    return rows


def fmt(value, digits=4):
    if value is None:
        return "—"
    return f"{value:.{digits}f}"


def markdown_table(rows, columns):
    header = "| " + " | ".join(label for label, _ in columns) + " |"
    rule = "|" + "|".join("---" for _ in columns) + "|"
    body = [
        "| " + " | ".join(
            str(row.get(field, "—")) if isinstance(row.get(field), (str, int)) and row.get(field) is not None
            else fmt(row.get(field))
            for _, field in columns
        ) + " |"
        for row in rows
    ]
    return "\n".join([header, rule, *body])


def style_axes(ax):
    ax.grid(True, color="0.82", linewidth=.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def configure_font():
    names = {entry.name for entry in font_manager.fontManager.ttflist}
    for candidate in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"):
        if candidate in names:
            matplotlib.rcParams["font.sans-serif"] = [candidate, "DejaVu Sans"]
            break
    matplotlib.rcParams["axes.unicode_minus"] = False


def plot_quantization(summary):
    FIG.mkdir(parents=True, exist_ok=True)
    rows = [r for r in summary if r["experiment"] == "quantization" and r["method"] in ("M2", "M3")]
    xlabels = ["连续", "12", "10", "8", "6", "4"]
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8), constrained_layout=True)
    for group, label, style in (
        ("strong_positive", "强正偏置", "-o"),
        ("strong_negative", "强负偏置", "--s"),
    ):
        group_rows = [r for r in rows if r["group"] == group]
        m2 = [next(r for r in group_rows if r["scenario"] == s and r["method"] == "M2") for s in QUANT_ORDER]
        m3 = [next(r for r in group_rows if r["scenario"] == s and r["method"] == "M3") for s in QUANT_ORDER]
        axes[0].plot(xlabels, [a["useful_steps_mean"] for a in m2], linestyle=":", marker="^", color="0.45", label=f"{label} M2")
        axes[0].plot(xlabels, [a["useful_steps_mean"] for a in m3], style, color="0.05", label=f"{label} M3")
        rates = [r["risk_violation_rate"] or 0 for r in m3]
        axes[1].plot(xlabels, rates, style, color="0.05", label=label)
    axes[0].set_ylabel("平均有用校正拍数")
    axes[0].set_xlabel("量化位宽（bit）")
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].set_ylabel("代理风险下界违约比例")
    axes[1].set_xlabel("量化位宽（bit）")
    axes[1].set_ylim(bottom=0)
    axes[1].legend(frameon=False, fontsize=8)
    for ax in axes:
        style_axes(ax)
    fig.savefig(FIG / "fig_quantization.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_drift(summary):
    rows = [r for r in summary if r["experiment"] == "drift" and r["scenario"].startswith("decay_")]
    order = tuple(f"decay_{x:02d}" for x in (0, 5, 10, 20, 35, 50))
    labels = ["0%", "5%", "10%", "20%", "35%", "50%"]
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.8), constrained_layout=True)
    for method, label, style in (
        ("M3", "M3（静态幅值）", "-o"),
        ("M3_rho", "M3-rho（下游机制探索）", "--s"),
    ):
        selected = [next(r for r in rows if r["scenario"] == scenario and r["method"] == method)
                    for scenario in order]
        baseline = [next(r for r in rows if r["scenario"] == scenario and r["method"] == "M2")
                    for scenario in order]
        axes[0].plot(
            labels,
            [a["actual_gain_mean"] - b["actual_gain_mean"] for a, b in zip(selected, baseline)],
            style, color="0.05", label=f"{label} 相对 M2",
        )
        axes[1].plot(
            labels, [r["risk_violation_rate"] or 0 for r in selected],
            style, color="0.05", label=label,
        )
    axes[0].axhline(0, color="0.4", linewidth=.7)
    axes[0].set_ylabel("相对 M2 的累计实际降损增量")
    axes[0].set_xlabel("512 拍累计漂移幅度")
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].set_ylabel("变幅参考下的代理下界违约比例")
    axes[1].set_xlabel("512 拍累计漂移幅度")
    axes[1].set_ylim(bottom=0)
    axes[1].legend(frameon=False, fontsize=8)
    for ax in axes:
        style_axes(ax)
    fig.savefig(FIG / "fig_drift_phase.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

def plot_model_mismatch(summary):
    rows = [r for r in summary if r["experiment"] == "model_mismatch"]
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.9), constrained_layout=True)
    for group, label, style in (
        ("strong_positive", "强正偏置", "-o"),
        ("strong_negative", "强负偏置", "--s"),
    ):
        for method, method_label, method_style in (
            ("M1", "M1", style),
            ("M2", "M2", ":" + style[-1]),
            ("M3", "M3", "-." + style[-1]),
        ):
            chosen = [next(r for r in rows if r["scenario"] == scenario and r["group"] == group and r["method"] == method)
                      for scenario in EPS_ORDER]
            axes[0].plot(
                ["0", "+1", "−1", "+2", "−2", "+5", "−5"],
                [r["actual_gain_mean"] for r in chosen],
                method_style,
                color="0.05" if method == "M3" else "0.4",
                label=f"{label} {method_label}",
            )
    for method, label, style in (
        ("M1_h0", "M1 h0", ":o"),
        ("M1_q95", "M1 q95", "--s"),
        ("M1", "M1", "-^"),
        ("M2", "M2", "-.x"),
        ("M3", "M3", ":D"),
    ):
        chosen = [next(r for r in rows if r["scenario"] == scenario and r["group"] == "health" and r["method"] == method)
                  for scenario in EPS_ORDER]
        axes[1].plot(
            ["0", "+1", "−1", "+2", "−2", "+5", "−5"],
            [r["false_action_trajectories"] / r["n"] for r in chosen],
            style,
            color="0.05" if method in ("M1", "M2", "M3") else "0.45",
            label=label,
        )
    axes[0].set_ylabel("攻击组平均实际降损")
    axes[0].set_xlabel("标称状态矩阵摄动 εA（%）")
    axes[0].legend(frameon=False, fontsize=7, ncol=2)
    axes[1].set_ylabel("健康轨迹至少一次非零动作比例")
    axes[1].set_xlabel("标称状态矩阵摄动 εA（%）")
    axes[1].set_ylim(0, 1)
    axes[1].legend(frameon=False, fontsize=8)
    for ax in axes:
        style_axes(ax)
    fig.savefig(FIG / "fig_model_mismatch.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    configure_font()
    rows = data_rows()
    expected = {"quantization": 216, "drift": 132, "model_mismatch": 252}
    actual = {name: sum(row["experiment"] == name for row in rows) for name in expected}
    if actual != expected:
        raise RuntimeError(f"Incomplete exploration data: {actual}")
    summary, detail = summarize(rows)
    write_csv(TASK / "quantization_summary.csv", ordered_summary(summary, "quantization"))
    write_csv(TASK / "drift_summary.csv", ordered_summary(summary, "drift"))
    write_csv(TASK / "model_mismatch_summary.csv", ordered_summary(summary, "model_mismatch"))
    write_csv(TASK / "trajectory_metrics.csv", detail)
    plot_quantization(summary)
    plot_drift(summary)
    plot_model_mismatch(summary)

    log = read(TASK / "run_log.json") if (TASK / "run_log.json").exists() else []
    registration = read(TASK / "registration.json")
    quant = ordered_summary(summary, "quantization")
    drift = ordered_summary(summary, "drift")
    mismatch = ordered_summary(summary, "model_mismatch")
    cols = [
        ("场景", "scenario"), ("工况", "group"), ("方法", "method"), ("n", "n"),
        ("实际降损均值", "actual_gain_mean"), ("条件改善均值", "conditional_gain_mean"),
        ("方法−M2配对均值", "paired_method_minus_M2_mean"),
        ("配对t区间下限", "paired_method_minus_M2_t95_low"),
        ("配对t区间上限", "paired_method_minus_M2_t95_high"),
        ("负条件改善轨迹", "conditional_negative_trajectories"),
        ("有用拍数均值", "useful_steps_mean"), ("期末有用", "useful_endpoint"),
        ("误动作轨迹", "false_action_trajectories"),
        ("证书检查", "certificate_checks"), ("违约", "risk_violations"),
        ("违约比例", "risk_violation_rate"),
    ]
    parts = [
        "# 双容液位模型边界与失配稳健性探索",
        "",
        "本报告对应预先登记的探索性批次。M0/M1/M2/M3 使用同一条轨迹、同一接收记录和同一组随机种子。M1 使用冻结主门限 5.45758438644748；另以相同点估计提案并行回放 h0=0 和 q95=4.11686632914。样本是配对机制探索，不替代新的独立确认集。",
        "",
        "所有表的实际降损使用真实状态与发布输出，正数表示降低累计损失。条件改善单独按与连续真值滤波器的精确有理数差计算。量化实验中的条件量是连续真值参考代理，模型/漂移实验按各自失配真实模型递推。风险下界违约仅统计有正下界动作；变幅实验中的上游统计证书不适用于真实变幅，M3-rho 仅为下游传播机制探索。",
        "",
        "## 预注册协议与样本",
        "",
        f"- 源码基线提交：{registration['source_commit']}。随机种子基准为 {registration['seed_rule']['base_test_seed']}，按冻结组序号和轨迹编号构造 NumPy SeedSequence。每个工况复用相同编号，工况间共享外生随机流。量化反馈改变后续可信中心，故跨位宽事件前缀可能自然分叉。",
        "- 双容对象冻结参数 Z=2、b_max=0.35 cm、四个查询时刻 127/255/383/511、608 拍仿真、损失窗口 [50,561]。模型 A、B、C、Q、R、P0、W、控制输入及来源哈希在 registration.json。",
        "- 位宽为连续、12、10、8、6、4 bit。量化器是 [-5,5] cm 上端点包含的均匀 2^B 级 mid-rise，最近电平舍入，平局 ties-to-even，越界饱和。发送事件仍由干净量测触发，量化后的载荷进入名义 Monitor 并影响后续中心。",
        "- 漂移扫描的每拍上界 rho=0.35*f/511。正向增强从 +0.35 cm 起步并受同一幅值上限裁剪，故所有正向增强档位都饱和为常值，不能解释为有效的增强漂移试验。可选正弦工况未运行。",
        "- 系统摄动为 A_plant=A_nom*(1+epsilon_A)，对矩阵每个元素按比例缩放。所有算法和事件中心使用标称模型。扰动范围与谱半径逐轨迹写入 CSV。",
        "",
        "## 实验 1：有限位宽量化",
        "",
        "1A 是不依赖滤波模型的真实状态累计降损。有用校正用 M1 的非零发布以及 M2/M3 的实际发布下界阈值 0.000625。1B 是相对未量化连续真参数滤波器均值的条件改善代理；M2/M3 的认证风险下界仍来自连续载荷模型，表中明确按代理外包审计，不称有限位宽定理。",
        "",
        markdown_table(quant, cols),
        "",
        "## 实验 2A/2B：恒定幅值失配及漂移感知传播",
        "",
        "增强曲线与零漂移结果相同，因为正偏置基线已在 +b_max。衰减扫描按 512 拍末端总幅值下降百分比标定。2B 使用精确递推维护每个发送时刻的 Phi 响应，并在方向支撑中扣除 rho 加权残差上界。每个轨迹以最近已通过的方向证书时刻作幅值锚点。M3-rho 的上游似然区间仍由恒定幅值模型产生，故 M3-rho 输出下界是机制敏感性数值，不构成对变幅模型的概率保证。",
        "",
        markdown_table(drift, cols),
        "",
        "## 实验 3：系统矩阵模型失配",
        "",
        "真实物理状态由摄动后的 A_plant 演化。事件中心由标称 Monitor 从上一拍公开历史计算，触发概率仍作用于干净量测。条件真值滤波器使用 A_plant、共享中心、干净连续载荷和静默等效观测方差，协方差与均值均通过有理数递推。全部摄动档的谱半径及名义监视器与实现值最大差见逐轨迹 CSV。",
        "",
        markdown_table(mismatch, cols),
        "",
        "## 计算量与复核",
        "",
        "| 批次 | 轨迹请求数 | 新计算数 | 核时 | 墙钟小时 | 工作进程 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for item in log:
        parts.append(
            f"| {item['experiment']} | {item['requested']} | {item['newly_computed']} | "
            f"{item['cpu_seconds']/3600:.3f} | {item['wall_seconds']/3600:.3f} | {item['workers']} |"
        )
    parts += [
        "",
        "全量逐轨迹明细在 trajectory_metrics.csv；三张汇总表从冻结 JSON 重建。因 h0/q95/M1 共享一次点网格评分，门限分支没有重复执行似然搜索。重建图表的入口为 rebuild_report.py。",
        "",
        "## 解释边界",
        "",
        "- 10–12 bit 是否保持 M3–M2 续航和代理下界，需要结合量化汇总表判断。代理违约率不是量化观测模型下的严格风险保证。",
        "- 漂移下静态 M3 的负条件改善轨迹和认证下界违约显示固定幅值假设的经验失效范围，但样本量和给定噪声种子不提供分布无关漂移半径。",
        "- M3-rho 只放宽下游传播。其上游方向/幅值区间仍来自恒定幅值似然筛选，因此不能把残差扣减后的数值称作变幅攻击证书。",
        "- 参数摄动下的条件风险比较使用精确高斯递推，但失配的似然外包器仍按标称模型运行；观测到的风险违约是该模型边界下的直接诊断。",
        "- 正向增强档位因幅值裁剪而退化为常值，不能用于支持增强漂移结论。"
    ]
    REPORT.write_text("\n".join(parts) + "\n", encoding="utf8", newline="\n")
    print(f"rebuilt {len(rows)} tracks and {len(detail)} method rows")


if __name__ == "__main__":
    main()





