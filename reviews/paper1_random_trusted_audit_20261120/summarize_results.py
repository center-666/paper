"""Presentation from the frozen run only. No RNG, new trajectories or threshold fitting."""
from pathlib import Path
import csv
import hashlib
import json
import math
import numpy as np

HERE=Path(__file__).resolve().parent
RUN=HERE/"results/run_20261120_v1"
OUT=HERE/"presentation"


def main():
    OUT.mkdir(exist_ok=True)
    cfg=json.loads((HERE/"protocol.json").read_text(encoding="utf-8"))
    rows=list(csv.DictReader((RUN/"single_test_results.csv").open(encoding="utf-8-sig")))
    windows=list(csv.DictReader((RUN/"window_results.csv").open(encoding="utf-8-sig")))
    planner=json.loads((RUN/"quadrature_and_sample_planning.json").read_text(encoding="utf-8"))
    for row in rows:
        for key in ["conditional_detection","per_episode_detection",
                    "conditional_fpr_random_audit","per_episode_fpr_random_audit"]:
            row[key]=json.loads(row[key])
    maxdelta={m["id"]:max(m["delta_grid"]) for m in cfg["models"]}
    def pct(v):
        return "-" if v is None else f"{100*v:.3f}%"
    def ci(v):
        if v["rate"] is None:return "无样本"
        return f"{pct(v['rate'])} [{pct(v['wilson95_low'])}, {pct(v['wilson95_high'])}]"
    def table(head,body):
        return "\n".join(["| "+" | ".join(head)+" |","|"+"---|"*len(head)]+
                         ["| "+" | ".join(map(str,row))+" |" for row in body])+"\n"
    maximum=[r for r in rows if float(r["delta"])==maxdelta[r["model"]]]
    def rget(mid,attack,rho):
        return next(r for r in maximum if r["model"]==mid and r["attack"]==attack
                    and float(r["rho"])==rho)
    txt=["# 冻结运行的完整统计表\n",
         "各比例条件于固定健康校准阈值，方括号为95% Wilson区间；方案之间共享episode，区间不是多重比较保证。没有可用样本不报警，不等同于样本缺失。阈值目标为1%，实测超出不回调。\n",
         "## 最大预设精度：逐可信可用样本\n"]
    txt.append(table(["模型","rho","健康FPR","符号攻击报警率","反射攻击报警率"],[
        [mid,f"{rho:.0%}",ci(rget(mid,"cell_sign",rho)["conditional_fpr_random_audit"]),
         ci(rget(mid,"cell_sign",rho)["conditional_detection"]),
         ci(rget(mid,"balanced_reflection",rho)["conditional_detection"])]
        for mid in maxdelta for rho in cfg["audit_probabilities"]]))
    txt.append("\n## 最大精度：每个基础episode的报警率\n")
    txt.append(table(["模型","rho","FPR/episode","符号报警/episode","反射报警/episode"],[
        [mid,f"{rho:.0%}",pct(rget(mid,"cell_sign",rho)["per_episode_fpr_random_audit"]["rate"]),
         pct(rget(mid,"cell_sign",rho)["per_episode_detection"]["rate"]),
         pct(rget(mid,"balanced_reflection",rho)["per_episode_detection"]["rate"])]
        for mid in maxdelta for rho in cfg["audit_probabilities"]]))
    txt.append("\n## 全精度、全审计比例的条件检验与窗口\n")
    txt.append(table(["模型","delta","攻击","rho","可用样本数","健康FPR","攻击报警率"],[
        [r["model"],f"{float(r['delta']):.9g}",r["attack"],r["rho"],
         r["conditional_detection"]["trials"],ci(r["conditional_fpr_random_audit"]),
         ci(r["conditional_detection"])] for r in rows]))
    txt.append("\n窗口行按互不重叠的独立episode块计算，并非连续系统轨迹。健康标定块数为131072/n，测试块数262144/n。\n")
    txt.append(table(["模型","delta","攻击","rho","块大小","测试块","健康FPR","攻击报警率"],[
        [r["model"],f"{float(r['delta']):.9g}",r["attack"],r["rho"],
         r["episodes_per_nonoverlap_block"],r["blocks_test"],
         ci(json.loads(r["test_fpr"])),ci(json.loads(r["detection_rate"]))]
        for r in windows]))
    (OUT/"all_detection_tables.md").write_text("\n".join(txt),encoding="utf-8",newline="\n")
    txt=["# 损伤、有效样本与成本\n","损伤的MC估计保留单次随机符号/接受及真实物理残差，和解析条件均值估计分列，不能当成逐样本平方恒等式。\n"]
    dmg=[]
    for r in rows:
        if float(r["rho"])!=1:continue
        q=next(e["quadrature32"] for e in planner if "quadrature32" in e
               and e["model"]==r["model"] and e["attack"]==r["attack"]
               and e["delta"]==float(r["delta"]))
        mean=float(r["damage_mean"]);se=float(r["damage_paired_se"]);mse=float(r["healthy_mse"])
        dmg.append([r["model"],f"{float(r['delta']):.9g}",r["attack"],
            f"{mse:.9f}",f"{float(r['attacked_mse']):.9f}",
            f"{mean:.6g} [{mean-1.96*se:.6g},{mean+1.96*se:.6g}]",
            f"{float(r['damage_model_formula_mean']):.6g}",
            f"{q['target_damage']:.6g}",pct(q["target_damage"]/mse),
            pct(float(r["attack_action_rate"]))])
    txt.append(table(["模型","delta","攻击","健康MSE","攻击MSE","J_MC及近似95%区间",
                      "K²a²样本均值","J解析积分","J解析/健康MSE","非零动作率"],dmg))
    txt.append("\n## 最大精度下有效审计与认证包\n")
    txt.append(table(["模型","rho","下一可信载荷/episode","检测可用/episode",
                      "随机认证包/episode","全量认证包/episode","包数相对全量",
                      "16字节标签字节/episode"],[
        [mid,f"{rho:.0%}",pct(float(rget(mid,"cell_sign",rho)["next_payload_audit_fraction"])),
         pct(float(rget(mid,"cell_sign",rho)["paired_usable_fraction"])),
         f"{float(rget(mid,'cell_sign',rho)['auth_packets_random_audit']):.6f}",
         f"{float(rget(mid,'cell_sign',rho)['auth_packets_all_auth']):.6f}",
         pct(float(rget(mid,"cell_sign",rho)["auth_packet_fraction_vs_all_auth"])),
         f"{float(rget(mid,'cell_sign',rho)['tag_bytes_per_episode_illustrative']):.6f}"]
        for mid in maxdelta for rho in cfg["audit_probabilities"]]))
    txt.append("\n随机audit需审计标志控制/记录，每episode一个逻辑位（rho=0或1可确定），其保护、同步和计算成本未测。表中包数节省不代表相同检测收益下成本节省。ALL_AUTH是目标和下一拍都保护的预防基准，rho=1只保护下一拍；两者不可混称。\n")
    txt.append("## 最大精度：80%功效独立episode规划\n")
    planrows=[e for e in planner if "rho" in e and e["delta"]==maxdelta[e["model"]]]
    txt.append(table(["模型","攻击","rho","所需episode近似值","有效成对审计","下一认证包"],[
        [e["model"],e["attack"],e["rho"],
         e["planned_episodes_for_1pct_fpr_80pct_power_normal_approx"] or "不可用",
         round(e["planned_effective_paired_audits"]) if e["planned_effective_paired_audits"] else "-",
         round(e["planned_next_auth_packets"]) if e["planned_next_auth_packets"] else "-"]
        for e in planrows]))
    txt.append("\n## 三档精度：10%审计的样本规划\n")
    txt.append(table(["模型","delta","攻击","所需episode近似值","有效成对审计","下一认证包"],[
        [e["model"],f"{e['delta']:.9g}",e["attack"],e["planned_episodes_for_1pct_fpr_80pct_power_normal_approx"],
         round(e["planned_effective_paired_audits"]),round(e["planned_next_auth_packets"])]
        for e in planner if e.get("rho")==.1]))
    txt.append("\n规划依赖正确模型、重复同一攻击机制、独立重置样本与正态近似，不是在线时间窗或已实测80%功效。它不改变实测健康门限，也没有生成规划值所指的大量样本。\n")
    (OUT/"damage_cost_sample_size.md").write_text("\n".join(txt),encoding="utf-8",newline="\n")
    # SVG point-and-interval chart: fixed largest precision for each model.
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="520" viewBox="0 0 1100 520">',
           '<rect width="1100" height="520" fill="white"/>',
           '<style>text{font-family:Arial,sans-serif;fill:#222;font-size:13px}</style>',
           '<text x="550" y="25" text-anchor="middle" font-size="18">Random audit: single usable-sample alarm rates at the largest frozen precision</text>']
    for col,mid in enumerate(maxdelta):
        x0=75+col*540;y0=65;w=425;h=330; ymax=.025
        Y=lambda v:y0+h-h*v/ymax
        for val in [0,.005,.01,.015,.02,.025]:
            yy=Y(val);parts.append(f'<path d="M{x0},{yy}H{x0+w}" stroke="#ddd"/>')
            parts.append(f'<text x="{x0-8}" y="{yy+5}" text-anchor="end">{val*100:.1f}%</text>')
        parts.append(f'<path d="M{x0},{Y(.01)}H{x0+w}" stroke="#555" stroke-dasharray="5 4"/>')
        parts.append(f'<text x="{x0+w/2}" y="52" text-anchor="middle">{mid}, delta={maxdelta[mid]:.6f}</text>')
        rates=[.05,.1,.2,1]
        for i,rho in enumerate(rates):
            xx=x0+50+i*100
            parts.append(f'<text x="{xx}" y="{y0+h+23}" text-anchor="middle">{rho:.0%}</text>')
            for offset,color,key,attack in [(-11,"#444","conditional_fpr_random_audit","cell_sign"),
                                          (0,"#2171b5","conditional_detection","cell_sign"),
                                          (11,"#c43b3b","conditional_detection","balanced_reflection")]:
                r=rget(mid,attack,rho)[key]
                cx=xx+offset; low,high=r["wilson95_low"],r["wilson95_high"]
                parts.append(f'<path d="M{cx},{Y(low)}V{Y(high)} M{cx-3},{Y(low)}H{cx+3} M{cx-3},{Y(high)}H{cx+3}" stroke="{color}"/>')
                parts.append(f'<circle cx="{cx}" cy="{Y(r["rate"])}" r="4" fill="{color}"/>')
        parts.append(f'<text x="{x0+w/2}" y="445" text-anchor="middle">Audit probability rho (next payload only)</text>')
    for x,color,label in [(130,"#444","Healthy FPR"),(360,"#2171b5","Cell-sign attack"),(600,"#c43b3b","Balanced reflection")]:
        parts.append(f'<circle cx="{x}" cy="480" r="4" fill="{color}"/><text x="{x+12}" y="485">{label}</text>')
    parts.append('<text x="550" y="510" text-anchor="middle">Bars: 95% Wilson intervals. Dashed: nominal 1%. No post-test threshold adjustment.</text></svg>')
    (OUT/"detection_rates.svg").write_text("".join(parts),encoding="utf-8")
    # Summaries used by the narrative and read-back verification.
    summary={"quadrature_max_difference":max(e["mean_score_abs_diff"] for e in planner if "mean_score_abs_diff" in e),
             "quadrature_max_second_moment_difference":max(e["second_moment_abs_diff"] for e in planner if "second_moment_abs_diff" in e),
             "test_rows":len(rows),"window_rows":len(windows),
             "raw_input_hashes":json.loads((HERE/"input_manifest.json").read_text())["files"],
             "outputs_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name!="presentation_manifest.json"},
             "new_simulation":False,"thresholds_recalibrated":False}
    (OUT/"presentation_manifest.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({k:v for k,v in summary.items() if k not in ("outputs_sha256","raw_input_hashes")},ensure_ascii=True))


if __name__=="__main__":
    main()
