"""Read immutable G2 v3 artifacts; no simulation or online algorithm inputs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[3]
REVIEW = ROOT / "reviews/g2_closeout_errata"
SOURCE = ROOT / "simulation/g2_runs/2026-11-13_g2_replay_effectiveness_v3"
DEFAULT_ID = "2026-11-13_g2_readonly_erratum_r01"
FORCED = ("fixed_lag8", "random_history", "nearest_current_sender", "risk_greedy_forced_fallback")
NATURAL = ("risk_greedy_natural_budget_0.25", "risk_greedy_natural_budget_1.0")
METHODS = ("raw_yang_no_cap", "cap_only", "zhou_random_protection", "spatial_hard", "episode_prefix_mean", "energy_cusum")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes():
    return {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p)
            for p in sorted(SOURCE.rglob("*")) if p.is_file()}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def mean_ci(values):
    values = np.asarray(values, dtype=float)
    if not len(values):
        return {"n": 0, "mean": None, "low": None, "high": None}
    m = float(values.mean())
    half = float(stats.t.ppf(.975, len(values)-1) * values.std(ddof=1) / np.sqrt(len(values))) if len(values) > 1 else None
    return {"n": len(values), "mean": m, "low": m-half if half is not None else None,
            "high": m+half if half is not None else None}


def recovery(error, clean, origin, search_start, streak=5, tolerance=.1):
    """Earliest 5-state tolerance return, not permanent recovery; state indices."""
    for t in range(max(origin, search_start), len(error)-streak+1):
        if np.all(np.sqrt(error[t:t+streak]) <= np.sqrt(clean[t:t+streak]) + tolerance):
            return t-origin, False
    return len(error)-origin, True


def add_stats(row, label, values):
    row.update({label + "_" + k: v for k, v in mean_ci(values).items()})


def cell(row, prefix, digits=6):
    if row[prefix + "_mean"] is None:
        return "N/A"
    return f"{row[prefix+'_mean']:.{digits}f} [{row[prefix+'_low']:.{digits}f}, {row[prefix+'_high']:.{digits}f}]"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=DEFAULT_ID)
    args = parser.parse_args()
    if not args.run_id or Path(args.run_id).name != args.run_id:
        raise ValueError("Run ID must be one directory name")
    out = REVIEW / "results" / args.run_id
    out.mkdir(parents=True, exist_ok=False)
    before = hashes()
    write_json(out / "source_hashes_before.json", before)
    completion = json.loads((SOURCE / "completion.json").read_text(encoding="utf-8"))
    assert completion["completed"]
    for name, expected in completion["output_hashes"].items():
        assert sha(SOURCE / name) == expected, name
    config = json.loads((SOURCE / "config.json").read_text(encoding="utf-8"))
    lo, end, T = config["attack"]["start"], config["attack"]["end_inclusive"], config["T"]
    state_slice = slice(lo+1, end+2)
    window = end-lo+1
    metrics = {(r["selector"], r["method"], int(r["seed"])): r
               for r in read_csv(SOURCE / "per_seed_metrics.csv")}
    timing = {(r["selector"], r["method"], int(r["seed"])): r
              for r in read_csv(SOURCE / "detection_timing_per_seed.csv")}
    with np.load(SOURCE / "test_inputs.npz") as inputs:
        seeds = inputs["seeds"].astype(int)
        schedule = inputs["schedule"].astype(bool)
    sender = config["attack"]["sender"]
    opportunities = schedule[:, lo:end+1, sender].sum(axis=1)
    assert len(seeds) == 48 and np.all(opportunities == 14)
    per_seed, natural_summary, decomposition, excess_table = [], [], [], []
    with np.load(SOURCE / "mse_timeline_per_seed.npz") as data:
        assert np.array_equal(seeds, data["seeds"])
        for selector in FORCED + NATURAL:
            for method in METHODS:
                key = selector + "__" + method
                err = data[key + "__receiver_error_sq"]
                clean = data[key + "__receiver_clean_error_sq"]
                network = data[key + "__network_error_sq"]
                net_clean = data[key + "__network_clean_error_sq"]
                alarm = data[key + "__target_alarm"].astype(bool)
                injected = data[key + "__target_injected"].astype(bool)
                assert err.shape == clean.shape == (48, T+1)
                assert alarm.shape == injected.shape == (48, T)
                delta = (err[:, state_slice]-clean[:, state_slice]).mean(axis=1)
                network_delta = (network[:, state_slice]-net_clean[:, state_slice]).mean(axis=1)
                row = {"selector": selector, "method": method}
                add_stats(row, "receiver_excess", delta)
                add_stats(row, "actual_receiver_mse", err[:, state_slice].mean(axis=1))
                excess_table.append(row)
                grouped = []
                for i, seed in enumerate(seeds):
                    old = metrics[(selector, method, int(seed))]
                    record = timing[(selector, method, int(seed))]
                    assert np.isclose(delta[i], float(old["receiver_paired_excess_mse"]), rtol=1e-11, atol=1e-12)
                    attacked_times = np.flatnonzero(injected[i])
                    assert np.all((attacked_times >= lo) & (attacked_times <= end))
                    assert len(attacked_times) == int(old["replacements"])
                    attacked = len(attacked_times) > 0
                    first = int(attacked_times[0]) if attacked else None
                    last = int(attacked_times[-1]) if attacked else None
                    following = np.flatnonzero(schedule[i, last+1:, sender]) if attacked else []
                    exit_time = last+1+int(following[0]) if len(following) else None
                    if attacked:
                        assert first == int(record["first_replacement_time"])
                        assert last == int(record["last_replacement_time"])
                        assert exit_time == int(record["cache_exit_receive_time"])
                    hits = np.flatnonzero(alarm[i, first:]) + first if attacked else np.asarray([], int)
                    first_alarm = int(hits[0]) if len(hits) else None
                    r = {"selector": selector, "method": method, "seed": int(seed),
                         "attacked": attacked, "opportunities": int(opportunities[i]),
                         "replacements": len(attacked_times), "first_replacement": first,
                         "last_replacement": last, "cache_exit_receive": exit_time,
                         "receiver_excess_mse": float(delta[i]), "network_excess_mse": float(network_delta[i]),
                         "cumulative_receiver_excess": float(delta[i]*window),
                         "cumulative_excess_per_opportunity": float(delta[i]*window/opportunities[i]),
                         "alarm_any_registered_interval": bool(alarm[i, lo:end+1].any()),
                         "alarm_any_after_registered_interval": bool(alarm[i, end+1:].any()),
                         "alarm_any_horizon": bool(alarm[i].any()),
                         "alarm_before_first_attack": bool(alarm[i, :first].any()) if attacked else None,
                         "alarm_after_first_within_registered_interval": bool(alarm[i, first:end+1].any()) if attacked else None,
                         "alarm_during_actual_replacement_span": bool(alarm[i, first:last+1].any()) if attacked else None,
                         "first_alarm_after_first_attack": first_alarm,
                         "first_post_attack_alarm_only_after_interval": first_alarm > end if first_alarm is not None else None,
                         "alarm_after_first_any_horizon": bool(len(hits)) if attacked else None,
                         "first_post_attack_alarm_delay": first_alarm-first if first_alarm is not None else None,
                         "legacy_recovery_all_seed_value": int(old["recovery_duration"])}
                    for name, origin, start in (
                        ("legacy_conditional", last+1 if attacked else None, end+2),
                        ("last_update_return", last+1 if attacked else None, last+1 if attacked else None),
                        ("after_last_update_return", last+2 if attacked else None, last+2 if attacked else None),
                        ("cache_exit_return", exit_time+1 if exit_time is not None else None, exit_time+1 if exit_time is not None else None)):
                        duration, censored = recovery(err[i], clean[i], origin, start) if origin is not None else (None, None)
                        r[name+"_steps"] = duration
                        r[name+"_right_censored"] = censored
                    if attacked:
                        assert r["legacy_conditional_steps"] == int(old["recovery_duration"])
                    else:
                        assert np.max(np.abs(err[i]-clean[i])) < 1e-10
                    grouped.append(r)
                    per_seed.append(r)
                if selector in NATURAL:
                    active = [r for r in grouped if r["attacked"]]
                    inactive = [r for r in grouped if not r["attacked"]]
                    s = {"selector": selector, "method": method, "seed_count": len(grouped),
                         "attacked_seed_count": len(active), "unattacked_seed_count": len(inactive),
                         "total_opportunities": int(opportunities.sum()),
                         "total_replacements": sum(r["replacements"] for r in grouped),
                         "cumulative_excess_per_all_opportunities": sum(r["cumulative_receiver_excess"] for r in grouped)/opportunities.sum(),
                         "cumulative_excess_per_actual_replacement": sum(r["cumulative_receiver_excess"] for r in grouped)/sum(r["replacements"] for r in grouped),
                         "joint_attacked_and_eventual_alarm_over_all_seeds": sum(bool(r["alarm_after_first_any_horizon"]) for r in active)/len(grouped)}
                    for label, rows in (("all", grouped), ("attacked", active), ("unattacked", inactive)):
                        for field in ("receiver_excess_mse", "network_excess_mse"):
                            add_stats(s, label+"_"+field, [r[field] for r in rows])
                    for field in ("alarm_before_first_attack", "alarm_after_first_within_registered_interval",
                                  "alarm_during_actual_replacement_span", "alarm_any_after_registered_interval",
                                  "first_post_attack_alarm_only_after_interval", "alarm_after_first_any_horizon"):
                        count = sum(bool(r[field]) for r in active)
                        ci = stats.binomtest(count, len(active)).proportion_ci(method="wilson")
                        s["attacked_"+field+"_count"] = count
                        s["attacked_"+field+"_rate"] = count/len(active)
                        s["attacked_"+field+"_wilson_low"] = float(ci.low)
                        s["attacked_"+field+"_wilson_high"] = float(ci.high)
                    for field in ("alarm_any_registered_interval", "alarm_any_after_registered_interval", "alarm_any_horizon"):
                        s["unattacked_"+field+"_count"] = sum(bool(r[field]) for r in inactive)
                    add_stats(s, "legacy_all_seed_recovery", [r["legacy_recovery_all_seed_value"] for r in grouped])
                    for field in ("legacy_conditional", "last_update_return", "after_last_update_return", "cache_exit_return"):
                        add_stats(s, field, [r[field+"_steps"] for r in active])
                        s[field+"_censored_count"] = sum(r[field+"_right_censored"] for r in active)
                    natural_summary.append(s)
            for left, right in (("cap_only", "raw_yang_no_cap"), ("spatial_hard", "cap_only"),
                                ("zhou_random_protection", "cap_only"), ("episode_prefix_mean", "cap_only"),
                                ("energy_cusum", "cap_only")):
                row = {"selector": selector, "left": left, "right": right, "difference_sign": "left_minus_right"}
                for scope in ("receiver", "network"):
                    def vector(method, clean=False):
                        suffix = "__" + scope + ("_clean_error_sq" if clean else "_error_sq")
                        return data[selector+"__"+method+suffix][:, state_slice].mean(axis=1)
                    difference = vector(left)-vector(right)
                    add_stats(row, scope+"_actual_mse_difference", difference)
                    add_stats(row, scope+"_excess_mse_difference", difference-(vector(left, True)-vector(right, True)))
                decomposition.append(row)
    write_csv(out / "per_seed_reanalysis.csv", per_seed)
    write_csv(out / "natural_conditional_summary.csv", natural_summary)
    write_csv(out / "paired_cap_decomposition.csv", decomposition)
    write_csv(out / "all_policy_mse_summary.csv", excess_table)
    source_pilot = json.loads((SOURCE / "sample_size_pilot.json").read_text(encoding="utf-8"))
    assert source_pilot["approx_n_for_80pct_power_at_1pct_relative_difference"] == 745798149989
    config_out = {"analysis_run_id": args.run_id, "source_run_id": completion["run_id"],
                  "simulation_executed": False, "independent_unit": "paired_seed",
                  "attack_packet_indices_inclusive": [lo, end], "attack_state_indices_inclusive": [lo+1, end+1],
                  "alarm_last_index": T-1, "last_state_index": T,
                  "confidence_intervals": "descriptive Student t across seeds; Wilson for binomial counts; unadjusted, not causal",
                  "recovery_tolerance_rmse_norm": .1, "recovery_consecutive_states": 5,
                  "no_attack_recovery": None, "power_number_withdrawn_for_method_comparison": 745798149989,
                  "new_sample_size_estimate": None}
    write_json(out / "analysis_config.json", config_out)
    report = ["# G2结项统计勘误：仅重析原v3数据", "",
              f"分析 Run ID：`{args.run_id}`。原始证据：提交 `031d26eaf996b3583b2b2647b54702551466e20a`，`{completion['run_id']}`。本次不运行仿真、不更改冻结计划、原始结果、已验收报告、G1-R或算法。", "",
              "## 1. 结论与适用范围", "",
              "**EXPERIMENTAL：合法Replay威胁成立；现有强基线尚未被证明失效；G2结项，当前不支持新防御论文立项。** 以下修正统计解释，不撤销已验收的闭环损伤证据。固定外生发送日程中的估计反馈已闭环；Send-on-Delta发送日程反馈没有在本轮验证。", "",
              "MSE是二维状态误差平方范数，未除以2；网络MSE是五节点平均。攻击发生在包索引200–249，对应被更新状态201–250；报警索引0–399，状态索引0–400。独立单位为seed，时间步、包和episode不作为独立样本。均值区间为未作多重校正的95% Student-t描述区间；受攻条件样本仅9个，不作确认性推断。", "",
              "## 2. 自然预算：无替换和受攻seed必须分开", "",
              "两种自然预算的各方法均只有9/48 seed实际替换过包，其余39/48无替换。18.75%=9/48是有攻击且随后存在报警的联合比例（对有报警的方法），不是条件检出率。无攻击seed恢复为N/A，不能计作检出失败或真实零恢复。按是否受攻击条件化是策略选择后的描述，跨方法条件集合不应被视为随机分组。", "",
              "每机会效果采用所有seed攻击状态窗口累计超额平方误差之和/全部合法发送机会数；未替换机会也保留。每次替换归一化另报，二者不是可分离的单包因果效应。", "",
              "|预算/方法|实际替换seed|替换总数/总机会|无条件超额MSE|受攻条件超额MSE|每机会累计超额|每次替换累计超额|",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for s in natural_summary:
        if s["method"] in ("raw_yang_no_cap", "spatial_hard", "zhou_random_protection"):
            budget = s["selector"].split("_")[-1]
            report.append(f"|{budget}/{s['method']}|{s['attacked_seed_count']}/48|{s['total_replacements']}/{s['total_opportunities']}|{cell(s, 'all_receiver_excess_mse')}|{cell(s, 'attacked_receiver_excess_mse')}|{s['cumulative_excess_per_all_opportunities']:.6f}|{s['cumulative_excess_per_actual_replacement']:.6f}|")
    report += ["", "## 3. 报警时段与因果归因", "",
               "下表均以9个实际受攻seed为分母。‘区间内’从各seed首次实际替换开始，至249；‘区间后任意’为250–399；两类可重叠。‘仅迟到首警’指首次替换之后的首个报警落在250以后；并不要求攻击前从未报警。完整记录另保留实际首次至末次替换跨度内报警及攻击前报警。", "",
               "|预算/方法|区间内|区间后任意|仅迟到首警|首次替换后任意|攻击前已有报警|",
               "|---|---:|---:|---:|---:|---:|"]
    for s in natural_summary:
        if s["method"] not in ("raw_yang_no_cap", "cap_only"):
            report.append("|"+s["selector"].split("_")[-1]+"/"+s["method"]+"|"+"|".join(str(s["attacked_"+f+"_count"])+"/9" for f in (
                "alarm_after_first_within_registered_interval", "alarm_any_after_registered_interval", "first_post_attack_alarm_only_after_interval", "alarm_after_first_any_horizon", "alarm_before_first_attack"))+"|")
    spatial = [s for s in natural_summary if s["method"] == "spatial_hard"]
    assert [s["attacked_alarm_after_first_within_registered_interval_count"] for s in spatial] == [6, 7]
    assert all(s["attacked_alarm_after_first_any_horizon_count"] == 9 for s in spatial)
    report += ["", f"空间硬门控在39个无替换seed中，200–249出现报警{spatial[0]['unattacked_alarm_any_registered_interval_count']}/39，250–399出现报警{spatial[0]['unattacked_alarm_any_after_registered_interval_count']}/39。故9/9最终报警不能解释成9/9准确检测了攻击。健康同seed报警时间序列未保存，不能仅凭这些数据识别哪次迟到报警由攻击造成。",
               "", "报警数组对空间门控/Zhou由低权重状态构造，缓存驻留期间可持续为真；这里统计的是报警/拒绝状态出现，不是每一步都有新的独立检测。完整汇总包含Wilson区间，9/9的95% Wilson区间约[0.701,1]，也不能作必然检出保证。", "",
               "## 4. 恢复时间的两层勘误", "",
               "原函数无攻击返回0，导致自然组平均值混入39个零。另一个问题是：搜索强制从251开始，但以最后替换+1计时。自然策略可能更早结束并恢复，故仅剔除零值仍会高估首次容差返回。", "",
               "本次同时保留legacy条件统计，并以原始误差轨迹重新搜索：①自末次攻击更新状态last+1开始，计时也从last+1；②从其下一状态last+2开始；③从末次恶意包退出缓存所影响的首状态cache_exit+1开始。三者计时原点不同，不能混作同一个恢复指标。", "",
               "|预算/方法|旧全48seed均值|旧受攻9seed条件均值|从last+1搜索|从last+2搜索|从cache_exit+1搜索|",
               "|---|---:|---:|---:|---:|---:|"]
    for s in natural_summary:
        if s["method"] in ("raw_yang_no_cap", "spatial_hard", "zhou_random_protection"):
            report.append("|"+s["selector"].split("_")[-1]+"/"+s["method"]+"|"+"|".join(f"{s[f+'_mean']:.3f}" for f in (
                "legacy_all_seed_recovery", "legacy_conditional", "last_update_return", "after_last_update_return", "cache_exit_return"))+"|")
    report += ["", "恢复规则保持原口径：连续5个状态满足‖e_attack‖≤‖e_clean‖+0.1，记录首次满足的起点。它不是永久恢复，也不是与健康估计逐状态重合；可能随后再次超限。右删失计数与逐seed记录均保存，若存在删失，所列时长含截尾观测，不能解释成无偏平均恢复时间。缓存更换后载荷未再次被攻击者篡改，不代表sender估计已经健康。", "",
               "## 5. cap与附加防御收益分解", "",
               "|Replay|raw超额MSE|cap超额MSE|cap+空间超额MSE|cap+Zhou超额MSE|",
               "|---|---:|---:|---:|---:|"]
    for selector in FORCED:
        lookup = {r["method"]: r["receiver_excess_mean"] for r in excess_table if r["selector"] == selector}
        report.append("|"+selector+"|"+"|".join(f"{lookup[m]:.6f}" for m in ("raw_yang_no_cap", "cap_only", "spatial_hard", "zhou_random_protection"))+"|")
    report += ["", "负差表示左方法MSE更低。以下为同seed实际受攻MSE差；另一个CSV列单独给出相对各自健康基准的超额MSE差，二者不可混用。", "",
               "|Replay|左−右|实际受攻MSE配对差[95%CI]|",
               "|---|---|---:|"]
    for r in decomposition:
        if r["selector"] in ("random_history", "nearest_current_sender") and r["left"] in ("cap_only", "spatial_hard", "zhou_random_protection"):
            report.append(f"|{r['selector']}|{r['left']}−{r['right']}|{cell(r, 'receiver_actual_mse_difference')}|")
    report += ["", "cap消除了该模型中强随机Replay的大部分损失；附加保护仍降低cap剩余损失。不能把raw→最终方法的全部收益归给检测器。episode/CUSUM还包含年龄衰减，不能解释为仅增加一个检测统计量。不同防御改变发送端估计及历史字典，所以同攻击策略、机会和seed并不等于逐字节相同的Replay载荷；这些差分是闭环策略比较，不是固定载荷的纯模块因果分解。",
               "", "原正常episode误隔离审计：Zhou约4.88%、空间4.68%、episode均值4.73%、CUSUM6.50%。CUSUM风险未匹配5%目标，不可将当前排序当作等误报风险结论。机会、字节口径保持原样：每seed503次节点发送、1006条边消息、16096载荷字节（仅2个float64状态，不含网络协议头）；本次分析新增部署通信为0。", "",
               "## 6. 撤回不适用的1%方法改进功效解释", "",
               "撤回745798149989作为‘检出两个候选方法1%改善所需seed数’的依据。原数来自raw攻击与健康逐seed相对损失(P_attack−P_healthy)/P_healthy的标准差3082.526；分母随机且可能很小，并非两个防御方法配对差的标准差。本次不替换为另一个臆测样本数。", "",
               "正确后续流程：先固定候选a和基准b、主要窗口损失L及1%参考尺度S，再用独立pilot估计D_s=L_a(s)−L_b(s)的方差。若S由独立健康pilot固定，则目标δ=0.01S；配对均值检验近似n≈[(z_(1−α/2)+z_(1−β))sd(D)/δ]^2需检查尾部、有限样本和多重比较，不能直接沿用本次数值。若用比值目标E[L_a]/E[L_b]，应对配对联合分布与分母不确定性建模，不能把逐seed随机比值与均值比混同。", "",
               "## 7. 可复现性及研究决定", "",
               f"复现命令（仓库根目录）：`.venv/Scripts/python.exe reviews/g2_closeout_errata/code/analyze_errata.py --run-id {args.run_id}_reproduce`。输出目录禁止已存在，不覆盖任何历史分析。", "",
               f"结果目录：`results/{args.run_id}/`。包含全部1728个seed×策略×方法记录、12个自然组汇总、30个配对分解、配置、输入输出SHA256及验证日志。所有原v3文件运行前后逐字节哈希相同，且completion登记输出哈希均校验。", "",
               "**研究决定：维持G2结项及G1-R当前候选终止。攻击有效性成立；检测具有条件局限；恢复统计应采用本勘误；论文方法增量仍未建立。G3只进入预注册筛选，不批准新算法开发。** 本次无新文献下载。", ""]
    (out / "g2_erratum_report.md").write_text("\n".join(report), encoding="utf-8")
    after = hashes()
    write_json(out / "source_hashes_after.json", after)
    assert before == after, "Original G2 files changed"
    assert len(per_seed) == 1728 and len(natural_summary) == 12 and len(decomposition) == 30
    write_json(out / "validation.json", {"passed": True, "simulation_executed": False,
        "source_files_byte_identical": True, "source_file_count": len(before),
        "original_registered_hashes_verified": len(completion["output_hashes"]),
        "per_seed_rows": len(per_seed), "natural_summary_rows": len(natural_summary),
        "paired_decomposition_rows": len(decomposition), "legacy_metrics_reconstructed": True,
        "unattacked_errors_equal_clean": True, "natural_spatial_counts_independently_checked": True})
    write_json(out / "provenance.json", {"analysis_run_id": args.run_id,
        "parent_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "analysis_source_sha256": sha(Path(__file__)), "python": platform.python_version(),
        "numpy": np.__version__, "scipy": __import__("scipy").__version__})
    write_json(out / "output_hashes.json", {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()})
    print(json.dumps({"run_id": args.run_id, "passed": True, "per_seed_rows": len(per_seed),
                      "original_files_unchanged": True, "report": str(out / "g2_erratum_report.md")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
