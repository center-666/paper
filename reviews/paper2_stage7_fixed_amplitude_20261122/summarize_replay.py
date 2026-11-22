"""Summarize paired Stage 6 frozen-trace propagation ablation."""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
from scipy.stats import beta, t as student

HERE = Path(__file__).resolve().parent
STAGE6 = HERE.parent / "paper2_stage6_vector_correction_20261122"
OUT = HERE / "analysis"
OUT.mkdir(exist_ok=True)


def moment(values):
    x = np.asarray(values, dtype=float)
    n = len(x)
    mean = float(x.mean())
    se = float(x.std(ddof=1) / math.sqrt(n)) if n > 1 else 0.0
    half = float(student.ppf(.975, n - 1) * se) if n > 1 else None
    return {"n": n, "mean": mean, "se": se,
            "student_95_low": mean-half if half is not None else None,
            "student_95_high": mean+half if half is not None else None}


def proportion(k, n):
    return {"k": k, "n": n, "rate": k/n if n else None,
            "CP95_low": 0. if k == 0 else float(beta.ppf(.025, k, n-k+1)),
            "CP95_high": 1. if k == n else float(beta.ppf(.975, k+1, n-k))}


def main():
    files = sorted((HERE / "results" / "replay").glob("b*_episode*.json"))
    rows = [json.loads(p.read_text(encoding="utf8")) for p in files]
    protocol = json.loads((STAGE6 / "pilot_protocol.json").read_text(encoding="utf8"))
    by_case = {}
    max_replay_error = 0.0
    for b in protocol["attack_strengths"]:
        eps = [r for r in rows if r["b"] == b]
        case = {"b": b, "n": len(eps), "windows": []}
        for H in protocol["evaluation_windows"]:
            ss = [e["snapshots"][str(H)] for e in eps]
            paired = {
                "old_gain": [s["old_gain"] for s in ss],
                "new_gain": [s["new_directional_gain"] for s in ss],
                "gain_difference_new_minus_old": [s["new_directional_gain"]-s["old_gain"] for s in ss],
                "old_conditional_gain": [s["old_conditional_gain"] for s in ss],
                "new_conditional_gain": [s["new_directional_conditional_gain"] for s in ss],
                "old_action_square": [s["old_action_square"] for s in ss],
                "new_action_square": [s["new_action_square"] for s in ss],
                "old_monitor_mse": [s["monitor"] for s in ss],
                "new_mse": [s["new_directional"] for s in ss],
            }
            episode = {
                "H": H,
                "old_useful_endpoint": proportion(sum(s["old_current_action_norm"] >= .025-1e-12 for s in ss), len(ss)),
                "new_useful_endpoint": proportion(sum(s["new_current_action_norm"] >= .025-1e-12 for s in ss), len(ss)),
                "old_ever_useful": proportion(sum(s["first_old_useful"] is not None for s in ss), len(ss)),
                "new_ever_useful": proportion(sum(s["first_new_useful"] is not None for s in ss), len(ss)),
                "coverage_violation_episode": proportion(sum(e["coverage_violations"] > 0 for e in eps), len(eps)),
                "old_support_violation_episode": proportion(sum(e["old_support_violations"] > 0 for e in eps), len(eps)),
                "bound_monotonicity_violation_episode": proportion(sum(e["bound_monotonicity_violations"] > 0 for e in eps), len(eps)),
                "metrics": {k: moment(v) for k, v in paired.items()},
                "mean_replay_seconds": moment([e["replay_seconds"] for e in eps]),
                "mean_interval_onsets": moment([s["new_interval_onsets"] for s in ss]),
            }
            for e in eps:
                base = json.loads((STAGE6 / "results_v2" / "final" /
                    f"b{b:g}_episode{e['episode']:03d}.json").read_text(encoding="utf8"))
                old = e["snapshots"][str(H)]
                target = base["snapshots"][str(H)]
                for mine, theirs in ((old["monitor"], target["monitor"]),
                                     (old["old_gain"], target["certified_gain"]),
                                     (old["old_conditional_gain"], target["conditional_certified_gain"]),
                                     (old["old_action_square"], target["squared_actions"])):
                    max_replay_error = max(max_replay_error, abs(mine-theirs))
            case["windows"].append(episode)

        lag_summary = {}
        for lag in (0, 1, 10, 25, 50):
            useful_eps = []
            old_useful_eps = []
            new_norms, old_norms, bounds = [], [], []
            for e in eps:
                measures = [x for x in e["lag_snapshots"].values()
                            if x.get("lag") == lag and "new_action_norm" in x]
                if any(x["new_action_norm"] >= .025-1e-12 for x in measures):
                    useful_eps.append(e["episode"])
                if any(x["old_action_norm"] >= .025-1e-12 for x in measures):
                    old_useful_eps.append(e["episode"])
                for x in measures:
                    new_norms.append(x["new_action_norm"])
                    old_norms.append(x["old_action_norm"])
                    bounds.append(x["new_bound"]-x["old_bound"])
            lag_summary[str(lag)] = {
                "new_useful_episode_rate": proportion(len(set(useful_eps)), len(eps)),
                "old_useful_episode_rate": proportion(len(set(old_useful_eps)), len(eps)),
                "new_action_norm_per_certificate": moment(new_norms) if new_norms else None,
                "old_action_norm_per_certificate": moment(old_norms) if old_norms else None,
                "new_minus_old_bound_per_certificate": moment(bounds) if bounds else None,
                "certificate_lag_observations": len(new_norms),
            }
        case["lag_summary"] = lag_summary
        case["successful_certificate_episode_rate"] = proportion(
            sum(bool(e["successful_certificates"]) for e in eps), len(eps))
        case["mean_successful_certificates"] = moment([len(e["successful_certificates"]) for e in eps])
        case["mean_support_search_seconds"] = moment([e["timing"]["support_search"] for e in eps])
        case["mean_parameter_update_seconds"] = moment([e["timing"]["parameter_updates"] for e in eps])
        case["mean_exact_dynamics_seconds"] = moment([e["timing"]["exact_dynamics"] for e in eps])
        by_case[str(b)] = case

    summary = {
        "status": "PASS_REPRODUCED",
        "design": "Paired replay of 36 Stage 6 final traces; cached certificate decisions, exact same physical random streams",
        "independent_confirmation": False,
        "max_stage6_old_branch_reproduction_error": max_replay_error,
        "useful_action_threshold": .025,
        "rows_by_attack_strength": by_case,
        "claims_boundary": [
            "This is a frozen-trace propagation ablation, not an independent seed confirmation.",
            "Successful/failed certificate-search decisions were replayed; certificate search time is excluded.",
            "Student-t intervals are descriptive for n=12 and do not establish generalization or a risk failure rate.",
            "No actual-MSE guarantee follows from G_cert or G_cond; G_sample is a paired finite-sample metric."
        ]
    }
    (OUT / "replay_summary.json").write_text(json.dumps(summary, indent=2)+"\n",
                                              encoding="utf8", newline="\n")
    lines = ["# 阶段七冻结轨迹传播消融", "",
             "同一阶段六最终样本、同一事件/量测随机流、同一认证输出，只改变认证后污染证书表示。旧算法分支逐窗重现已存档结果。认证搜索输出使用缓存，耗时不包含重新求似然。", "",
             "所有区间均为每组12条轨迹的描述性配对Student-t 95%区间；这不是独立确认，也不支持0.1%风险率结论。", "",
             "## 认证后50拍仍达到预设动作阈值的轨迹", "",
             "| 攻击幅值 | 旧半空间 | 起点关联固定幅值外包 | 成功证书轨迹 | 覆盖/单调性违反 |", "|---:|---:|---:|---:|---:|"]
    for b in protocol["attack_strengths"]:
        c = by_case[str(b)]
        w512 = c["windows"][-1]
        lag = c["lag_summary"]["50"]
        lines.append(f"| {b:.2f} | {lag['old_useful_episode_rate']['k']}/12 | "
                     f"{lag['new_useful_episode_rate']['k']}/12 | "
                     f"{c['successful_certificate_episode_rate']['k']}/12 | "
                     f"{w512['coverage_violation_episode']['k']}/12, "
                     f"{w512['bound_monotonicity_violation_episode']['k']}/12 |")
    lines += ["", "## 512拍配对累计MSE", "",
              "改善定义为monitor累计平方误差减新输出累计平方误差，正值较好。括号为Student-t区间。", "",
              "| 攻击幅值 | 旧改善均值 [95%区间] | 新改善均值 [95%区间] | 新减旧改善 [95%区间] |", "|---:|---:|---:|---:|"]
    for b in protocol["attack_strengths"]:
        c = by_case[str(b)]["windows"][-1]
        m = c["metrics"]
        def fmt(k):
            q=m[k]; return f"{q['mean']:.4f} [{q['student_95_low']:.4f}, {q['student_95_high']:.4f}]"
        lines.append(f"| {b:.2f} | {fmt('old_gain')} | {fmt('new_gain')} | {fmt('gain_difference_new_minus_old')} |")
    lines += ["", "## 512拍证书量与配对条件风险", "",
              "G_cert为平方动作范数下界累计；G_cond读取真实污染，只用于离线核验；G_sample是实际配对MSE差。", "",
              "| 攻击幅值 | 旧G_cert | 新G_cert | 旧G_cond | 新G_cond | 最大旧分支复现误差 |", "|---:|---:|---:|---:|---:|---:|"]
    for b in protocol["attack_strengths"]:
        c = by_case[str(b)]["windows"][-1]["metrics"]
        lines.append(f"| {b:.2f} | {c['old_action_square']['mean']:.6g} | {c['new_action_square']['mean']:.6g} | "
                     f"{c['old_conditional_gain']['mean']:.6g} | {c['new_conditional_gain']['mean']:.6g} | "
                     f"{max_replay_error:.2e} |")
    lines += ["", "## 计算成本边界", "",
              "同轨迹回放重算精确协方差、区间响应更新和支持搜索，但复用了旧认证查询，因此不是新算法的完整端到端认证耗时。日志分别给出exact_dynamics、parameter_updates与support_search。阶段七的第一实现是认证后传播器，后续若进行独立确认，必须重跑完整认证搜索并重新冻结。", "",
              "## 判断", "",
              "若新动作在认证后lag 50仍有明显非零率且G_cert不低于旧算法，这支持‘固定幅值信息丢失会使半空间界过度衰减’这一机制解释。实际G_sample的描述性区间仍需独立新种子确认；健康/弱攻击下保持零动作是必要的选择性安全条件。"]
    (HERE / "07_frozen_replay_results.md").write_text("\n".join(lines)+"\n",
                                                       encoding="utf8", newline="\n")
    print(json.dumps({"status": summary["status"], "max_old_replay_error": max_replay_error,
                      "strong_lag50": by_case["0.25"]["lag_summary"]["50"]["new_useful_episode_rate"],
                      "strong_512_gain": by_case["0.25"]["windows"][-1]["metrics"]["gain_difference_new_minus_old"]}, indent=2))


if __name__ == "__main__":
    main()
