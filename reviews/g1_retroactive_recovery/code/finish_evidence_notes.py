from pathlib import Path
B=Path(__file__).resolve().parents[1]

def write(name,text):
    (B/name).write_text(text.strip()+"\n",encoding="utf-8")

p=B/"01_literature_gap.md"
s=p.read_text(encoding="utf-8")
s=s[:s.index("## 闭环传播审计")]
s+="""
## 当前实验与方法排重

最终P0结果为g1r_p0_verified_20261113_v1，详见07/08。固定外生日程全时域、
两单位响应、合法缓存通道已通过独立验证。mapping_04仅到q前；output_channels_02
越权使用未发送sender状态；本轮中间04–07响应矩阵方向错误，性能及旧P0假通过均撤回。

同窗口合法cache分歧与local的MSE配对区间跨零，正常误修正风险未匹配，
不能声称已有公平算法优越性。完整窗口与post窗口数据量不同，仅作信息量诊断。
GLS同窗递推等价是标准代数，不是原Deghat式(18)动态detector。
P1逐式映射见09：辅助误差估计通信、离散cache增广、H∞条件和持续白噪声差别
使当前尚未形成忠实性能适配。没有把“无法直接套原LMI”称为数学上不可能离散化。

维持终止当前GLS/influence-capsule独立创新，保留基础恢复机制；最终决策见10。
"""
write(p.name,s)

write("05_minimal_experiment.md",r"""
# 实验结果及证据撤回（2026-11-13）

最终P0运行：
[g1r_p0_verified_20261113_v1](results/g1r_p0_verified_20261113_v1)。
完整配置、seed、源哈希、全部状态/缓存分量、正常误修正MSE见该目录。
方法/时序与边界见[07](07_full_horizon_propagation_audit.md)、
[08](08_information_permission_audit.md)。

## 现象与修正边界

五节点原异质模型，gap8公共日程，单边0→1，r=200、q=208、d=216、T=280。
恢复窗状态217–260，MSE是状态平方范数和，网络再平均5节点，没有除以状态维数2。
健康receiver/network MSE=0.206899/0.184455。
未保护Replay恢复excess=0.816381/0.244695，单次FDI=0.000719/0.000485。
后续未篡改sender包仍能带网络反馈污染，已在全时域独立差分中验证。

旧minimal_screen_02里receiver drop-and-replay恢复excess约0.146311，
本地滤波checkpoint基线约0.062821；它们基于固定实际入包日志继续运算，
没有让校正回写后重建其他节点发送，不能称为全网闭环恢复。
本轮标准GLS同样只形成影子输出；全网影子结果是离线评价。

## 合法缓存A/B对照

沿用64训练、48校准、48测试seed；ridge=.02，正常95%分位数。
A为本地innovation，B增加实际收到的aligned cache分歧；事件边/时刻oracle已知。

| Replay影子输出 | receiver excess | network excess | normal误修正率 |
|---|---:|---:|---:|
| full A | -0.003048 | -0.001216 | 4.17% |
| full B | 0.000074 | 0.000051 | 6.25% |
| post A | 0.009752 | 0.002766 | 2.08% |
| post B | 0.000875 | -0.000462 | 0% |

同窗口B-A接收MSE配对区间：full[-0.002718,0.008963]，
post[-0.017907,0.000154]，均跨零。FPR未匹配，不能公平排名；
full17拍与post8拍不能用MSE声称结构优越。样本重复研究且无多重校正。
标准GLS同窗递推等价batch的旧代数结论保留，但不构成新机制或Deghat复现。

特征新增消息0字节，原通信179次广播/358边包/5728字节；
full A/B历史272/544B，post A/B为128/256B，拟合矩阵成本见08。
稠密白化仍需历史，不能称全算法仅48B。全网修正广播和内部回写未实现。

## 失败及旧数值状态

| Run | 状态 |
|---|---|
| mapping_01/02 | 循环式核验；原JSON伪CSV保留 |
| mapping_03 | 回灌实际sender差，不独立 |
| mapping_04 | 独立但仅r..q-1；不验证q后 |
| mapping_05 | 导出失败 |
| mapping_06 | 全时域但per-seed扩展名错误 |
| mapping_07/08 | 全时域中间记录，最终入口已更新 |
| output_channels_01 | 未启用分歧分支 |
| output_channels_02 | augmented读取未发送sender状态，仅作额外信息对照 |
| 本轮output_channels_04–07 | 缓存来源合法，但响应矩阵方向错，修正MSE撤回 |
| p0_final_audit_02–05 | 漏查响应矩阵，完整P0 PASS撤回 |

最终Run在计算MSE前核验两单位方向响应；全时域节点/缓存差最大2.31e-13。
所有旧Run均保持原样；正确格式副本位于g1r_format_repair_20261113_v1，
含原文件哈希，格式修复不恢复旧科学有效性。不将多次重跑合并为独立样本。
""")

write("06_research_decision.md",r"""
# 研究决定（最终审计入口）

2026-11-13。**终止post-cache GLS/influence-capsule作为独立创新，
保留后续可信量测验证历史邻居数据及修正污染的基础机制。**

本轮最终证据仅g1r_p0_verified_20261113_v1；旧mapping_04的q后独立验证声明、
output_channels_02的合法信息主张及本轮中间04–07的修正MSE均撤回。
P0详细验收见07、08；原文件/负结果保留。

单枚合法Replay在固定日程下能产生显著残余污染；合法本地数据可支持已知事件的
标准GLS影子输出修正，但未完成未知事件定位、全网内部回写或闭环SoD验证。
方法层面仍是标准传播和GLS，正常误修正率未匹配，未显示新机制的公平优势。

P1已完成Deghat逐式映射及离散误差输出方程核验；由于辅助误差估计消息缺失、
新离散cache设计与噪声条件不同，未完成忠实性能适配，不作Deghat性能排名。
这不等于宣称现有文献已公平证明完全解决该问题。

完整P1结论见[09](09_deghat_discrete_baseline.md)，
最终P2判断及五项回答见[10](10_final_research_decision.md)。
当前不重开G1-R，不增加算法模块、不撰写新稿。G2文件保持原样。
""")

p=B/"03_candidate_methods.md";s=p.read_text(encoding="utf-8")
a=s.index("## 当前排序");b=s.index("## 2026-11-13",a)
s=s[:a]+"""## 当前排序

当前A、B、C均没有通过独立创新验收，不再保留A为立题候选。
保留基本历史验证/修正机制；具体原因见08–10，不把停止GLS独立创新扩大为停止整个恢复问题。

"""+s[b:]
write(p.name,s)
print("Removed conflicting current claims; retained all run artifacts.")
