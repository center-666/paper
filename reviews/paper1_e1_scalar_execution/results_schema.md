# E1原始制品与信息权限

本目录所有数值为合成研究数据，无第三方PDF。单位、参数与RNG合同见原冻结protocol_snapshot.json和code_and_input_contract.json。

## 原始输入

每模型一个 S1_inputs.npz / U1_inputs.npz：

- x、y、v、U：形状[2048,6]，时刻0..5；w形状[2048,5]；base_sample_id为0..2047。
- x是真值、y是未经载荷修改的测量，v/w/U是生成过程的保存输入，供独立复算使用。
- 策略API不读取x、w、v、U或未来y。它只接收已生成的发送位、发送时真实量测、自己的当前预测/协方差和公开参数。
- 随机生成采用协议规定的PCG64子流，健康/正/负和所有精度/协议复用同一基础物理与触发输入；模型之间独立。

## 每个配置的trace.npz

统一轴为[基础样本, 分支, 时刻]，分支0=healthy、1=plus、2=minus；float64连续状态、bool事件和int64码索引。

| 字段 | 含义及权限 |
|---|---|
| m_prior、m_post | 接收端精确内部预测/后验；在C-predictor可见，在B遥测中不公开 |
| P_prior、P_post、gain | 事件确定的协方差及更新增益；P标签属于相应审计记录 |
| feedback、feedback_index、qerror | 实际触发反馈中心、量化码索引、中心减预测误差；A中心精确，index字段置0且不作为A审计信息 |
| sent | 使用真实y、实际center和U生成的可信发送位，早于动作 |
| payload | 实际收到的连续值；静默为NaN；C-payload可见，B不公开 |
| action、eligible、gate_M、gate_margin | 实施动作和策略资格诊断；门控只在目标真实发送后计算；无包时M/margin为NaN |
| rounded_log_feedback、rounded_log_index | 由内部预测被动舍入得到的A-rounded-log视图（B时与实际码一致）；A触发不读取它 |
| mu_prior、mu_post | 基于真实已发送历史和已知动作的分析条件均值；仅评价层使用 |
| trigger_send_probability | 给定当前真实测量的随机事件概率；不是仅靠B记录可恢复的概率 |
| history_send_probability | 给定分析条件历史、积分掉当前量测/触发随机数后的事件概率；仅分析诊断 |

NaN只表示没有实际载荷/没有可见的目标包，不删除任何样本。所有完整轨迹先保存，再执行硬断言。

## 汇总与区间

sample_metrics.csv有24576行＝12配置×2048基础样本；所有行均保留。J_paired使用正负两分支平均后减同协议健康值。J_formula是对应理论恒等式的逐样本右侧。C矩差也是同一组B数组的字段后处理。

bootstrap_indices.npz含每模型[1000,2048]索引；同模型所有配置共用。样本间相关性通过配对索引保持，正负符号不另当独立样本。summary.json含均值和探索性百分位区间；区间既不同时覆盖所有表格，也不代替有限样本风险定理。

W_cond、certificate_conditional_diagnostic依赖分析条件均值/偏差，必须与审计者可见的W区别。A的W_gap样本为0，不能把退化bootstrap区间解释为总体差异严格为0。

## 完整性

input_hashes_before_simulation.json在任何状态方法执行前写入。cases.json记录12份轨迹SHA；运行器、独立核查、聚合复核和交付核查依次留档。原始bootstrap索引和状态数组均发布，可从指定代码与元数据复算，不要求访问用户Zotero。

本目录局部.gitattributes关闭自动换行转换，使新运行JSON/CSV/源码的SHA256与仓库字节一致。原历史协议的source_sha256指原工作区运行时字节；运行快照及交付核验另保留其语义一致性，避免将旧JSON在不同平台的CRLF/LF转换误判为参数变更。
