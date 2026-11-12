# G1任务三：最小实验筛选计划、功效与未执行项

日期：2026-11-12。G1停止条件审计发现候选主要score已在旧实验使用，且样本量不足以可靠分辨1%效应。本文件是未执行的筛选草案与停止记录，不是已注册实验。本轮没有创建Run ID、分配或使用新种子，也没有生成新轨迹。

## 1. 源代码时序审计

读文件：simulation/engine.py、model.py、sequential_cache.py、run_sequential_validation.py。

1. 线上触发：t进入时用估计hat(t)与最近实际发送估计比较Send-on-Delta阈值；或达到timeout；t=0强制发。
2. 本地量测y(t)每个tick可用。触发决定形成后，攻击只替换真实发送包；没有send不产生链路攻击机会。
3. receiver融合并缓存实际收到的payload；缓存age=t-last_receive，随后用A^age外推。
4. online episode monitor每tick读receiver真实本地measurement、aligned cache、age和fresh；不读truth/future。fresh在monitor update前重置cache。
5. 残差是y_i(t)-H_i A^age payload。下一fresh tick先flush旧episode，再形成新包age0残差。
6. G1历史序贯结果使用固定外生gap8/irregular发送schedule以便公平配对，没有使用线上Send-on-Delta反馈。这限制了旧结果适用范围。
7. 末尾未关闭episode标right-censored，不进入训练、校准、tune与false-isolation完整episode分母；必须另报告删失率。
8. gain按全边全通信q=1估算，再复用于触发cache system；原Yang原始增益和稳定结论未自动成立。

## 2. 已发生的门槛判定

停止条件1 **已满足：本候选episode prefix统计的主要机制已在旧测试中实现。** 旧代码用经验full joint covariance归一化每个完整cache prefix的算术均值，并对一整个episode内所有prefix最大值定门限。它不是任意动态设计矩阵GLS，但“共同误差 + episode max calibration + cache quarantine”的表述已不能写作尚未实现。

原实验（新数值仿真不再执行）：

| 来源 | 既有单位/设置 | 结果 |
|---|---|---|
| 2026-11-11 sequential strong | 异质全秩模型，每主比较192配对种子，固定gap8/irregular；12项主比较 | 5单项过，完整主场景cell仅1/4过，half-step未过 |
| 2026-11-11 carry CUSUM | 192新种子，跨新包保留CUSUM | step 4项3项过；half-step收益约−.22%至+.33% |
| 2026-11-11 partial-observability | 接收主边秩一压力模型，每主比较192配对种子 | step 4项均未过 |
| episode covariance counts | steady主边 | gap8 age 1–8各4032训练/标定完整episodes；irregular age1–8训练/标定数8160/7392/6624/4224/2592/2592/864/864，age9–10 fallback |
| test episode censoring | 单种子T=400 steady主边 | gap8 8256 episode中192删失，2.326%；irregular 16512中192删失，1.163%，删失长度不均匀 |

## 3. 样本量/置信区间精度

使用旧192种子种子级配对差SD估计，对比检测器mean/原window-CUSUM。把1% relative MSE定义成最小实际可分辨差。正态近似、80% power、双侧检验：

| 旧场景 | 单一comparison所需独立种子范围（Bonferroni 12比较） |
|---|---:|
| step：五个对比中的典型区间 | 976–1266 |
| half-step | 339–587 |

若保留12项家族推断、控制family alpha=0.05，step需约1708–2215独立种子；这只是planning近似，不是样本量保证，exact GLS未知也可能有不同方差。旧192种子在step comparison的配对95%区间半宽约基线MSE的1.6%–1.8%，不足以窄到分辨1%改善。具体逐比较参数和假设见g1_sample_size.json。

若未来另批准GLS screen，训练、covariance calibration、template choice、FPR tune、normal audit、最终test必须用互不重叠seed。例如每阶段120、test240可用于粗机制筛查；但功效近似仍要求近1000个独立seed作单一step比较，familywise更高。该新统计的方差未知，具体N须在新注册前重新做blind pilot或保守规划。由于已满足停止条件1，本轮不为标准GLS变体分配seed。

episode长度不是独立样本；同种子/trajectory的多个episode和多方法高度相关。置信区间需按独立seed聚类bootstrap/配对推断。每phase及每edge的误隔离率单独报告；数据不足的phase不许用partial episode补齐后冒充完整episode概率。

## 4. 原本应有的冻结实验计划草案

本段不执行，仅说明若未来先有独立机制论证并另获批准时的对照范围。停止条件1已满足，不建议把本节视为本轮预注册。

### 方法

1. local estimator；
2. 无保护Yang-form；
3. Zhou随机保护；
4. 单步Zhou spatial residual/instant score；
5. 项目既有完整covariance prefix-mean score与episode最大值门限；
6. 相关白化window和跨包energy/signed CUSUM；
7. 精确trigger-conditioned联合GLS/公共缓存偏置GLRT（只有先成功推导条件分布才实施）。

状态：NOT EXECUTED / NOT REGISTERED。G1停止条件1已触发，本轮不创建试验目录、不分配新seed范围，避免把未批准的future test误写成已冻结或已运行实验。

关键防伪增量：第5项必须标记为已实现基准；第7项若只是已知joint covariance下的标准Wald/GLS，不能计创新。UIO (Liang 2023)若适配，要独立写observer增广模型、所需neighbor输出及rank/detectability条件，并同样信息权限运行；没能公平适配就标“未完成移植”，不得报谁胜。

### 场景

- normal/clean；
- 强step持续bias；
- half/low bias持续注入；
- 固定滞后实际历史包Replay；
- 连续历史片段Replay；
- matched-gap历史片段Replay，来源包间隔与当前发包间隔相同。

所有Replay包都需验证源时刻是该发送者在本受攻链路上实际发出的包，不读取未发送state。matched-gap不代表内容同分布。

### 设计、校准、指标

- 第一层固定完全相同的外生schedule、noise、x、attack opportunities、edge与攻击数量，比较检测/融合统计；
- 每方法用相同信息、本地measurement和episode definition。阈值只用normal tune set校准episode-level false isolation，normal audit测漂移；
- 第二层仅对冻结通过的少量方法运行各自Send-on-Delta闭环，报告actual sends、edge messages、payload bytes；不宣称同触发数值阈值就是同成本；
- 报完整episode FPR及右删失数量、conditional detection delay（按episode age和发包机会分别定义）、正常MSE、攻击窗口MSE、攻击后固定恢复窗MSE、packet count与bytes；
- 配对统计单位是seed。长度a的同一缓存内时间步/episodes不能作独立样本。

## 5. 本轮为何不执行

G1授权任务要求在样本功效评估后决定是否扩展实验。只读代码复核确认full-covariance prefix-mean + episode max + persistent cache isolation已在旧实验中实现；理论设计矩阵GLS是标准Wald推导，且真实Send-on-Delta选择分布条件Gaussian尚未建立。旧192独立种子不足以可靠分辨1% step MSE增益；所需新样本量约1000至2200，已超出“最小复核”且可能只验证一个统计等价改写。

根据停止条件1及当前创新性缺口，本轮没有冻结seed allocation、没有生成任何新的test/训练轨迹、没有修改既有运行。该决定避免用大仿真替代方法增量论证。
