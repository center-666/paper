"""Generate the G2 five-question report from the immutable v3 run outputs."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy import stats


ROOT = Path(__file__).resolve().parents[3]
RUN_ID = "2026-11-13_g2_replay_effectiveness_v3"
RUN = ROOT / "simulation/g2_runs" / RUN_ID
REVIEW = ROOT / "reviews/fdi_replay_20261112"
OUT = REVIEW / "g2_final_report.md"
FORCED = ("fixed_lag8", "random_history", "nearest_current_sender", "risk_greedy_forced_fallback")
NATURAL = ("risk_greedy_natural_budget_0.25", "risk_greedy_natural_budget_1.0")
METHODS = ("raw_yang_no_cap", "cap_only", "zhou_random_protection", "spatial_hard",
           "episode_prefix_mean", "energy_cusum")


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def numeric(rows, key):
    return np.asarray([float(r[key]) for r in rows if r.get(key, "") not in ("", None)], dtype=float)


def mean_ci(values):
    a = np.asarray(values, dtype=float)
    if not len(a):
        return None, None, None
    mean = float(a.mean())
    if len(a) < 2:
        return mean, None, None
    half = float(stats.t.ppf(.975, len(a)-1) * a.std(ddof=1) / np.sqrt(len(a)))
    return mean, mean-half, mean+half


def seed_bootstrap_ci(values, seed=20261113, draws=10000):
    a = np.asarray(values, dtype=float)
    if not len(a):
        return None, None, None
    rng = np.random.default_rng(seed)
    sampled = rng.choice(a, size=(draws, len(a)), replace=True).mean(axis=1)
    low, high = np.quantile(sampled, [.025, .975])
    return float(a.mean()), float(low), float(high)


def fmt(x, digits=3):
    if x is None or not np.isfinite(float(x)):
        return "NA"
    return f"{float(x):.{digits}f}"


def cell(mean, low, high, digits=3):
    return f"{fmt(mean, digits)} [{fmt(low, digits)}, {fmt(high, digits)}]"


def paired(left, right, metric):
    l = {int(r["seed"]): float(r[metric]) for r in left}
    r = {int(row["seed"]): float(row[metric]) for row in right}
    seeds = sorted(set(l) & set(r))
    return mean_ci([l[s]-r[s] for s in seeds])


def phase_rows(all_rows, selector, method, phase):
    return [r for r in all_rows if r["selector"] == selector and r["method"] == method and r["phase"] == phase]


def main():
    completion = json.loads((RUN / "completion.json").read_text(encoding="utf-8"))
    plan = json.loads((RUN / "plan.json").read_text(encoding="utf-8"))
    seed_doc = json.loads((RUN / "seeds.json").read_text(encoding="utf-8"))
    assert completion["completed"] and completion["run_id"] == RUN_ID
    assert completion["registered_selectors"] == list(plan["replay_selectors"][1:])
    assert completion["registered_defenses"] == plan["defenses"]
    test_seeds = set(seed_doc["test"])
    assert len(test_seeds) == plan["calibration"]["test_seeds"]["count"]
    splits = list(seed_doc.values())
    assert all(not (set(splits[i]) & set(splits[j])) for i in range(len(splits)) for j in range(i+1, len(splits)))
    for name, expected in completion["output_hashes"].items():
        assert sha(RUN/name) == expected, f"Output hash mismatch: {name}"
    hashes = json.loads((RUN / "code_hashes.json").read_text(encoding="utf-8"))
    assert hashes["g2_screen_plan.json"] == sha(REVIEW / "g2_screen_plan.json")
    assert hashes["engine.py"] == sha(ROOT / "simulation/engine.py")
    assert hashes["g2_replay_runner.py"] == sha(ROOT / "simulation/g2_replay_runner.py")

    summaries = read_csv(RUN / "selector_method_summary.csv")
    seed_metrics = read_csv(RUN / "per_seed_metrics.csv")
    packets = read_csv(RUN / "packet_opportunities.csv")
    phases = read_csv(RUN / "phase_metrics_per_seed.csv")
    timings = read_csv(RUN / "detection_timing_per_seed.csv")
    normal = read_csv(RUN / "normal_audit.csv")
    clean = read_csv(RUN / "no_attack_baseline_per_seed.csv")
    with np.load(RUN / "test_inputs.npz") as test_inputs:
        test_seed_order = test_inputs["seeds"].astype(int)
        test_schedule = test_inputs["schedule"].astype(bool)
    seed_index = {int(seed): i for i, seed in enumerate(test_seed_order)}
    sender = int(plan["model"]["primary_attack_edge"][0])
    assert len(seed_metrics) == 6*6*len(test_seeds)
    assert len(phases) == 6*6*48*4
    assert len(timings) == 6*6*48
    assert len(summaries) == 6*6
    assert {int(r["seed"]) for r in seed_metrics} == test_seeds
    assert len({(r["selector"],r["method"],int(r["seed"])) for r in seed_metrics}) == len(seed_metrics)

    # Validate opportunities, replacement counts, and source packet legality.
    forced_group = set(plan["attack_information"]["same_replacement_count_group"])
    for r in seed_metrics:
        assert int(r["opportunities"]) == 14
        if r["selector"] in forced_group:
            assert int(r["replacements"]) == 14
    for r in packets:
        assert r["replacement_attempted"] in {"True", "False"}
        if r["replacement_attempted"] == "True":
            assert 0 <= int(r["source_time"]) < int(r["time"])
            assert int(r["content_age"]) == int(r["time"])-int(r["source_time"])
            assert test_schedule[seed_index[int(r["seed"])], int(r["source_time"]), sender]
    changed_counts = {}
    replacement_counts = {}
    for row in packets:
        key = (row["selector"], row["method"], int(row["seed"]))
        changed_counts[key] = changed_counts.get(key, 0) + int(row["payload_changed"] == "True")
        replacement_counts[key] = replacement_counts.get(key, 0) + int(row["replacement_attempted"] == "True")
    for row in seed_metrics:
        key = (row["selector"], row["method"], int(row["seed"]))
        assert int(row["payload_changes"]) == changed_counts.get(key, 0)
        assert int(row["replacements"]) == replacement_counts.get(key, 0)
    assert {int(r["opportunities"]) for r in seed_metrics} == {14}

    # Same-opportunity damage ranking uses the unprotected closed-loop Yang baseline.
    raw = [r for r in seed_metrics if r["method"] == "raw_yang_no_cap"]
    raw_summary = {r["selector"]: r for r in summaries if r["method"] == "raw_yang_no_cap"}
    packet_summary = {}
    for selector in list(FORCED)+list(NATURAL):
        rows = [r for r in packets if r["selector"] == selector and r["method"] == "raw_yang_no_cap"]
        attacked = [r for r in rows if r["replacement_attempted"] == "True"]
        packet_summary[selector] = {
            "mean_age": float(np.mean([int(r["content_age"]) for r in attacked])) if attacked else None,
            "matched_gap": float(np.mean([r["matched_gap"] == "True" for r in attacked])) if attacked else None,
            "fragment": float(np.mean([r["consecutive_historical_fragment"] == "True" for r in attacked])) if attacked else None,
            "distinct": float(np.mean([r["payload_changed"] == "True" for r in attacked])) if attacked else None,
        }
    ranking = []
    for selector in list(FORCED)+list(NATURAL):
        srows = [r for r in raw if r["selector"] == selector]
        sr = raw_summary[selector]
        recovery = [float(r["recovery_duration"]) for r in srows]
        recovery_censored = [float(r["recovery_right_censored"] == "True") for r in srows]
        attack_m, attack_l, attack_h = mean_ci([float(r["receiver_paired_excess_mse"]) for r in srows])
        net_m, net_l, net_h = mean_ci([float(r["network_paired_excess_mse"]) for r in srows])
        opportunities = np.asarray([int(r["opportunities"]) for r in srows], float)
        replacements = np.asarray([int(r["replacements"]) for r in srows], float)
        changed = np.asarray([int(r["payload_changes"]) for r in srows], float)
        ranking.append({"selector": selector, "opp": float(opportunities.mean()),
            "repl": float(replacements.mean()), "changed": float(changed.mean()),
            "receiver": (attack_m, attack_l, attack_h), "network": (net_m, net_l, net_h),
            "per_opp": float(sr["receiver_excess_per_opportunity"]),
            "per_repl": float(sr["receiver_excess_per_replacement"]),
            "recovery": mean_ci(recovery), "recovery_censored": float(np.mean(recovery_censored)),
            **packet_summary[selector]})
    ranking.sort(key=lambda r: r["receiver"][0], reverse=True)

    # Paired seed differences among the four strategies that replace all 14 opportunities.
    raw_forced = {s: [r for r in raw if r["selector"] == s] for s in FORCED}
    pairwise = []
    winner = ranking[0]["selector"]
    for other in FORCED:
        if other == winner:
            continue
        m, lo, hi = paired(raw_forced[winner], raw_forced[other], "receiver_paired_excess_mse")
        pairwise.append((other, m, lo, hi))

    # Error progression is paired against each method's same-seed no-attack run.
    stage_names = ("registered_attack_window", "actual_replacement_span",
                   "post_attack_stale_cache", "after_replayed_payload_cache_exit")
    stage_tables = {}
    for selector in list(FORCED)+list(NATURAL):
        stage_tables[selector] = {}
        for stage in stage_names:
            rs = phase_rows(phases, selector, "raw_yang_no_cap", stage)
            stage_tables[selector][stage] = {
                "receiver": mean_ci([float(r["receiver_excess_mse"]) for r in rs if r["receiver_excess_mse"]]),
                "network": mean_ci([float(r["network_excess_mse"]) for r in rs if r["network_excess_mse"]]),
                "cumulative_receiver": mean_ci([float(r["receiver_cumulative_excess"]) for r in rs]),
                "length": float(np.mean([int(r["state_count"]) for r in rs])),
            }
    lifecycle = {}
    for selector in list(FORCED)+list(NATURAL):
        rs = [r for r in timings if r["selector"] == selector and r["method"] == "raw_yang_no_cap"]
        exits = [float(r["cache_exit_receive_time"]) for r in rs if r["cache_exit_receive_time"]]
        lasts = [float(r["last_replacement_time"]) for r in rs if r["last_replacement_time"]]
        lifecycle[selector] = {"last": mean_ci(lasts), "exit": mean_ci(exits),
                               "exit_missing": sum(not r["cache_exit_receive_time"] for r in rs)}

    # Aggregate the four forced policies within each seed before inferential summaries.
    monitored = ("zhou_random_protection", "spatial_hard", "episode_prefix_mean", "energy_cusum")
    normal_by_method = {r["method"]: r for r in normal}
    detector_tables = []
    for method in monitored:
        tr = [r for r in timings if r["method"] == method and r["selector"] in FORCED]
        by_seed = {}
        for r in tr:
            z = by_seed.setdefault(int(r["seed"]), {"detect": [], "delay": [], "pre": [],
                                                      "prelen": [], "same_tick": [], "miss": []})
            detected = not (r["first_alarm_time"] in ("", None))
            z["detect"].append(float(detected))
            if detected:
                z["delay"].append(float(r["alarm_delay_from_first_replacement"]))
            z["same_tick"].append(float(detected and
                int(r["first_alarm_time"]) == int(r["first_replacement_time"])))
            z["miss"].append(float(not detected))
            z["pre"].append(float(r["receiver_excess_before_alarm_cumulative"]))
            z["prelen"].append(float(r["receiver_states_before_alarm"]))
        detect_rates = [np.mean(v["detect"]) for v in by_seed.values()]
        delays = [np.mean(v["delay"]) for v in by_seed.values() if v["delay"]]
        pre = [np.mean(v["pre"]) for v in by_seed.values()]
        prelen = [np.mean(v["prelen"]) for v in by_seed.values()]
        same_tick = [np.mean(v["same_tick"]) for v in by_seed.values()]
        missed = [np.mean(v["miss"]) for v in by_seed.values()]
        alarm_frac = [float(r["attack_window_alarm_fraction_per_opportunity"])
                      for r in summaries if r["method"] == method and r["selector"] in FORCED]
        nr = normal_by_method[method]
        detector_tables.append({"method": method, "fpr": float(nr["episode_false_isolation"]),
            "normal_receiver": float(nr["normal_receiver_mse"]),
            "detect": mean_ci(detect_rates), "delay": seed_bootstrap_ci(delays),
            "pre": mean_ci(pre), "prelen": mean_ci(prelen),
            "same_tick": mean_ci(same_tick), "missed": mean_ci(missed),
            "alarm_per_op": float(np.mean(alarm_frac))})

    # Per-packet hard gating versus no defense, plus the local-estimator reference.
    isolation = []
    for stage in stage_names:
        seed_deltas = {s: [] for s in test_seeds}
        for selector in FORCED:
            hard = {int(r["seed"]): float(r["receiver_mse"]) for r in
                    phase_rows(phases, selector, "spatial_hard", stage) if r["receiver_mse"]}
            base = {int(r["seed"]): float(r["receiver_mse"]) for r in
                    phase_rows(phases, selector, "raw_yang_no_cap", stage) if r["receiver_mse"]}
            for seed in seed_deltas:
                if seed in hard and seed in base:
                    seed_deltas[seed].append(hard[seed] - base[seed])
        mm, ll, hh = mean_ci([float(np.mean(v)) for v in seed_deltas.values() if v])
        isolation.append((stage, mm, ll, hh))
    clean_methods = {}
    for method in METHODS + ("local",):
        rows = [r for r in clean if r["method"] == method]
        clean_methods[method] = {"receiver": mean_ci([float(r["receiver_mse"]) for r in rows]),
                                 "network": mean_ci([float(r["network_mse"]) for r in rows])}
    raw_fpr = normal_by_method["raw_yang_no_cap"]["episode_false_isolation"]
    hard_normal_delta = clean_methods["spatial_hard"]["receiver"][0] - clean_methods["raw_yang_no_cap"]["receiver"][0]

    v2_failure = RUN.parent / "2026-11-13_g2_replay_effectiveness_v2" / "failure.json"
    report = []
    report.append("# G2：历史估计包 Replay 闭环效果与防御审计")
    report.append("")
    report.append(f"Run ID：`{RUN_ID}`。测试 48 个独立 seed；五节点、二维状态、T=400；目标边 0→1；攻击时段发送机会为 200–249；同一外生 irregular 日程用于全部策略与方法。此为预注册小型探索筛选，不是确认性论文实验，48 seed 无法支撑 1% MSE 改善主张。")
    report.append("")
    report.append(f"冻结计划 SHA-256：`{hashes['g2_screen_plan.json']}`；engine SHA-256：`{hashes['engine.py']}`。v2 失败仅在结果追加时缺少局部列表，失败目录和已有正常校准/clean baseline 均保留，未并入本报告；见 [`v2 failure`](../../simulation/g2_runs/2026-11-13_g2_replay_effectiveness_v2/failure.json)。")
    report.append("")
    report.append("MSE 按状态误差分量平方和计算；network MSE 再对节点取平均。表内区间按 seed 配对 t 区间，seed 是统计单位。缓存替换和退出口径采用融合时间 t 与估计状态索引 t+1：缓存退出发生在下一次实际 sender 包接收 q，状态索引 q+1 才进入“缓存退出后”区间。新传输未再次被篡改，不等于 sender estimate 等于健康轨迹。")
    report.append("")
    report.append("## 五项结论")
    report.append("")
    report.append("### 1. 相同攻击机会下的 Replay 损失")
    report.append("")
    report.append("先用无保护 `raw_yang_no_cap` 排序闭环攻击后果。四个强制策略在每个 seed 都覆盖 14/14 个真实发送机会、14 次替换；自然预算策略也按全部 14 个机会作分母，未删除未替换机会。实际载荷变化数、内容年龄和来源间隔如下：")
    report.append("")
    report.append("| Replay 策略 | 机会/替换/载荷变化 | 平均内容年龄 | Replay包间隔匹配率 | 连续历史片段率 | receiver MSE 超额 [95% CI] | network MSE 超额 [95% CI] | receiver 超额/机会 |")
    report.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in ranking:
        report.append(f"| `{r['selector']}` | {fmt(r['opp'],1)}/{fmt(r['repl'],1)}/{fmt(r['changed'],1)} | {fmt(r['mean_age'],1)} | {fmt(100*r['matched_gap'],1)}% | {fmt(100*r['fragment'],1)}% | {cell(*r['receiver'])} | {cell(*r['network'])} | {fmt(r['per_opp'])} |")
    report.append("")
    report.append(f"在相同 14 次替换下，均值最高的是 `{winner}`。它相对其他强制策略的 receiver MSE 超额配对差为：")
    report.append("")
    for other, m, lo, hi in pairwise:
        report.append(f"- 对 `{other}`：{cell(m,lo,hi)}。")
    report.append("")
    report.append("冻结计划没有单独设计 matched-gap Replay selector；本表只对实际选出的 Replay 包离线统计来源间隔是否匹配当前接收间隔，不能将该比例解读为一次主动优化的 matched-gap 攻击实验。")
    report.append("这些差是同 seed 的比较；若区间跨零，只能说均值排序如此，不能断言稳定优于。自然风险预算策略替换数不同，只能按每机会总体影响比较，不能与强制组冒充同替换次数排名。旧的 frozen-sender 字典 probe 仅为攻击侧评分，不能替代本表的闭环估计损失。")
    report.append("")
    report.append("### 2. 损失发生时段")
    report.append("")
    report.append("`registered_attack_window` 是估计状态索引 201–250；`actual_replacement_span` 从首次注入后首个状态至最后注入后首个状态；`post_attack_stale_cache` 从最后注入后继续使用旧缓存，到 q 收到下一包；`after_replayed_payload_cache_exit` 从 q+1 状态开始。下面是无保护 Yang 的 receiver 超额 MSE，括号为配对 95% CI，区间均对同 seed 的健康轨迹计算：")
    report.append("")
    report.append("| Replay 策略 | 攻击登记窗 | 实际替换跨度 | 攻击停止但旧缓存驻留 | 旧载荷退出缓存后 | 自然恢复步数/右删失率 | 平均最后替换时刻→缓存退出接收时刻 |")
    report.append("|---|---:|---:|---:|---:|---:|---:|")
    for r in ranking:
        s = r["selector"]
        st = stage_tables[s]
        life = lifecycle[s]
        report.append("| " + s + " | " + cell(*st["registered_attack_window"]["receiver"]) + " | " +
            cell(*st["actual_replacement_span"]["receiver"]) + " | " +
            cell(*st["post_attack_stale_cache"]["receiver"]) + " | " +
            cell(*st["after_replayed_payload_cache_exit"]["receiver"]) + " | " +
            cell(*r["recovery"]) + " / " + f"{100*r['recovery_censored']:.1f}%" + " | " +
            fmt(life["last"][0],1) + "→" + fmt(life["exit"][0],1) + " |")
    report.append("")
    report.append("同一时段的全网络平均 MSE 超额如下：")
    report.append("")
    report.append("| Replay 策略 | 攻击登记窗 | 实际替换跨度 | 攻击停止但旧缓存驻留 | 旧载荷退出缓存后 |")
    report.append("|---|---:|---:|---:|---:|")
    for r in ranking:
        s = r["selector"]
        st = stage_tables[s]
        report.append("| " + s + " | " + cell(*st["registered_attack_window"]["network"]) + " | " +
            cell(*st["actual_replacement_span"]["network"]) + " | " +
            cell(*st["post_attack_stale_cache"]["network"]) + " | " +
            cell(*st["after_replayed_payload_cache_exit"]["network"]) + " |")
    report.append("缓存退出后仍可见网络误差超额，随后与滤波递推自然衰减；这证明攻击影响越过直接缓存驻留期，不证明估计器永久不恢复，也不代表后续发送被再次篡改。登记窗包含无发送更新，实际替换跨度则按实际攻击事件界定。")
    report.append("")
    report.append("按预设的连续 5 步回到 clean 误差 +0.1 判据，raw Yang 的恢复时间为：")
    report.append("")
    report.append("| Replay 策略 | 平均恢复步数 [95% CI] | 右删失率 |")
    report.append("|---|---:|---:|")
    for r in ranking:
        report.append("| " + r["selector"] + " | " + cell(*r["recovery"]) +
                      " | " + f"{100*r['recovery_censored']:.1f}%" + " |")
    report.append("")
    report.append("### 3. 检测失败还是报警太迟")
    report.append("")
    report.append("对四个相同替换次数策略，先在每个 seed 内平均策略结果，再计算 seed 区间。报警前损失是从首个注入之后至首次 alarm 更新之前的 receiver 累计 MSE 超额；没有报警的轨迹按右删失并计至仿真末，不从分母删除。攻击检测率和同更新比例按 seed 使用 t 区间，条件延迟按 seed 做 percentile bootstrap；MSE 超额使用 seed 配对 t 区间。")
    report.append("")
    report.append("| 方法 | 正常 episode 误隔离率 | 四策略攻击报警率 | 同更新报警率 | 已报警条件延迟 | 报警前 receiver 累计超额 | 报警前状态数均值 | 正常 receiver MSE |")
    report.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for d in detector_tables:
        report.append("| " + d["method"] + " | " + f"{100*d['fpr']:.2f}%" + " | " +
            cell(*(100*x for x in d["detect"])) + "% | " + cell(*(100*x for x in d["same_tick"])) + "% | " +
            cell(*d["delay"],digits=2) + " 步 | " + cell(*d["pre"]) + " | " +
            fmt(d["prelen"][0],1) + " | " + fmt(d["normal_receiver"]) + " |")
    report.append("")
    report.append("原始 Yang 与 cap-only 都没有检测器输出，因此不能把 cap-only 的低残余误差称为成功检测。其余方法在本模型强攻击下的报警比例及报警前损失见表。报警率必须与各自正常 episode 误隔离率一起读；energy-CUSUM 的正常误隔离略高于计划 5%目标，不能按同一风险水平宣称排名。nearest-current 的攻击残差更弱、报警延迟较长；但其无保护真实损失也明显低于随机历史包重放。误隔离率是 episode 描述性点估计；episode 在 seed 内相关，因此不将 episode 数当作独立样本构造置信区间。")
    report.append("")
    report.append("同一融合更新报警的比例（报警发生在当前被攻击消息参与状态更新之前）为：")
    report.append("")
    report.append("| 方法 | 同更新报警率（按 seed 平均四个强制策略） |")
    report.append("|---|---:|")
    for d in detector_tables:
        report.append("| " + d["method"] + " | " + f"{100*d['same_tick'][0]:.1f}%" + " |")
    report.append("")
    report.append("### 4. 自然恢复与隔离代价")
    report.append("")
    report.append("无保护 Yang 在攻击停止后仍因旧缓存和当前估计状态承载污染，但缓存退出后 MSE 通常下降；恢复时间按原代码条件定义为连续 5 步误差范数回到 clean 误差 +0.1 以内，报告右删失率。下表比较四个强制策略上 `spatial_hard` 相对无保护 Yang 的 receiver MSE 配对差；负值表示硬门控误差更低。")
    report.append("")
    report.append("| 时段 | spatial_hard − raw Yang receiver MSE [95% CI] |")
    report.append("|---|---:|")
    for stage, m, lo, hi in isolation:
        report.append(f"| `{stage}` | {cell(m,lo,hi)} |")
    report.append("")
    report.append(f"正常审计中 hard gate 的 episode 误隔离率为 {100*float(normal_by_method['spatial_hard']['episode_false_isolation']):.2f}%；正常 receiver MSE 相对 raw Yang 变化 {hard_normal_delta:+.6f}。本实现是每个新包的单拍 hard gate，不是报警后永久隔离。无攻击 receiver MSE 基线：raw Yang {clean_methods['raw_yang_no_cap']['receiver'][0]:.6f}，local {clean_methods['local']['receiver'][0]:.6f}。所有方法使用相同 503 node broadcasts、1006 directed edge messages、16096 个 payload bytes/seed；local baseline 不发送邻居估计。")
    report.append("")
    report.append("因此，在此冻结模型下，直接硬门控没有显示出平均 MSE 增加；但它是条件化的一拍门控结果，不能外推到永久隔离策略或其他拓扑。攻击停止后的滤波自然恢复也不是对健康轨迹的即时回滚。")
    report.append("")
    report.append("### 5. 明确防御缺口与论文判断")
    report.append("")
    report.append("本轮证据支持一个**模型范围内的风险事实**：合法历史包重放可在未经保护的闭环估计器中造成很大的估计损失，并在旧载荷退出缓存后继续传播；随机挑选历史包是等替换次数组中的最强平均攻击。与此同时，Zhou 随机保护、空间硬门控、episode-prefix mean 和 energy-CUSUM 在这一全本地可观的五节点模型下都产生高报警率并大幅压低平均损失，简单 cap-only 也显著限制异常消息影响。因此目前没有证据证明现有基准存在一个不可替代且尚未覆盖的防御缺口。")
    report.append("")
    report.append("信息限制仍然重要：没有可信序号/认证时，当前接收时间只能证明包现在到达，不能证明载荷是当前生成；历史片段可在连续替换时匹配发送间隔。但这次实验中该潜在不可辨识性没有转化成对现有方法的稳定性能击穿。若未来要研究迟到历史修正，需证明在可比误隔离率、同一通信成本下强基线仍留下可恢复损失，而不能仅以缓存后误差存在作为创新。")
    report.append("")
    report.append("**四类判断分开给出：**攻击有效性——在冻结模型与所测历史选择策略下成立；检测能力——已有方法对本轮主要强攻击大多可报警，局部难例是低扰动最近邻策略；恢复损失——未保护误差可在缓存退出后延续但会自然衰减，硬门控显著降低攻击损失；论文创新性——本轮未建立。**当前不推荐新的学报候选**，也不恢复 G1-R 的 post-cache GLS/influence-capsule 候选。")
    report.append("")
    report.append("## 复现与边界")
    report.append("")
    report.append(f"最终原始结果：[`{RUN_ID}`](../../simulation/g2_runs/{RUN_ID})。报告程序 SHA-256：`{sha(Path(__file__))}`。冻结 JSON 和旧结果未改；engine 新增了接收端回调合法历史发送包的 selector 接口，runner 的 seed/selector/defense 解析与冻结计划对齐，修改后代码哈希见 Run 目录 `code_hashes.json`。")
    report.append("Runtime 原始源码哈希见 Run 目录 code_hashes.json；[源码指纹说明](g2_source_fingerprints.json)同时记录工作区原始字节 SHA-256 与仅将 CRLF 转为 LF 后的 SHA-256，便于 Windows/Unix 检出时核验同一源码。v2 失败 Run 保留但不并入统计；v3 使用冻结计划的 48 个 seed，不构成新增独立样本。")
    report.append("")
    report.append("本结论只覆盖 G2 注册的单向链路替换、不规则固定外生发送日程、每步本地量测及指定攻击时段。未验证闭环触发次数随估计改变、可信新鲜度认证、任意 Byzantine 攻击、更多攻击链路或确认性 1% 改善。方法新颖性和投稿可行性不能从攻击曲线单独推出。")
    OUT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(OUT), "ranking": ranking,
        "detectors": detector_tables, "isolation_deltas": isolation,
        "report_sha256": sha(OUT)}, ensure_ascii=False, indent=2, default=float))


if __name__ == "__main__":
    main()
