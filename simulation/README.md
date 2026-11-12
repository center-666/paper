# 五节点安全分布式估计研究工程

2026-11-12 增加了与旧稿衔接的独立代数核验，**不改五节点主模型**：可达方向/多拍静默推导见[研究报告](../literature_review/可达攻击方向与多拍静默损伤界_推导稿_2026-11-12.md)，480 项精确秩与独立高斯积分在 [reachable-silence 结果](checks/2026-11-12_reachable_silence_screen_v2/results.json)，16 组真实目标损伤解析核验在[独立审计](checks/2026-11-12_reachable_silence_atom_audit/audit.json)。共享时隙候选未超过动态 EDF，见[筛选停止报告](checks/2026-11-12_shared_channel_deadline_screen/REPORT.md)。这些都不是新的状态估计 Monte Carlo 结果。

2026-11-11 新增有限探索：参考污染恢复、缓存驻留相关统计、正确均值强基准和年龄价值对齐。最新决策与运行目录见[连续验证报告](../literature_review/增量候选筛选与连续验证_2026-11-11.md)及[稳态误隔离/CUSUM 综合报告](../literature_review/稳态误隔离校准与CUSUM强基准结论_2026-11-11.md)。当前可用模型构造器支持显式二维 H/R 矩阵；这不等于已证明一般局部不可观测理论。

最新：已完成独立复查和扩展验证，正式的同数据尾部消融见[纠正后验证报告](validation_runs/2026-11-10_shared_data_v2/REPORT.md)，综合判断见[复查与验证结论](../literature_review/模型复查与验证结论_2026-11-10.md)。9项主要比较均未达到预设1%改善门槛，当前不继续包装尾部分组为主创新。

最新序贯验证已另存为 [第一轮强基准](validation_runs/2026-11-11_sequential_strong_v1/REPORT.md) 和 [跨消息 CUSUM 公平审计](validation_runs/2026-11-11_cusum_carry_v1/REPORT.md)。第一轮整体门槛为 1/4 场景单元，补充审计主边 step 为 3/4，二者不能合并解读为整体通过。

定向查新后的秩亏量测压力验证见 [报告](validation_runs/2026-11-11_partial_observability_probe_v4/REPORT.md)：主边 step 的 4 项比较均未通过，结果只保留为候选边界，不再继续扩展算法模块。

已搭建并运行。它是**参考论文构造、明确记录改编的研究模型**，不是对原论文全部设定或图表的严格复现。

首轮结果：[REPORT.md](runs/2026-11-10_five_node_v2/REPORT.md)。研究判断见[首轮贡献评估](../literature_review/五节点模型搭建与首轮贡献评估.md)。

当前 v2 已修正 Zhou 随机保护为同一接收节点共享当步随机门限；v1 按边独立抽样的旧输出保留但不再作为当前对照。模型、攻击和种子未因结果改动。版本说明见 [VERSION_NOTES.md](runs/2026-11-10_five_node_v2/VERSION_NOTES.md)。

## 一键运行

在项目根目录 PowerShell 执行：

```powershell
.\simulation\run.ps1 -RunId five_node_repeat_01
```

或者分别执行：

```powershell
.\.venv\Scripts\python.exe simulation\verify.py --config simulation\config.json --output simulation\verification_new.json
.\.venv\Scripts\python.exe simulation\run_study.py --config simulation\config.json --run-id five_node_repeat_01
.\.venv\Scripts\python.exe simulation\analyze_increment.py simulation\runs\five_node_repeat_01
```

运行标识必须是新名称，已有实验目录不会覆盖。首轮 Python 3.14.9 环境建在项目 `.venv/`，未改系统默认解释器。依赖版本在 [requirements-lock.txt](requirements-lock.txt)；迁移时先创建虚拟环境，再安装该文件。若使用不同 Python/数值库，结果可能有浮点或随机数实现差异，应另存环境记录。

扩展验证（使用固定的新样本计划及严格共享校准数据的两方法消融）可运行：

```powershell
.\simulation\validate.ps1 -RunId validation_repeat_01
```

这会重现预设研究，不应被用来反复更换测试参数筛选正面结果。它依次保存九方法部署比较、两方法共享校准数据消融和输出审计。主要有效性结论看第二步，原因见首批 [STATUS.md](validation_runs/2026-11-10_locked_v1/STATUS.md)。

重新建环境的通用方式：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r simulation\requirements-lock.txt
```

若本机有 uv，也可用 `uv venv` 和 `uv pip install --python .venv\Scripts\python.exe -r simulation\requirements-lock.txt`。现有 `.venv` 不需要再次安装。

## 论文依据与自行设定

| 部分 | 来源或处理 |
|---|---|
| 更新结构 | Yang 等 2014，DOI 10.1016/j.automatica.2014.05.025；用时刻 t 的量测/邻居估计更新 t+1 |
| 名义增益 | 原结构全量通信 q=1 情形的联合误差最小方差推导；显式保留跨节点误差协方差 |
| 随机保护对照 | Zhou 等 2022，DOI 10.1016/j.automatica.2021.110151 的指数随机门限机制移植，另加共同裁剪/缓存；不是原完整方法复现 |
| 系统矩阵 | A=1.01I，与原文数值风格相同 |
| 规模与噪声 | 5 节点、n=2、T=400、Q=0.02I、R_i=0.05I，采用此前讨论的研究配置，非原论文 30 节点与 Q=2I |
| 量测/拓扑 | 自行明确设定 H_i=(1,0.8,1.2,0.9,1.1)_i I；双向五节点环网；epsilon=0.08 |
| 通信 | 每步本地量测可用；状态估计 Send-on-Delta 与最大间隔 10，替代原文量测/发送随机激活 |
| 缓存 | 以接收时刻推演 A^age m；每包权重保持到下一包；原始上一收到载荷用于时间残差，不以“判为可信”冒充真实来源 |
| 攻击 | 一条有向边 0→1 的实际发送载荷被替换，本地量测不变；时间 200–249，偏置 [1.2,-0.8]，Replay 滞后 8 个实际历史包 |

全状态量测使各节点均可独立估计。该模型适合先排查机制和校准，但不能用于证明局部不可观测情形下的分布式安全理论。若后来改为部分可观测模型，增益、稳定条件、裁剪影响都需重新检验。

## 增益与误差模型

设 L 是接收邻接对应的入度 Laplacian，

\[
B=(I-\varepsilon L)\otimes A,
\qquad
K_i=(BP)_{ii}H_i^\top(H_iP_{ii}H_i^\top+R_i)^{-1}.
\]

令 F=B−diag(K_i H_i)，名义全量通信误差协方差递推为

\[
P^+=FPF^\top+\mathbf1\mathbf1^\top\otimes Q
+\operatorname{diag}(K_iR_iK_i^\top).
\]

过程噪声是同一个真实系统对全网共有的输入，所以使用全 1 矩阵 Kronecker Q，不是独立节点过程噪声。初始估计全为零，P(0)=11ᵀ⊗P0。

事件触发/攻击/权重/裁剪运行共用预先生成的**名义**增益序列，不声称仍是精确最优增益。无邻居的本地基准单独计算 epsilon=0 的增益。

## 方法、数据与运行方式

8 个方法：Yang 型主干、本地估计、仅裁剪、空间硬拒绝、统一标定、分间隔尺度归一化、进一步分间隔尾部标定、Zhou 随机保护机制移植。

前两者无裁剪；其他方法共用从正常训练数据确定的 99.5% 裁剪阈值。三个连续权重版本共用 alpha=0.5、同一评分/融合骨架，不加入历史记忆。

训练/标定/验证/测试分别为 48/48/24/32 个独立种子。训练协方差与标定分位数分开；两轮正常闭环重标定、三轮验证参数更新后冻结。正常目标为新包 w<0.5 比例 5%，同时报告平均权重和实际测试偏差。

发送协议：

- `reference_schedule`：从各种子无攻击 Yang 型参考运行记录发送时刻，各方法/攻击共享该日程；不是从受攻击轨迹决定机会。
- `closed_loop`：各方法自己运行同一触发规则，攻击可能通过估计改变后续发送，但不能直接操控调度器。记录实际通信，不声称已精确同成本。

每种协议 8 方法×4 场景×32 种子，共 2,048 条测试方法轨迹，按种子配对；这些共享真值/噪声，不能当作 2,048 个互相独立统计样本。

场景是正常、突变 FDI、缓变 FDI、历史包重放。暂未做匹配间隔历史片段、低幅隐蔽、多方向攻击、异质噪声敏感性和部分可观测压力模型。

后续扩展已补低幅突变、固定80步匹配历史间隔Replay、三档通信压力和重复不规则日程；仍未做一般隐蔽最坏攻击、异质噪声敏感性或局部不可观测模型。扩展使用新128种子，不能把24,192条方法轨迹当独立样本。

## 工程文件

| 文件 | 内容 |
|---|---|
| [config.json](config.json) | 所有系统、攻击、标定参数与种子范围 |
| [model.py](model.py) | 系统数据和包含互相关的名义增益 |
| [engine.py](engine.py) | 因果更新、实际发送、合法攻击、缓存与指标 |
| [calibration.py](calibration.py) | 独立正常数据标定与验证参数 |
| [verify.py](verify.py) | 联合协方差 Monte Carlo、攻击时序、重放来源等检查 |
| [run_study.py](run_study.py) | 完整预定流程、结果与源码快照 |
| [analyze_increment.py](analyze_increment.py) | 已冻结结果的配对超额损失分析与输出审计 |
| [report.py](report.py) | 表格与可导出 PNG/PDF 图 |
| [validation_plan.json](validation_plan.json) | 新测试前固定的设置、判据与停止条件 |
| [validation_suite.py](validation_suite.py) | 全方法扩展与分时间窗诊断 |
| [corrected_tail_pair.py](corrected_tail_pair.py) | 同一批正常残差、相同其他统计量的严格尾部消融；另用新测试种子 |
| [validation_summary.py](validation_summary.py) | 主要9项Holm检验、实用差异界、正常代价与边界报告 |
| [validation_output_audit.py](validation_output_audit.py) | 从保存的残差/轨迹复核q、MSE、源包和哈希 |
| [independent_checks.py](independent_checks.py) | 非对角矩阵、独立协方差、手算缓存及真值不可见检查 |
| [reference_screen.py](reference_screen.py) | 前包污染恢复候选与空间/重置强基准，计划reference_exploration_plan.json |
| [cache_monitor.py](cache_monitor.py) | 同缓存相关前缀的瞬时/联合能量/GLS/正确协方差均值统计；episode-max正常校准 |
| [cache_screen.py](cache_screen.py) | 缓存证据筛选、纯正常选择年龄权重与检测门限；各运行保留独立计划 |
| [cache_aged_confirmation.py](cache_aged_confirmation.py) | 所有检测器共享正常数据选出的年龄权重，排除信息价值管理的混淆 |
| [audit_exploration_outputs.py](audit_exploration_outputs.py) | 保存轨迹与MSE、源包、哈希、数据划分复算；无新模拟 |
| [run_partial_observability_probe.py](run_partial_observability_probe.py) / [audit_partial_observability_probe.py](audit_partial_observability_probe.py) | 秩一交替量测压力验证及独立输出审计；结果见对应 validation_runs 目录 |

## 已完成的验证及结果限制

- 4,000 次独立全量通信试验的联合协方差相对误差约 2.02%；网络 MSE 理论值 0.084064、样本值 0.084294。
- 验证了无限裁剪阈值恢复主干、初始/攻击时序、无攻击外生日程重放一致性、本地基准不受通信攻击影响。
- 审计保存的 64 组结果：种子拆分、发送日程、有限数值/权重范围、真实历史包来源及报告 MSE 与保存轨迹一致。
- 这验证的是实现与声明模型一致，不是所有参考论文的完整复现。

首轮没有支持“分间隔尾部具有稳定 MSE 增量”的结论。结果与失败对照均保存在运行目录，不依据测试结果更改参数再覆盖原结果。
