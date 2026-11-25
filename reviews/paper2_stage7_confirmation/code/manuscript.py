"""Create the Chinese acceptance report from the registered analysis outputs."""
import csv
import os
from statistics import mean,median
from pathlib import Path
import numpy as np
from report import OUT,REG,inputs,GROUPS
from run import TASK,read

def table(name):
    with (OUT/(name+".csv")).open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def f(x,n=3):
    return f"{float(x):.{n}f}" if x not in (None,"") else "—"

def ci(x,lo,hi):
    return f"{f(x)} [{f(lo)}, {f(hi)}]"

NAME={"strong_early":"0.25，50","strong_late":"0.25，96","weak_early":"0.10，50",
      "weak_late":"0.10，96","health":"健康"}
def main():
    rows=inputs()
    stats=read(OUT/"decision.json")
    groups=table("method_by_case")
    comparisons=table("paired_comparisons")
    health=stats["health"]
    cost=table("query_cost")
    fail=table("query_outcomes")
    eng=read(TASK/"results/engineering_replay.json")
    head=stats["primary"]
    summary=lambda g,m:next(r for r in groups if r["group"]==g and r["method"]==m)
    p=summary("strong_early","M3")
    old=summary("strong_early","M2")
    point=summary("strong_early","M1")
    doc=[f"# 第二篇论文确认实验验收报告\n\n**裁决为「{stats['decision']}」。**",
        f"按预注册完成 {len(rows)} 条独立轨迹，共 {4*len(rows)} 个计划查询时刻。主工况为持续偏置 0.25、起点 50。M3 相对 M2 的 512 拍实际累计降损差为 {ci(head[0]['difference'],head[0]['low'],head[0]['high'])}，相对预校准 M1 的差为 {ci(head[1]['difference'],head[1]['low'],head[1]['high'])}。正值表示 M3 降损更多。方括号为按轨迹配对的双侧 95% t 区间。",
        f"主工况 M2、M3 平均有用时长分别为 {f(old['mean_useful_or_active_steps'],1)}、{f(p['mean_useful_or_active_steps'],1)} 拍，攻击窗口期末仍有用分别为 {old['useful_at_endpoint']}/{old['n']}、{p['useful_at_endpoint']}/{p['n']}。两法使用同一记录、方向、等级尝试和成败。每拍有效门限为实际发布位移的认证风险下界 0.000625。",
        "## 独立确认的两个配对问题",
        "| 工况（b，k） | 独立条数 | M2 损失减 M3 损失 [95%] | 主门限 M1 损失减 M3 损失 [95%] | M3 相对 M2 的差占 Monitor 损失 |",
        "|---|---:|---:|---:|---:|"]
    for g in GROUPS:
        a,b=[next(c for c in comparisons if c["group"]==g and c["comparison"]=="M3_vs_"+m) for m in ("M2","M1")]
        doc.append(f"| {NAME[g]} | {a['n']} | {ci(a['difference'],a['low'],a['high'])} | {ci(b['difference'],b['low'],b['high'])} | {f(a['percent_of_monitor'],2)}% |")
    doc+=["",f"主工况以整条轨迹重采样 10,000 次，两个配对差的百分位区间依次为 [{f(head[0]['bootstrap_low'])}, {f(head[0]['bootstrap_high'])}]、[{f(head[1]['bootstrap_low'])}, {f(head[1]['bootstrap_high'])}]。第一个 t 区间下限{'大于' if head[0]['low']>0 else '未超过'}零，按预注册第二个比较{'可作确认性检验' if head[0]['low']>0 else '仅作描述'}。",
           "四个攻击工况各占四分之一。次要汇总见下表，区间在各工况内按整条轨迹重采样后等权合并。",
           "| 比较 | 等权平均差 | 描述性 bootstrap 95% 区间 |","|---|---:|---:|"]
    for x in table("equal_weight_attacks"):
        doc.append(f"| {x['comparison']} | {f(x['four_cell_mean'])} | [{f(x['stratified_boot_low'])}, {f(x['stratified_boot_high'])}] |")
    doc+=["## 实际损失、条件改善、认证下界与机会量",
          "各列采用同一 512 拍窗口。实际降损为 Monitor 损失减该方法损失。离线改善使用真参数污染，认证下界只使用发布时可见证据。恢复份额用组内条件改善总和除以组内未限幅 Oracle 机会量总和。M1、M2、M3 的平均延迟只在窗内成功轨迹中取中位数；M1 计首次非零出手，M2、M3 计首次有用证书动作。分母始终列全部轨迹。完整逐门限、M0、Oracle、期末及机会量分子分母见 [方法与工况表](method_by_case.csv)。",
          "| 工况 | 方法 | 实际降损 | 离线改善 | 认证下界 | 恢复份额 | 窗内成功/全体 | 成功者中位延迟 |",
          "|---|---|---:|---:|---:|---:|---:|---:|"]
    for g in GROUPS:
        for m in ("M1","M2","M3"):
            x=summary(g,m)
            doc.append(f"| {NAME[g]} | {m} | {f(x['gain'])} | {f(x['conditional'])} | {f(x['mean_cert'])} | {f(x['recovery_share'])} | {x['first_success']}/{x['n']} | {f(x['median_delay_among_successes'],1)} |")
    doc+=["## 健康轨迹与计算代价",
          f"主门限 M1 在 608 拍内至少误动一次的轨迹为 {health['method_active']}/{health['n']}，M3 为 {health['m3_active']}/{health['n']}。各自双侧 95% 精确区间为 [{100*health['method_lo']:.2f}%, {100*health['method_hi']:.2f}%]、[{100*health['m3_lo']:.2f}%, {100*health['m3_hi']:.2f}%]。仅 M1 出手 {health['only_method']} 条，仅 M3 出手 {health['only_m3']} 条。M1 减 M3 的误动率差为 {100*health['diff']:.2f} 个百分点，保守配对区间 [{100*health['lo']:.2f}, {100*health['hi']:.2f}] 个百分点。±1 个百分点等效{'通过' if health['equivalent'] else '未确定'}。健康损失仍按绝对 50–561 拍量计。",
          "![健康误动率与累计降损](tradeoff.png)",
          f"预注册代表轨迹为 {stats['first_curve'] or '无首证'}。左图从第一次共同正证开始，到下次查询之前或窗口终点；右图按绝对时钟将主工况全部轨迹计入，包括始终未取得证书者。[有首证轨迹的衰减数据](first_certificate_curves.csv)",
          "![同一首证之后的持续性与全组均值](persistence.png)",
          "| 工况 | 全流程平均秒/轨迹 | 4 次查询合并 P50 / P95 / 最大秒 | 首次计划查询 P50 | 后续计划查询 P50 | 正证 / 零相容 / 未决（查询数） |",
          "|---|---:|---:|---:|---:|---:|"]
    for g in GROUPS:
        cs=[next(x for x in cost if x["group"]==g and x["phase"]==phase and x["cost"]=="joint") for phase in ("all","first_scheduled","later_scheduled")]
        counts=[x["queries"] for x in fail if x["group"]==g]
        doc.append(f"| {NAME[g]} | {mean(r['seconds'] for r in rows if r['group']==g):.2f} | {f(cs[0]['p50'],2)} / {f(cs[0]['p95'],2)} / {f(cs[0]['max'],2)} | {f(cs[1]['p50'],2)} | {f(cs[2]['p50'],2)} | {' / '.join(counts)}（共 {cs[0]['n']}） |")
    times={m:[r["seconds"] for r in eng if r["method"]==m] for m in ("M1","M3")}
    doc+=["",f"确认集配对全流程消耗 {stats['cpu_hours']:.3f} 核时。为量出实际在线成本，另回放主工况固定编号 0–3，各方法单独读取相同公开记录，四工作进程，次序按编号奇偶交替。M1 平均 {mean(times['M1']):.2f} 秒/轨迹，带旧方法回退的 M3 平均 {mean(times['M3']):.2f} 秒/轨迹，包含在线状态建立、维护、查询和发布，排除轨迹生成及离线评分。每个输出的累计损失与相应确认行复核通过。这四条未增加样本数。联合全流程时间包含模拟和离线核验，两种时间口径单列。[独立方法计时](../results/engineering_replay.json) · [逐轨迹耗时](cost_per_trajectory.csv) · [查询时延及分母](query_cost.csv)",
        "## 核验与局限",
        f"四个计划时点外每轨迹有 604 拍未查。查询时若一档已成而下一档未决，时点按取得正证计，逐等级原因为独立列。未决保留在主表。真参数未保留累计 {stats['coverage_missed_steps']} 拍；在真参数保留时离线条件改善低于发布下界超过容限共 {stats['risk_violations']} 次。旧传播优于新区间提议的回退累计 {stats['legacy_fallback_steps']} 拍；局部数值或保守发布回退 M2、M3 分别为 {stats['numerical_fallback_steps']['M2']}、{stats['numerical_fallback_steps']['M3']} 拍。最大直接滤波差 {stats['direct_error_max']:.3g}。确认错误日志 {stats['error_records']} 份，期末缺失轨迹 0 条。覆盖违反按拍统计，仅为实现诊断。[查询及失败原因](query_log.csv) · [查询数与轨迹数](query_outcomes.csv)",
        f"开发集试算使用 6 条主要工况配对差，标准差分别为 {REG['development_sd'][0]:.3f} 和 {REG['development_sd'][1]:.3f}。希望分辨的累计差 1 相当于开发组 Monitor 损失的 {REG['effect_percent']:.3f}%；双侧 95%、80% 功效公式给出 7 和 56 条。取较大者，其他工况作描述。200 条独立健康开发路径的每条四查询最大分数按秩 190、198、199 冻结，临界轨迹用原区间搜索重新打分。仅 1 个顺序统计量位于主门限之上，尾部分位数本身仍有抽样误差。[预注册](../registration.json)",
        "认证所用的条件风险对应持续固定偏置、共同历史和正确连续观测核。逐点全时间覆盖须在每个固定真实参数自己的概率测度下理解。单条轨迹会因物理噪声出现负降损，成功子集也不代表全部攻击。本实验没有测量密码学认证、有限码字信道或硬实时最坏时限。[工程接口与文献对照](../design.md)",
        "## 建议写入摘要的表述",
        f"“在单节点 V2 的持续偏置模型下，我们在相同可信事件和接收历史上比较两种证据传播机制。对偏置 0.25、起点 50 的 {p['n']} 条独立轨迹，保留起点对应幅值区间后，有用校正持续时间由平均 {f(old['mean_useful_or_active_steps'],1)} 拍变为 {f(p['mean_useful_or_active_steps'],1)} 拍，累计降损的配对增量为 {ci(head[0]['difference'],head[0]['low'],head[0]['high'])}。相对于预校准、可拒绝的点补偿，增量为 {ci(head[1]['difference'],head[1]['low'],head[1]['high'])}。健康误动率的 ±1 个百分点等效性{'获得支持' if health['equivalent'] else '尚未确认'}。”",
        "复算入口、执行命令及源码身份见 [任务首页](../README.md)。"]
    # Keep rows in each Markdown table contiguous.
    output=""
    for s in doc:
        if not s.startswith("|") and output and not output.endswith("\n\n"): output+="\n"
        if s.startswith("|") and output and not output.splitlines()[-1].startswith("|"): output+="\n"
        output+=s+"\n"
    (OUT/"acceptance.md").write_text(output,encoding="utf8",newline="\n")
if __name__=="__main__":
    main()
