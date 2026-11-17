# G1 Task 1.0：历史闭环模型重构

日期：2026-11-17。范围：只读数学重构与确定性验证；不运行仿真、不生成Seed、不改共享代码。

标记：FACT 为历史代码、配置或 Task 0.5 数据直接支持；DERIVED 为在给定假设下推导；HYPOTHESIS 为待验证假设；OPEN 为证据缺口。

## 冻结模型

**FACT。** 本任务继承历史闭环 `five_node_v2`，不是后期 G1-R 的上三角异质模型。历史配置为

\[
A=1.01I_2,\quad Q=0.02I_2,\quad P_0=I_2,
\quad R_i=0.05I_2,
\]
\[
H_i=s_iI_2,\quad(s_0,s_1,s_2,s_3,s_4)=(1,0.8,1.2,0.9,1.1),
\quad \varepsilon=0.08.
\]

拓扑是双向环，边按 sender→receiver 排列：

\[
(0,1),(1,0),(1,2),(2,1),(2,3),(3,2),(3,4),(4,3),(4,0),(0,4).
\]

SoD 参数是 \(\theta=0.12\)（平方距离阈值）、\(T_{\max}=10\)，\(k=0\) 全节点强制发送。出处：历史 `simulation/runs/2026-11-10_five_node_v2/config.json`；Task 0.5 [01_data_integrity_audit.json](../task0_5/01_data_integrity_audit.json)。

**FACT。** 历史闭环调用传入 `schedule=None`，所以发送事件由历史 `sources/engine.py` 的 SoD/timeout 路径产生。历史源码的 SHA256 与 `environment.json` 一致；Task 0.5 配对审计确认两臂使用同一 `testseeds` 和同一 `x,y` 来源。出处：Task 0.5 [02_seed_pairing_audit.md](../task0_5/02_seed_pairing_audit.md)。

## 时序

**FACT。** 每个时刻先取 \(\hat x_i(k)\)，计算本地创新与本地更新候选；发送判决只读取当前 pre-measurement 估计、上次发送参考和上次发送时刻。发送判决完成后更新发送参考，随后才在目标真实发送机会替换 Replay 载荷，再覆盖接收缓存并进行 Yang 更新。出处：历史 `sources/engine.py` 的发送、Replay、缓存和估计更新代码。

**DERIVED。** 因此攻击在 \(r\) 时刻不能改变 \(\sigma_i(r)\)，最早在 \(r+1\) 改变被污染接收节点1的发送判决。Task 0.5 的32个Seed均满足攻击前及 \(r\) 当拍估计、发送事件一致；首次节点1分叉均晚于 \(r\)。

## 攻击

**FACT。** 理论只考虑一次真实发送机会上的历史包替换：目标边为 \(0\to1\)，\(s<r\) 且 \(\sigma_0(s)=1\)，攻击包为此前实际发送的 \(\hat x_0(s)\)。攻击不改物理状态、量测、发送判决或发送参考。历史数据本身在窗口200–249内多次 Replay，每个Seed 9–33次；因此 Task 0.5 只把首次注入用于单步理论核验，不能把全窗数字称为单次攻击确认。

## 增益边界

**FACT。** `model.py` 用全链路即时通信联合协方差递推生成名义 \(K_i(k)\)，再复用于闭环SoD；它不是根据当前实际缓存重新计算的最优增益。本文只把 \(K_i(k)\) 当作冻结、已知、时间变化的矩阵序列，不移植 Yang 2014 的全部原文定理。出处：历史 `sources/model.py`、G7报告§2.1。

**FACT / 公式还原。** 设入边拉普拉斯为 \(\mathcal L\)，\(\mathcal B=(I_N-\varepsilon\mathcal L)\otimes A\)，历史名义联合协方差为 \(\mathcal P_k\)。源码 `model.py:41–74` 实际计算

\[
\mathcal P_0=\mathbf1\mathbf1^T\otimes P_0,\qquad
K_i(k)=(\mathcal B\mathcal P_k)_{ii}H_i^T
(H_i\mathcal P_{k,ii}H_i^T+R_i)^{-1},
\]
\[
\mathcal A_k=\mathcal B-\operatorname{diag}_i(K_i(k)H_i),\qquad
\mathcal P_{k+1}=\mathcal A_k\mathcal P_k\mathcal A_k^T
+\mathbf1\mathbf1^T\otimes Q
+\operatorname{diag}_i(K_i(k)R_iK_i(k)^T).
\]

每步还做对称化和半正定检查。这是**生成名义增益的全通信模型**，不是对当前SoD真实误差协方差的声明。本轮只读取公式，没有调用 `nominal_gains` 或生成新的增益轨迹。

## 历史来源定位与审阅范围

以下路径的基目录是只读主工作区 `C:/Users/zhongxin/shixidoc/mypaper/`。隔离分支中的同名历史目录没有全部 `sources/` 文件；不得以隔离分支当前 `simulation/engine.py` 冒充历史版本。

| 历史文件/行号 | 对应事实 |
|---|---|
| `simulation/runs/2026-11-10_five_node_v2/sources/engine.py:37–40` | 发送参考、发送/接收时钟及raw缓存初值 |
| 同文件`:52–55` | 用 \(y(k)\) 和pre-update估计形成本地候选 |
| 同文件`:59–73` | 严格平方阈值、timeout、初始强发、参考更新、节点事件复制到出边 |
| 同文件`:83–90` | 仅真实发送时，从该sender第8个前序发送机会选旧raw估计；这是历史多次攻击策略 |
| 同文件`:108–125` | Yang权重1、无裁剪、接收时钟刷新、\(A^{age}\)对齐、一致性融合 |
| `sources/model.py:24–38,41–74` | 参数装配与上述名义增益递推 |
| `sources/model.py:86–100` | 历史物理状态/量测生成顺序；本轮未调用 |
| `sources/run_study.py:131–153` | 两臂共用testseeds/x/y，closed_loop传 `schedule=None`，保存历史结果 |
| `config.json` | 本报告模型参数；原件摘要见下表 |

**FACT。** 当前核验的历史原件摘要与原 `environment.json` 的源码摘要相同；参数逐字段一致。下列为原件字节哈希，不混同Git换行转换后的配置副本。

| 原件 | SHA256 |
|---|---|
| config.json | `c71c687f13a6182f05d878bb0f0d171a36f0ca26afa09f2694b907674f3ac3ec` |
| sources/engine.py | `766b58625775378405db110b4157d41b2700f8622f461383000d31fabd2cd508` |
| sources/model.py | `d471643f273f119a1c934d1a79e83efcde3143244b6a491f65c740cb8a888d5d` |
| sources/run_study.py | `e394675504effc2fa59e50cd4649b8528bcc05721334a6fc532be4ac29d6c811` |

**FACT。** 为便于GitHub复核，本轮将上述三个历史源码以及config/environment原件按原始字节复制到本目录的[evidence/historical_five_node_v2](evidence/historical_five_node_v2)。脚本只读副本，核对原environment中的摘要及参数；不导入、不运行副本。副本不是可执行实验包，也没有增加轨迹。

克隆本分支后，Task0.5保存数据与本目录证据副本足以执行公式复核，不依赖旁边的主工作区。缺少或损坏证据时脚本报错，不自动重建。

## 任务边界

**OPEN。** 单次Replay的未来正式攻击时刻、来源选择和没有合法发送机会时的处理尚未冻结；本报告只给条件理论和历史首次注入核验，不替负责人选择实验协议。
