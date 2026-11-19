# Paper 1 E1：冻结标量执行与证据验收

原始基准7b14caa54caac116970b3aa0fb1ee2d9224f9d61；在原研究审查分支提交新增代码后，运行前冻结源码SHA、原协议和环境，再生成输入并记录输入哈希，最后开始模拟。共享engine/model、原论文和旧实验均不改。

代码职责：

- run_e1.py：仅执行冻结的S1/U1、3δ、k=4、b=.1、每模型2048基础样本；健康/±共用输入。保存所有原始数组后判定硬断言；失败不删样本、不继续汇总。
- audit_e1.py：不导入运行器，读取保存的输入/状态，独立重算因果时序、精度、Bayes精度形式后验、量化事件历史和真实损伤/连续矩恒等式。
- analyze_e1.py：仅在前述硬检查通过时，从保存样本计算逐样本表、统计、1000次按基础样本配对bootstrap、图表；不新增物理随机轨迹。
- verify_analysis.py：另行从原始数组和保存的重采样索引复算关键均值/区间，核对导出CSV。

**最终裁决：EXPERIMENT PASS，限冻结E1实现和证据合同。** A的实际事件小差异未被本批样本分辨，相关负向证据保留。项目整体仍为CONDITIONAL GO。C与A-rounded-log只定义观察字段，无额外方法运行。所有统计结论限于预设精度主导区，TV=0由既有证明支持，不估计完整连续日志TV。

- [执行结果与限制](01_execution_report.md)
- [独立审稿前证据自查](02_referee_evidence_audit.md)
- [原始输入、状态数组和完整断言](results/e1_20261119_v1/)
- [运行前源码与协议冻结](results/e1_20261119_v1/code_and_input_contract.json)
- [独立数值核查](results/e1_20261119_v1/independent_audit.json)
- [逐样本表](results/e1_20261119_v1/analysis/sample_metrics.csv)与[全部统计及区间](results/e1_20261119_v1/analysis/summary.json)
- [原始数组结构与权限](results_schema.md)
- [交付哈希和修改边界](delivery_validation.json)
- [更新后的讨论稿](../../papers/paper1_trusted_record_integration_20261119/README.md)

新目录不会复用旧Run。若硬性检查失败，保留输入、轨迹、断言和失败索引，论文“待验证”状态不移除。

完整复算应选择另一个明确的新Run目录；现有run_e1.py、audit_e1.py、analyze_e1.py、verify_analysis.py均拒绝覆盖已有制品。本轮只执行e1_20261119_v1这一批，不为复现演示再跑第二批样本。
