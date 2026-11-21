"""Summarize the frozen Monte Carlo trial without generating samples."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = HERE / "results" / "run_v1"
DIAG = HERE / "results" / "run_v1_diagnostic"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z / den * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return center - half, center + half


def percent_interval(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{100*k/n:.3f}% [{100*lo:.3f}, {100*hi:.3f}]"


def drift_constant(model: dict[str, float], b_ref: float, delta_ref: float = 0.25) -> tuple[float, float, float]:
    A, Q, R, Z = (model[k] for k in ("A", "Q", "R", "Z"))
    P0 = model["P0"]
    r0 = R + 1 / Z
    Pmax = max(P0, A * A * r0 + Q)
    rho = abs(A) * max(R / (Q + R), r0 / (Q + r0))
    gmax = Pmax / (Pmax + R)
    B = gmax * b_ref / (1 - rho)
    Vmin = 1 / Z + Q + R
    Vmax = 1 / Z + A * A * r0 + Q + R
    kappa = (
        A * A / (2 * Vmax * math.sqrt(Z * Vmax))
        * math.exp(-(A * A * B * B + delta_ref * delta_ref) / (2 * Vmin))
    )
    return rho, B, kappa


def main() -> None:
    original = json.loads((RUN / "summary.json").read_text(encoding="utf8"))
    diagnostic = json.loads((DIAG / "summary.json").read_text(encoding="utf8"))
    protocol = json.loads((HERE / "protocol.json").read_text(encoding="utf8"))
    runtime = json.loads((HERE / "execution_runtime.json").read_text(encoding="utf8"))
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf8"))
    dmanifest = json.loads((DIAG / "manifest.json").read_text(encoding="utf8"))
    if len(original) != 8 or len(diagnostic) != 8:
        raise AssertionError("Expected all eight frozen model/attack settings")
    if manifest["summary_sha256"] != sha(RUN / "summary.json"):
        raise AssertionError("Primary result hash mismatch")
    if dmanifest["summary_sha256"] != sha(DIAG / "summary.json"):
        raise AssertionError("Diagnostic result hash mismatch")
    for a, b in zip(original, diagnostic):
        for key in ("model", "attack_bound", "attack", "attack_alarm_rate", "average_audit_score_attack",
                    "average_predicted_audit_drift_attack", "score_minus_predicted_drift_attack"):
            if a[key] != b[key]:
                raise AssertionError(f"The diagnostic rerun changed sampled result field {key}")
        for key in ("clean", "monitor", "hard", "soft"):
            if a["mse_metrics"][key] != b["mse_metrics"][key]:
                raise AssertionError(f"The diagnostic rerun changed {key} MSE")

    n = protocol["episodes"]
    lines: list[str] = []
    lines.extend([
        "# 固定协议下的序贯审计与恢复试验结果",
        "",
        "本报告只分析冻结试验输出，不生成随机样本。8 个设置各运行 20,000 个独立 episode，共 160,000 个 episode；每个 episode 从攻击起点起计 513 个估计时刻，并审计随后 512 个可信事件位。攻击在整个计分窗口持续。",
        "",
        f"冻结连续代码 SHA-256：`{manifest['script_sha256']}`；协议 SHA-256：`{manifest['protocol_sha256']}`。运行环境为 Python {runtime['actual_runtime']['python'].split()[0]}、NumPy {runtime['actual_runtime']['numpy']}、SciPy {runtime['actual_runtime']['scipy']}。冻结记录原本指定 Python 3.14.9/NumPy 2.5.4，但该环境离线不可用；本次保留了原代码和协议哈希，并将实际运行环境单独记录。",
        "",
        "## 误报、报警与 monitor 损伤",
        "",
        "阈值为 34.3355，对应固定 512 事件时域的 Azuma 误报上界 1%。下表的误报率和检出率为 episode 比例，括号中是 95% Wilson 区间；检出延迟只在报警 episode 中计算。MSE 差值以 1e-3 为单位，是相对于共用外生噪声、但允许事件历史自然分叉的健康滤波器。",
        "",
        "| 模型 | 攻击幅值上界 | 攻击策略 | 健康误报率 [95% CI] | 攻击报警率 [95% CI] | 报警 episode 平均延迟 | Monitor MSE 增量 ×10⁻³ (SE) |",
        "|---|---:|---|---:|---:|---:|---:|",
    ])
    for r in original:
        k0 = round(r["healthy_false_alarm_rate"] * n)
        k1 = round(r["attack_alarm_rate"] * n)
        mse = r["mse_metrics"]["monitor"]
        lines.append(
            f"| {r['model']} | {r['attack_bound']:.2f} | {r['attack']} | {percent_interval(k0,n)} "
            f"({k0}/{n}) | {percent_interval(k1,n)} ({k1}/{n}) | "
            f"{r['attack_detection_delay_mean_conditional']:.1f} | "
            f"{1e3*mse['paired_excess_vs_clean']:.3f} ({1e3*mse['paired_excess_se']:.3f}) |"
        )

    lines.extend([
        "",
        "健康误报率为 0.025%–0.085%，明显低于 1% 名义上界。检测功效也很低：除 U1、正向持续攻击、幅值上界 0.25 外，攻击报警率与健康误报率接近；即使该最强设置也只报出 90/20,000 个 episode（0.45%）。条件平均延迟约 442–473 拍，且只基于极少数报警样本，不能当作通常检测延迟。",
        "",
        "所有攻击设置的平均预测审计漂移均为正；幅值增大时总体上升。跨 episode 的“实际累计审计分数 − 预测累计漂移”残差与零相容：",
        "",
        "| 模型 | 幅值 | 策略 | 残差均值 | SE | 残差 / SE |",
        "|---|---:|---|---:|---:|---:|",
    ])
    max_z = 0.0
    for r in diagnostic:
        se = r["score_minus_predicted_drift_attack_se"]
        z = r["score_minus_predicted_drift_attack"] / se
        max_z = max(max_z, abs(z))
        lines.append(
            f"| {r['model']} | {r['attack_bound']:.2f} | {r['attack']} | "
            f"{r['score_minus_predicted_drift_attack']:.4f} | {se:.4f} | {z:.2f} |"
        )
    lines.extend([
        "",
        f"最大绝对标准化残差为 {max_z:.2f}。这次诊断重跑使用相同主种子，仅增加跨 episode 标准误输出；它不是独立复现实验。",
        "",
        "仓库已有的后置相位单拍反射试验也发现，小步长下事件-only TV 约为 3.3e-5（S1），联合载荷/相位/事件 TV 约为 3.7e-5；冻结 test 上事件检测未超过误报基线。这里的持续攻击试验把该结论推进到序贯风险审计：期望漂移为正，但在 512 拍内仍太弱。两项结果共同说明总体可辨识性不能替代可用检测功效。",
        "",
        "## 恢复输出的风险",
        "",
        "S1 中硬回滚、固定 50/50 融合与 monitor 的 MSE 几乎重合，因为 512 拍内报警率只有 0.025%–0.05%。它们没有降低测得的攻击损伤。S1 健康情况下的恢复切换代价很小，主要因为误报极少；这不适用于 U1 的过期检查点。",
        "",
    ])
    s1_hard_diffs = [r["mse_metrics"]["hard"]["paired_excess_vs_clean"] for r in original if r["model"] == "S1"]
    s1_soft_diffs = [r["mse_metrics"]["soft"]["paired_excess_vs_clean"] for r in original if r["model"] == "S1"]
    s1_healthy_hard = [r["mse_metrics"]["healthy_hard"]["paired_excess_vs_clean"] for r in original if r["model"] == "S1"]
    s1_healthy_soft = [r["mse_metrics"]["healthy_soft"]["paired_excess_vs_clean"] for r in original if r["model"] == "S1"]
    lines.append(
        f"S1 攻击运行中，硬回滚相对健康基线的 MSE 增量为 {min(s1_hard_diffs):.2e}–{max(s1_hard_diffs):.2e}，"
        f"固定软融合为 {min(s1_soft_diffs):.2e}–{max(s1_soft_diffs):.2e}，与 monitor 基本相同，没有降低攻击损伤。"
        f"健康运行下，硬回滚代价为 {min(s1_healthy_hard):.2e}–{max(s1_healthy_hard):.2e}，"
        f"软融合代价为 {min(s1_healthy_soft):.2e}–{max(s1_healthy_soft):.2e}。"
    )
    u1 = [r for r in original if r["model"] == "U1"]
    u1_hard = [r["mse_metrics"]["hard"]["mse"] for r in u1]
    u1_soft = [r["mse_metrics"]["soft"]["mse"] for r in u1]
    u1_monitor = [r["mse_metrics"]["monitor"]["mse"] for r in u1]
    lines.extend([
        "",
        f"U1 中 episode 起点检查点在不稳定系统上长期开环外推，使硬回滚平均 MSE 达 {min(u1_hard):.2e}–{max(u1_hard):.2e}，"
        f"固定软融合达 {min(u1_soft):.2e}–{max(u1_soft):.2e}；monitor MSE 只有 {min(u1_monitor):.3f}–{max(u1_monitor):.3f}。"
        "这些巨大值由稀少报警触发后放弃当前估计、切换到过期锚点所致。该结果说明检查点新鲜度是恢复算法的硬约束；它不否定带新鲜认证锚点的其他策略，但当前回滚方案在 U1 不可用。",
        "",
        "## 偏差能量界的数值常数",
        "",
        "旧公式检查只用攻击幅值上界 0.10；本轮协议还测试 0.25，因此按同一保守定理重新计算 b_ref=0.10、0.25 的界，令 delta_ref=0.25 覆盖两个量化步长。",
        "表中末拍偏差最大值只取各 episode 最后时刻的偏差绝对值，不是全轨迹最大值，也不替代理论半径证明。",
        "",
        "| 模型 | b_ref | rho | B | 末拍偏差最大值 | kappa |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for model in protocol["models"]:
        for b in (0.10, 0.25):
            rho, B, kappa = drift_constant(model, b)
            observed = max(r["maximum_abs_analysis_bias"] for r in original
                           if r["model"] == model["id"] and r["attack_bound"] == b)
            if observed > B + 1e-12:
                raise AssertionError(f"Observed bias exceeds the declared radius for {model['id']} b={b}")
            lines.append(f"| {model['id']} | {b:.2f} | {rho:.5f} | {B:.4g} | {observed:.4g} | {kappa:.4g} |")
    lines.extend([
        "",
        "这补上了原公式检查的幅值覆盖缺口：0.25 设置不能沿用 b_ref=0.10 的常数，必须按上表重算。S1 的界仍为正但保守；U1、0.25 的 kappa 约为 5e-16，停止时能量上界在数值上没有工程意义。理论的定性正漂移仍成立，定量报警/恢复性能则受限。",
        "",
        "## 结论和下一步",
        "",
        "这次没有验证出可用的恢复算法。后置随机相位的条件漂移恒等式与样本均值相符，但在当前 S1/U1 参数、量化步长、512 拍窗口及 1% 固定时域阈值下，事件审计几乎不报警；恢复因此没有收益。过期检查点在 U1 造成灾难性风险。",
        "",
        "继续推进应先解决两个方法问题：一是提高受约束审计的有效信息利用率或延长有理论误报控制的观测时域；二是设计并分析有新鲜度上限的可信检查点策略。每种方案都需在同一攻击权限、健康 MSE 和通信预算下与当前基线比较。不能把这轮的正漂移定理当作工程成功证据。",
        "",
        "协议时序和统计口径见 [trial_interpretation.md](../../trial_interpretation.md)。实际运行环境差异见 [execution_runtime.json](../../execution_runtime.json)，随机样本汇总见 [summary.json](summary.json)。",
    ])
    report = "\n".join(lines) + "\n"
    (RUN / "results_analysis.md").write_text(report, encoding="utf8", newline="\n")
    print(json.dumps({"status": "PASS", "cases": len(original), "max_drift_residual_se": max_z,
                      "report": str(RUN / "results_analysis.md")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
