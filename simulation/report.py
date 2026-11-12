from __future__ import annotations
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

LABELS={"yang":"Yang-form nominal", "local":"Local estimator", "capped":"Cap only",
        "spatial_hard":"Spatial gate + cap", "pooled":"Pooled calibration + cap",
        "interval_scale":"Gap scale + pooled tail", "interval_tail":"Gap scale + gap tail",
        "zhou_random":"Zhou-mechanism + cap"}
CN={"yang":"Yang 型名义主干","local":"独立本地估计","capped":"仅裁剪",
    "spatial_hard":"空间硬拒绝＋裁剪","pooled":"统一尺度/尾部",
    "interval_scale":"分间隔尺度/统一尾部","interval_tail":"分间隔尺度/尾部",
    "zhou_random":"Zhou 随机保护移植＋裁剪"}
SCENARIOS={"clean":"No attack","step":"Step FDI","ramp":"Ramp FDI","replay_packet":"Historical packet replay"}


def save(fig,path):
    fig.savefig(path.with_suffix(".png"),dpi=160,bbox_inches="tight")
    fig.savefig(path.with_suffix(".pdf"),bbox_inches="tight")
    plt.close(fig)


def build_report(folder):
    folder=Path(folder)
    cfg=json.loads((folder/"config.json").read_text(encoding="utf-8"))
    summary=json.loads((folder/"summary.json").read_text(encoding="utf-8"))
    get={(r["protocol"],r["method"],r["scenario"]):r for r in summary}
    plots=folder/"figures";plots.mkdir(exist_ok=True)
    methods=cfg["methods"]
    with np.load(folder/"mse_curves.npz") as curves:
        fig,axs=plt.subplots(2,2,figsize=(13,8),sharex=True)
        for ax,scenario in zip(axs.ravel(),cfg["test_scenarios"]):
            for m in methods:
                z=curves["reference_schedule__"+m+"__"+scenario]
                ax.plot(np.arange(cfg["T"]+1)[cfg["warmup"]:],z[cfg["warmup"]:],label=LABELS[m],linewidth=1.3)
            if scenario!="clean":ax.axvspan(cfg["attack"]["start"]+1,cfg["attack"]["end_inclusive"]+1,color="gray",alpha=.12)
            ax.set_title(SCENARIOS[scenario]);ax.set_ylabel("Network MSE (squared vector norm)");ax.grid(alpha=.2)
        axs[1,0].set_xlabel("Estimate index");axs[1,1].set_xlabel("Estimate index")
        handles,labels=axs[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc="lower center",ncol=4,fontsize=8,bbox_to_anchor=(.5,-.03))
        fig.suptitle("Paired comparison with the same externally fixed sending schedule",fontsize=13)
        fig.tight_layout(rect=(0,.03,1,.96));save(fig,plots/"mse_reference_schedule")
    with (folder/"normal_group_metrics.csv").open(encoding="utf-8-sig",newline="") as f:groups=list(csv.DictReader(f))
    fig,axs=plt.subplots(1,2,figsize=(12,4),sharey=True)
    for ax,protocol in zip(axs,("reference_schedule","closed_loop")):
        for m in ("pooled","interval_scale","interval_tail","zhou_random","spatial_hard"):
            vals=[]
            for b in range(len(cfg["interval_upper_bounds"])):
                r=[z for z in groups if z["protocol"]==protocol and z["method"]==m and int(z["interval_bin"])==b]
                vals.append(sum(float(z["low_weight_rate"])*int(z["n"]) for z in r)/sum(int(z["n"]) for z in r) if r else np.nan)
            ax.plot(range(len(vals)),100*np.asarray(vals),marker="o",label=LABELS[m])
        ax.axhline(100*cfg["normal_low_weight_target"],linestyle="--",color="gray",linewidth=1)
        ax.set_xticks(range(5),["1","2","3-4","5-7","8-10"]);ax.set_xlabel("Inter-reception gap group");ax.set_title(protocol);ax.grid(alpha=.2)
    axs[0].set_ylabel("Normal packets with weight < 0.5 (%)")
    axs[1].legend(fontsize=8);fig.tight_layout();save(fig,plots/"normal_low_weight_by_gap")
    fig,axs=plt.subplots(2,2,figsize=(11,8))
    for ax,scenario in zip(axs.ravel(),cfg["test_scenarios"]):
        for k,m in enumerate(methods):
            r=get["closed_loop",m,scenario]
            ax.scatter(r["edge_messages"],r["mse_attack_window"],label=LABELS[m],s=45)
            ax.annotate(str(k+1),(r["edge_messages"],r["mse_attack_window"]),fontsize=8,xytext=(4,4),textcoords="offset points")
        ax.set_title(SCENARIOS[scenario]);ax.set_xlabel("Actual edge messages per trial");ax.set_ylabel("MSE in indices 201-250");ax.grid(alpha=.2)
    handles,labels=axs[0,0].get_legend_handles_labels();fig.legend(handles,[str(i+1)+": "+s for i,s in enumerate(labels)],loc="lower center",ncol=3,fontsize=8,bbox_to_anchor=(.5,-.03))
    fig.suptitle("Closed-loop trigger: communication costs are measured, not matched")
    fig.tight_layout(rect=(0,.04,1,.96));save(fig,plots/"closed_loop_cost_performance")

    lines=["# 五节点研究模型：首轮实验记录","",
        "本结果来自参考论文自行构造的研究模型，不是 Yang 2014/Zhou 2022 全文算法与原图的严格复现。参数在测试前写入配置，测试结果不用于再次调参。",
        "","## 模型与权限","",
        "- 5 节点双向环网，二维状态；A=1.01I、Q=0.02I、R_i=0.05I，H_i 为配置中的满秩尺度矩阵。该模型各节点均可独立观测，不能宣称证明了局部不可观测协同优势。",
        "- q=1 全量通信下联合协方差递推生成时变名义增益，包含共同过程噪声与跨节点误差相关。事件触发/缓存/非线性防御后不再宣称该增益最优。",
        "- 本地基准重新计算无协同的本地增益。空间门限、三种标定与 Zhou 机制移植共用同一名义主干和固定裁剪阈值。",
        "- 发送触发为当前估计相对上次真实发送估计的平方欧氏距离；最大间隔 10。首包初始化。只有实际发送时攻击可替换 0→1 载荷；正常量测不被修改。",
        "- Replay 使用该方法自身实际发送历史中的第 8 个此前包；不是未发送内部估计，也不是固定时间延迟。尚未实现间隔匹配历史片段的困难测试。",
        "- 更新 t+1 使用 t 的量测与缓存；注入 t=200…249，对应估计损失窗口 201…250。旧恶意缓存可在攻击窗口结束后继续影响更新。",
        "","## 数据与校准","",
        f"- 训练 {cfg['train_seeds']['count']}、标定 {cfg['calibration_seeds']['count']}、验证 {cfg['validation_seeds']['count']}、测试 {cfg['test_seeds']['count']} 个独立种子，具体范围见 config.json。",
        "- 每条边分组标定；样本不足的组回退到全局统计，记录在 calibration_counts.csv。",
        "- 开发阶段做两次正常运行分布重标定及三次验证集控制参数更新，最后另跑验证；有限轮迭代不等于已证明达到闭环统计固定点。",
        "- 连续权重目标是正常新包 w<0.5 的比例约 5%；Zhou 移植为随机接纳，匹配拒绝比例。两者平均权重可能不同，表中同时报告，不能仅以一个误报率认定信息损失完全相同。",
        "- 所有防御参数只使用正常训练/标定/验证数据。只有裁剪阈值从共同训练基准的正常一致性差异 99.5% 分位数确定，所有裁剪方法共用。",
        "- Reference schedule 来自各种子无攻击 Yang 型参考轨迹，随后对所有通信方法固定；closed loop 则允许真实估计改变未来发送。后者尚未做通信率阈值匹配，不能声称同成本优越。",
        "","## 相同发送时刻的主要结果","",
        "网络 MSE 定义为各节点状态误差平方范数的平均（不是再除以状态维数）。正常 MSE 使用去除前 50 步后的全窗口；攻击列使用估计 201–250。",
        "","| 方法 | 正常 MSE | 突变 FDI | 缓变 FDI | 历史包 Replay | 正常低权重率 | 正常平均接收权重 |","|---|---:|---:|---:|---:|---:|---:|"]
    for m in methods:
        c=get["reference_schedule",m,"clean"]
        vals=[get["reference_schedule",m,s]["mse_attack_window"] for s in ("step","ramp","replay_packet")]
        low="—" if c["received_low_weight_rate"] is None else f"{100*c['received_low_weight_rate']:.2f}%"
        mean="—" if c["mean_received_weight"] is None else f"{c['mean_received_weight']:.3f}"
        lines.append(f"| {CN[m]} | {c['mse_all']:.6f} | {vals[0]:.6f} | {vals[1]:.6f} | {vals[2]:.6f} | {low} | {mean} |")
    lines += ["","## 关键增量的配对差异","","负值表示分间隔尾部版本损失更小。区间按独立种子配对 bootstrap，未作多重比较校正，仅作探索性判断。","",
              "| 发送协议 | 场景 | 对照 | 配对 MSE 差 | 95% bootstrap 区间 |","|---|---|---|---:|---|"]
    with (folder/"paired_comparisons.csv").open(encoding="utf-8-sig",newline="") as f:comparisons=list(csv.DictReader(f))
    for r in comparisons:
        if r["baseline"] not in {"interval_scale","zhou_random","capped"}:continue
        lines.append(f"| {r['protocol']} | {r['scenario']} | {CN[r['baseline']]} | {float(r['paired_mean_difference']):+.6f} | [{float(r['bootstrap95_low']):+.6f}, {float(r['bootstrap95_high']):+.6f}] |")
    lines += ["","## 图表和复核材料","",
        "- [相同发送日程 MSE](figures/mse_reference_schedule.png)",
        "- [正常分间隔低权重率](figures/normal_low_weight_by_gap.png)",
        "- [闭环实际通信—误差](figures/closed_loop_cost_performance.png)",
        "- per_seed_metrics.csv：逐种子损失、正常代价、消息/载荷字节数、直接攻击包降权及运行时间。",
        "- paired_comparisons.csv：分间隔尾部与尺度/统一/Zhou/仅裁剪/本地基准的配对差异。",
        "- 每个协议目录内 NPZ：所有测试估计轨迹、权重、发送日志、恶意缓存、注入掩码和 Replay 源时刻。",
        "- test_inputs.npz：共同测试真值、量测、种子及参考日程。sources/ 和 environment.json：源码快照、哈希与环境。",
        "","## 必须保留的限制","",
        "1. 单个自行设定模型、单条边、固定攻击方向和幅值、32 个测试种子，不构成论文级完整实验或普遍结论。",
        "2. Zhou 是随机保护机制移植，加入公共裁剪、名义增益与缓存保持；不是对原文完整方法的胜负判定。",
        "3. 暂不加入可信度历史记忆，从而优先隔离标定作用；该研究模型不等于最初全部模块的 IR-TCF。",
        "4. 正常校准、通信匹配和真正的 MSE 改善必须分别审查；仅误降权率变均衡不是独立安全贡献。",
        "5. 若本地估计或简单保护器已经更好，应按结果收缩主张。没有性能门槛通过就不写成有效性已证。"]
    (folder/"REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("run_folder");a=p.parse_args();build_report(a.run_folder)
