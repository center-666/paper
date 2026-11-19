"""Exact covariance-label audit and one bounded constant refinement, 2026-10-19.

Run with Python + numpy. Existing manuscript data are read only. No Monte Carlo,
attack optimization, numerical integration, or modification of earlier files.
Exact labels use fractions.Fraction; norm/eigenvalue/constant evaluations use
ordinary floating point and are explicitly not interval certificates.
"""
from __future__ import annotations

from fractions import Fraction as F
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
INPUT = ROOT / "vector_data" / "results.json"
OUT = HERE / "label_constants_20261019.json"
REPORT = HERE / "label_constants_20261019.md"


def matrix(x):
    return tuple(tuple(F(str(a)) for a in row) for row in x)


def add(x, y):
    return tuple(tuple(a + b for a, b in zip(rx, ry)) for rx, ry in zip(x, y))


def transpose(x):
    return tuple(zip(*x))


def multiply(x, y):
    return tuple(tuple(sum(a * b for a, b in zip(rx, cy)) for cy in transpose(y))
                 for rx in x)


def inverse(x):
    # Only the two fixed 2D examples are investigated here.
    a, b = x[0]
    c, d = x[1]
    det = a * d - b * c
    assert det != 0
    return ((d / det, -b / det), (-c / det, a / det))


def floating(x):
    return np.asarray([[float(v) for v in row] for row in x])


def serial(x):
    return [[str(v) for v in row] for row in x]


def sym(x):
    return (x + x.T) / 2


def opnorm(x):
    return float(np.linalg.norm(x, 2))


def conditional_parameters(P, A, Q, R, Z):
    sigma = A @ P @ A.T + Q + R
    W = np.linalg.inv(Z) + sigma
    H = sym(0.5 * A.T @ np.linalg.solve(W, A))
    h = float(np.linalg.eigvalsh(H).min())
    # det(I+Sigma Z)=det(Z)det(Z^-1+Sigma), evaluated with symmetric factors.
    signz, logz = np.linalg.slogdet(Z)
    signw, logw = np.linalg.slogdet(W)
    assert signz == signw == 1 and h > 0
    s = math.exp(-(logz + logw) / 2)
    return h, s


def radial_coefficient(h, B):
    # Continuous extension of B^2/(1-exp(-h B^2)) as B tends to zero.
    return 1 / h if B == 0 else B * B / (-math.expm1(-h * B * B))


def oscillation(records, coefficient):
    values = []
    for row in records:
        c = coefficient(row)
        for Y in (0, 1):
            value = row["trace"] + c * (1 - Y / row["s"])
            values.append((value, row["histories"], Y, c))
    lo, hi = min(values, key=lambda x: x[0]), max(values, key=lambda x: x[0])
    return {"constant": hi[0] - lo[0],
            "minimum": {"value": lo[0], "histories": lo[1], "Y": lo[2], "c": lo[3]},
            "maximum": {"value": hi[0], "histories": hi[1], "Y": hi[2], "c": hi[3]}}


def evaluate(name, raw, parameters, reference):
    exact = {key: matrix(raw[key]) for key in ("A", "P0", "Q", "R", "Z")}
    A, Q, R, Z = (floating(exact[key]) for key in ("A", "Q", "R", "Z"))
    invz = inverse(exact["Z"])
    noises = {0: add(exact["R"], invz), 1: exact["R"]}
    k, bref = parameters["k"], parameters["b_ref"]
    v = np.asarray(raw["direction"], dtype=float)
    v /= np.linalg.norm(v)
    # Each coefficient product T_{j,h} multiplies one (possibly data-dependent)
    # input a_j in D_t=-sum_{j:gamma_j=1} T_{j,h} a_j.
    nodes = [{"history": "", "prior": exact["P0"], "mass": 1.,
              "products": [], "radius_recursive": 0.}]
    global_radius = 0.
    global_radii, ells, target, lower = [], [], [], []
    max_recursion_residual = 0.
    for t in range(k + 1):
        next_nodes, alphas, betas = [], [], []
        ell = opnorm(A) * global_radius if t else 0.
        for node in nodes:
            P = floating(node["prior"])
            W = P + R + floating(invz)
            s = math.exp(-.5 * (np.linalg.slogdet(Z)[1] + np.linalg.slogdet(W)[1]))
            for gamma in (0, 1):
                noise = noises[gamma]
                post_exact = inverse(add(inverse(node["prior"]), inverse(noise)))
                gain_exact = multiply(node["prior"], inverse(add(node["prior"], noise)))
                K, post = floating(gain_exact), floating(post_exact)
                max_recursion_residual = max(max_recursion_residual,
                                             float(np.linalg.norm(post - (P - K @ P))))
                S = np.eye(2) - K
                M = S @ A
                products = [M @ T for T in node["products"]]
                if gamma:
                    products.append(K)
                rprod = sum(opnorm(T) for T in products)
                rrec = opnorm(M) * node["radius_recursive"] + gamma * opnorm(K)
                assert rprod <= rrec + 1e-12
                history = node["history"] + str(gamma)
                mass = node["mass"] * (s if gamma == 0 else 1 - s)
                alphas.append(opnorm(S))
                if gamma:
                    betas.append(opnorm(K))
                pred_exact = add(multiply(multiply(exact["A"], post_exact),
                                          transpose(exact["A"])), exact["Q"])
                next_nodes.append({"history": history, "prior": pred_exact, "mass": mass,
                                   "products": products, "radius_recursive": rrec})
                if t == k:
                    target.append({"history": history, "P_exact": post_exact,
                                   "P": post, "healthy_mass": mass,
                                   "radius_product": rprod,
                                   "radius_recursive": rrec})
                    if gamma:
                        Scurrent = P + R
                        Ti = np.linalg.inv(Scurrent) + Z
                        u = A @ K @ v
                        F1 = math.sqrt(2 / math.pi) * (
                            math.sqrt(v @ np.linalg.solve(Scurrent, v))
                            + s * math.sqrt(v @ Ti @ v))
                        F2 = 2 * (v @ np.linalg.solve(Scurrent, v) + s * (v @ Ti @ v))
                        az = float(u @ Z @ u)
                        Bh = F2 + 4 * F1 * math.sqrt(az / math.e) + 2 * (1 - s) * az
                        lower.append({"mass": node["mass"], "L": (1 - s) * float(np.linalg.norm(K @ v) ** 2),
                                      "Bh": Bh, "u_norm": float(np.linalg.norm(u))})
        global_radius = max(alphas) * ell + max(betas)
        ells.append(ell)
        global_radii.append(global_radius)
        nodes = next_nodes
    assert abs(sum(x["healthy_mass"] for x in target) - 1) < 1e-12
    groups = {}
    for row in target:
        groups.setdefault(row["P_exact"], []).append(row)
    labels = []
    for Pexact, group in groups.items():
        P = floating(Pexact)
        h, s = conditional_parameters(P, A, Q, R, Z)
        rprod = max(x["radius_product"] for x in group)
        rrec = max(x["radius_recursive"] for x in group)
        labels.append({"histories": [x["history"] for x in group], "P_exact": serial(Pexact),
                       "trace": float(np.trace(P)), "h": h, "s": s,
                       "radius_product_per_unit_b": rprod,
                       "radius_recursive_per_unit_b": rrec,
                       "B_product": bref * rprod, "B_recursive": bref * rrec,
                       "healthy_mass": sum(x["healthy_mass"] for x in group)})
    assert len(target) == 2 ** (k + 1)
    hstar, M = min(x["h"] for x in labels), max(1 / x["s"] for x in labels)
    omega = max(x["trace"] for x in labels) - min(x["trace"] for x in labels)
    Bglobal = global_radius * bref
    q = 1 / radial_coefficient(hstar, Bglobal)
    Cold = M / q + omega
    Cpeak = global_radius ** 2 + omega * opnorm(Z) * sum(x * x for x in ells) / 2
    Cpm = sum(x["mass"] * x["Bh"] for x in lower) / 4
    Lv = sum(x["mass"] * x["L"] for x in lower)
    kappa = 1 / max(1, max(x["u_norm"] for x in lower))
    refc = reference["constants"]
    for key, value in (("r_k", global_radius), ("h_star", hstar), ("M", M), ("q", q),
                       ("Omega", omega), ("C_record", Cold), ("C_peak", Cpeak),
                       ("C_pm", Cpm), ("L_v", Lv), ("kappa", kappa)):
        assert abs(value - refc[key]) <= 1e-10 * max(1, abs(value)), (name, key, value, refc[key])
    variants = {
        "global_coefficient_exact_oscillation": oscillation(labels, lambda x: 1 / q),
        "local_h_global_radius": oscillation(labels, lambda x: radial_coefficient(x["h"], Bglobal)),
        "local_h_recursive_radius": oscillation(labels, lambda x: radial_coefficient(x["h"], x["B_recursive"])),
        "local_h_product_radius": oscillation(labels, lambda x: radial_coefficient(x["h"], x["B_product"])),
        "local_h_product_radius_zero_on_zero_bias": oscillation(
            labels, lambda x: 0. if x["B_product"] == 0 else radial_coefficient(x["h"], x["B_product"]))}
    for value in variants.values():
        value["reduction_percent_vs_old"] = 100 * (1 - value["constant"] / Cold)
        value["linear_upper_lower_slope_ratio"] = value["constant"] * Cpm / Lv
    chosen = variants["local_h_product_radius"]["constant"]
    budgets = []
    b = parameters["budget_peak"]
    for eps in parameters["epsilon_values"]:
        attainable = Lv * min(kappa * kappa * b * b, eps / Cpm)
        old_upper = min(Cpeak * b * b, Cold * eps)
        new_upper = min(Cpeak * b * b, chosen * eps)
        budgets.append({"b": b, "epsilon": eps, "attainable_lower": attainable,
                        "old_upper": old_upper, "new_upper": new_upper,
                        "old_upper_lower_ratio": old_upper / attainable,
                        "new_upper_lower_ratio": new_upper / attainable})
    minpair = min(np.linalg.norm(x["P"] - y["P"], "fro")
                  for i, x in enumerate(target) for y in target[i + 1:])
    labeltext = json.dumps([{k: row[k] for k in ("histories", "P_exact")} for row in labels],
                           sort_keys=True, separators=(",", ":"))
    return {"k": k, "b_ref": bref, "history_count": len(target), "exact_label_count": len(labels),
            "injective_by_exact_fraction_equality": len(target) == len(labels),
            "minimum_pair_distance_fro_float_diagnostic": float(minpair),
            "exact_label_table_sha256": hashlib.sha256(labeltext.encode()).hexdigest(),
            "covariance_formula_max_float_residual": max_recursion_residual,
            "old_constants_independently_recomputed": {
                "r_k": global_radius, "h_star": hstar, "M": M, "q": q, "Omega": omega,
                "C_record": Cold, "C_peak": Cpeak, "C_pm": Cpm, "L_v": Lv, "kappa": kappa},
            "old_linear_upper_lower_slope_ratio": Cold * Cpm / Lv,
            "radius_product_range": [min(x["B_product"] for x in labels), max(x["B_product"] for x in labels)],
            "global_bias_radius": Bglobal,
            "variants": variants, "budget_comparison": budgets, "labels": labels}


def main():
    global INPUT, OUT, REPORT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=INPUT,
                        help="Existing manuscript directory or its vector_data/results.json (read only)")
    parser.add_argument("--output-dir", type=Path, default=HERE,
                        help="Write the two audit outputs here; defaults to this script directory")
    args = parser.parse_args()
    INPUT = args.source / "vector_data" / "results.json" if args.source.is_dir() else args.source
    args.output_dir.mkdir(parents=True, exist_ok=True)
    OUT = args.output_dir / "label_constants_20261019.json"
    REPORT = args.output_dir / "label_constants_20261019.md"
    original = json.loads(INPUT.read_text(encoding="utf-8"))
    parameters = original["parameters"]
    cases = {name: evaluate(name, dict(parameters["common"], **specific), parameters,
                            original["cases"][name])
             for name, specific in parameters["cases"].items()}
    result = {"status": "exact_label_enumeration_and_float_constant_audit_passed",
              "input": str(INPUT), "input_sha256": hashlib.sha256(INPUT.read_bytes()).hexdigest(),
              "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "python": platform.python_version(), "numpy": np.__version__,
              "parameters": parameters, "cases": cases,
              "limitations": [
                  "Injectivity is exact for the stated decimal-rational S/U parameters at k=4 only.",
                  "Constants and norm/eigenvalue values are ordinary floating-point evaluations, not rigorous intervals.",
                  "No Monte Carlo, no new attack policy, no attack-class optimization, and no full-log numerical TV integration.",
                  "The refined bound remains conservative; attaining an order does not mean attaining its numerical constant.",
                  "The label radius applies to all admissible policies because it bounds every bounded input in the bias recursion."]}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 精确协方差标签与一次标签依赖常数核查（2026-10-19）", "",
             "## 核查范围", "",
             "仅复用正式稿固定二维 S/U 工况、k=4、设计幅值 b_ref=0.2。原始实验文件只读；未重新运行 Monte Carlo，未优化攻击。精确有理数递推用于判定标签是否相等，谱范数、特征值与常数仅为普通浮点评估。", "",
             "## 精确标签", "",
             "输入十进制参数按其十进制有理数值解释。以 P^+=(P^{-1}+R_gamma^{-1})^{-1} 和 P_next^-=A P^+ A^T+Q 递推，完整输出保存在同名 JSON 的 labels[].P_exact。每个分母与分子均为整数，去重使用 Fraction 的精确相等判定。", "",
             "| 工况 | 历史数 | 精确标签数 | 最小 Frobenius 间距（仅浮点诊断） |", "|---|---:|---:|---:|"]
    for name, case in cases.items():
        lines.append(f"| {name} | {case['history_count']} | {case['exact_label_count']} | {case['minimum_pair_distance_fro_float_diagnostic']:.9g} |")
    lines += ["", "两工况均为单射。因此在这两个固定模型和 k=4 下，(P_4^+,gamma_5) 与 gamma_{0:5} 互相确定，对任意同一合法攻击有 Delta_marked=Delta_bits。此结论与攻击策略无关，但不能推广为所有参数、所有时刻的结论；本算例未展示精确标记的历史信息压缩。", "",
              "## 对所有合法攻击有效的半径", "",
              "固定事件历史 h，记 M_t(h)=(I-K_{gamma_t})A。偏差递推逐项展开为 D_k=-sum_{j:gamma_j=1} T_{j,h} a_j，其中 T_{j,h}=M_k ... M_{j+1} K_1(P_j^-)（空乘积为 I）。因此 R_h=sum_j ||T_{j,h}||_2 给出 ||D_k||_2 <= b R_h，无论每个 a_j 如何依赖其允许信息。相同精确标签 P 如由多条历史产生，取 R(P)=max_{h:P(h)=P}R_h；令 B(P)=b_ref R(P)。全零事件历史的 R=0。", "",
              "脚本也计算 r_h=||(I-K_gamma)A||_2 r_parent+gamma||K_1||_2 并确认逐项乘积求和不大于该递推上界。两种半径均依据全类幅值约束，不使用观测到的某个策略的偏差作为半径。", "",
              "## 标签依赖证书的推导", "",
              "令 h(P)=lambda_min(H(P))>0，c(P)=B(P)^2/[1-exp(-h(P)B(P)^2)]；B=0 时用连续延拓 c=1/h(P)。函数 x/(1-exp(-h x)) 在 x>=0 上递增，故在 ||D||<=B(P) 下，c(P)[1-exp(-D^T H(P)D)]>=||D||^2。", "",
              "取 F(P,Y)=tr(P)+c(P)[1-Y/s(P)]。条件静默恒等式给出 E_pi F=E_pi tr(P)+E_pi c(P)[1-exp(-D^T H(P)D)]，健康时 E_0 F=E_0 tr(P)。结合真实损伤分解得到 J_k<=E_pi F-E_0 F<=osc(F) Delta_marked。这里 osc(F) 在全部可达精确标签与 Y=0,1 上取最大值减最小值；全零历史的 c=1/h 是连续延拓，不是必须的最优选择。", "",
              "还单独保留 B(P)=0 时直接令 c(P)=0 的变体。此时所有对应历史下 D=0，所需点态不等式两侧都为零，因此此取值同样有效；它并非上述比例的连续延拓。其余标签不变，两个口径分别计算，不互相替代或混报。", "",
              "这只是现有见证统计量的常数精化，不改变主定理阶数，不宣称新的最优证书定理。", "",
              "## 一次常数对照", "",
              "| 工况 | 原 C_record | 全局 c 的精确振幅 | 局部 h+全局 B | 局部 h+递推 B | 局部 h+乘积 B | 相对原值下降 | 原线性斜率上/下比 | 新线性斜率上/下比 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, case in cases.items():
        v = case["variants"]
        best = v["local_h_product_radius"]
        lines.append(f"| {name} | {case['old_constants_independently_recomputed']['C_record']:.9f} | {v['global_coefficient_exact_oscillation']['constant']:.9f} | {v['local_h_global_radius']['constant']:.9f} | {v['local_h_recursive_radius']['constant']:.9f} | {best['constant']:.9f} | {best['reduction_percent_vs_old']:.4f}% | {case['old_linear_upper_lower_slope_ratio']:.6f} | {best['linear_upper_lower_slope_ratio']:.6f} |")
    lines += ["", "边界处理对照（同一乘积半径，仅改变 B=0 标签的系数）：", "",
              "| 工况 | 连续延拓 c=1/h 的常数 | B=0 时 c=0 的常数 | 后者相对原 C_record 下降 | 后者线性上/下斜率比 |",
              "|---|---:|---:|---:|---:|"]
    for name, case in cases.items():
        v = case["variants"]
        alt = v["local_h_product_radius_zero_on_zero_bias"]
        lines.append(f"| {name} | {v['local_h_product_radius']['constant']:.9f} | {alt['constant']:.9f} | {alt['reduction_percent_vs_old']:.4f}% | {alt['linear_upper_lower_slope_ratio']:.6f} |")
    lines += ["", "线性斜率上/下比为 C*C_pm/L_v，适用于双预算曲线尚未进入幅值平台的部分。完整预算表在 JSON 的 budget_comparison；b=0.1。这里沿用同一个合法两拍构造及解析 TV 充分上界，未把事件位 TV 当成完整载荷日志 TV。", "",
              "## 复现与适用边界", "",
              "运行 `python label_constants_20261019.py`（需 numpy）会重建同名 JSON 和本报告。可用 `--source <稿件目录>` 或 `--source <results.json>` 指定输入，`--output-dir <目录>` 指定输出（默认脚本所在目录）。脚本独立核算原 C_record、C_peak、C_pm、L_v 等并与原结果逐项比较。输入和脚本 SHA-256 保存在 JSON。", "",
              "精确标签数判定属于有理数计算结论；常数差与半径范数数值属于浮点评估。若将具体小数作为严格区间上界发表，仍需定向舍入或区间计算，当前脚本没有作此声称。"]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({name: {"labels": case["exact_label_count"],
                            "old_C": case["old_constants_independently_recomputed"]["C_record"],
                            "new": case["variants"]["local_h_product_radius"],
                            "new_zero_bias": case["variants"]["local_h_product_radius_zero_on_zero_bias"]}
                      for name, case in cases.items()}, indent=2))


if __name__ == "__main__":
    main()
