# 19 E2正式启动前完整性审计（E2-P0）

日期：2026-11-16。审计基线：09637308c03c51dfa5891ed35d17cfa5ab0c1a7e；隔离分支：g1r-e2-status-contract-20261115。

**结论：两个P0已修复，可提交负责人审查新E2授权；本轮未授权、未执行E2/E3。旧授权绑定禁止继续使用。** 本报告更新18号计划的启动依据，不覆盖旧报告、原始实验或冻结协议。

## 1. 证据与范围

- [R06测试汇总](results/g1r_e2_prelaunch_integrity_20261116_r06/tests.json)及[完整测试日志](results/g1r_e2_prelaunch_integrity_20261116_r06/tests.log)：71项通过（39项P0、32项原运行器回归），0失败、0错误。
- [实时环境比较](results/g1r_e2_prelaunch_integrity_20261116_r06/live_environment.json)。
- [30组缓存proposal逐项等价比较](results/g1r_e2_prelaunch_integrity_20261116_r06/proposal_equivalence.json)。
- [最终五项绑定与来源资产](sources/e2_prelaunch_integrity_20261116/final_assets.json)、[CLI完整输出](sources/e2_prelaunch_integrity_20261116/authorization_bindings.stdout.txt)，均为authorized=false，不是有效授权。
- [R06文件清单](results/g1r_e2_prelaunch_integrity_20261116_r06/manifest.json)。R06后唯一包装变更是明确results/.gitattributes自身使用LF行尾，最终代码绑定已重算，R06原绑定不覆盖。

保留所有过程结果：R01因测试路径过长及一项夹具批次计划缺失失败；R02/R03相应测试通过；R04新增恢复完成测试存在上下文语法错误；R05该夹具未满足原每攻击Seed24场景的行数检查；R06修正夹具并保留完整24场景，全部通过。上述为工程/测试失败，不是算法负结果；未用正式数据调参。

## 2. 唯一环境基准与实时守卫

环境基准来自Task 5原始calibration_manifest.json，与C0 R12 source_hashes.json逐字段核对。来源原文件SHA为：

| 来源 | SHA256 |
|---|---|
| Task 5校准manifest | 7ccd2a04d94e464a4f4b2b0ef67c134bbd3c613d73f08b95e1b0aa91663ee813 |
| R12 source_hashes.json | e715d11c3ab48e03e5fa81ddcc758d3f216753311c827369634f8b299f7a88cf |

原校准器通过redirect_stdout捕获numpy.show_config()完整文本，不过滤路径。新environment_guard采用相同方式，对归档和当前文本仅统一CRLF/CR为LF；不删改BLAS/LAPACK、编译器、ABI、架构或构建路径。没有指定新的参考环境。

Task 5、R12与本轮实时核验一致：Python 3.14.9、NumPy 2.5.4、SciPy 1.18.1；完整BLAS规范文本SHA256：

39fda87a49467f782309e1d07b91b7399217f915b323071f52807b1f59384e87

版本、BLAS摘要及采集/规范化方法组成environment_fingerprint，并纳入experiment_config_sha256。配置加载、授权校验、正式入口、批次前和正式数据生成边界均实时核验。授权摘要缓存已移除；原静态布尔值不再充当当前环境证据。来源SHA改变、两份参考不一致或当前环境不一致时拒绝；首次正式入口拒绝发生在创建Run目录和生成数据之前。

保证范围限于原证据能够确认的版本与完整numpy.show_config配置，不宣称认证未记录的机器负载或操作系统状态。

## 3. 新五项授权绑定

五字段结构不变；只有代码和实验配置摘要更新。其余三项保持原值。

| 字段 | 新SHA256 |
|---|---|
| final_code_sha256 | d9969aef9d6a8f271a258828ab030a476f304e3b4945f0f338e50b4b93c1e70a |
| protocol_sha256 | 7c7a2589c1f7d136886ea5a1d4c1664552d7d463cbd143f5fb0e8c455b3fbeab |
| calibration_thresholds_sha256 | 3c1255122f15c1efb9eaee284e00135247da2b16961c7b50c0ecbb3ecd244e00 |
| seed_list_sha256 | 8dd8d513d0bcff0ee80b5aa3dd797a2f49df2e5655aba40d2024645e37ddd946 |
| experiment_config_sha256 | ba4a22ae5b1fd52cf27b3374aa59200c9550f380a2c6dc0ef679861ebe41d66f |

原代码b8a0b0e…、原配置34f9404…构成的旧绑定被内存授权负测试拒绝；实时环境变化也使先前的内存授权回执失效。测试没有写入有效授权文件：C0中原有的有效文件测试已改用内存文件对象。代码包SHA与Git提交SHA不同；最终交付Git SHA见提交记录和最终回复。

## 4. 算法拒绝与执行异常

| 情况 | 处理 | 正式统计资格 |
|---|---|---|
| 冻结算法实际返回INPUT_INVALID、MODEL_INVALID、EMPTY_UNION、ZERO_OR_UNRESOLVED、SOLVER_REJECT、ZERO_PROPOSAL，或门限GATE_REJECT | 原Proposal、派生状态、证书、原门限结果全部保留；实际零动作 | 保留样本分母，不删除 |
| 模型/数据构造、Yang模拟、Replay规则、非有限创新、未预期proposal程序异常 | 保存原异常类型及完整堆栈、阶段/Seed/事件/年龄/方法；保留完成片段；ABORTED_INCONCLUSIVE | 不标记当前Seed成功，不完成当前批次，不发布gate_counts |
| 在线写入、离线评价、结果文件或checkpoint损坏 | 同样中止并保留证据 | 不能算成算法性能失败 |
| KeyboardInterrupt/SystemExit及进程中断恢复 | 可捕获中断记为INTERRUPTED_RESUMABLE，原授权/原配置及checkpoint哈希核验后恢复同一Run | 仅完整完成并审计通过后可汇总 |

BatchRunner已删除except Exception→failed_proposal_record转换，程序异常只在Run事务边界处理。冻结B.1便捷入口propose_adapted内部会吞掉任意Exception：本轮保持该文件不变，运行器直接调用同一v2_estimators.propose，再将原始Proposal交给同一e2_status_adapter.adapt及原apply_gate。实际返回的合法拒绝不变；未返回Proposal的程序异常不再伪装成MODEL_INVALID。算法内部本来明确捕获并编码为合法拒绝的结果，仍按冻结实现处理，不声称能区分已被算法编码成同一状态的内部原因。

partial_online保留同一Seed内已完成的方法结果；离线评价在在线结果落盘之后执行。离线程序异常不再一律变成覆盖false；明确的集合构造拒绝或非有限集合仍可记为未确认覆盖，中心失败与覆盖独立。每个Replay无论是否覆盖都必须有有限二维true impact。

## 5. 完整性、中止与恢复

validate_batch_rows对正常/Replay均要求simulation_status恰为PASS，无条件核验来源=r-age、源包与当前包合法发送、actual age、正确缓存替换时刻=r+8。proposal/action必须二维有限，范数、score和threshold必须有限，阈值与冻结校准一致。FAIL不能进入完成批次。共享Yang Run无原生状态字符串，适配层先校验数组形状、数值、发送日程及Replay记录再产生PASS。

执行故障写入execution_failures/<id>.json并更新run_status.json。正式启动及独立CSV复算拒绝带ABORTED_INCONCLUSIVE或失败标记的Run，等待负责人处理，不自动跳过/重试/换Seed。若汇总写入后封装失败，把未发布gate_counts隔离为unreleased证据，不能作Go/No-Go。原损坏文件不覆盖。

中断测试确认已完成分片哈希不变、恢复时不重跑完成Seed，并能继续原合成计划直至事务完成。该测试使用10+10个非正式ID、原24场景布局及缓存proposal，统计末端是明确的合成哨兵；冻结统计公式另由200+200个虚构ID的20批CSV完整复算测试验证，不混淆证据范围。

若Run磁盘不可写，尝试临时目录应急标记并向stderr输出完整堆栈。若所有介质均不可写，只能保证进程返回中止且不发布有效结论，不能声称日志已落盘；必须保留终端/调度器输出并交负责人检查。操作系统强制终止也不能保证生成Python堆栈，恢复依据原授权及持久化checkpoint/分片哈希。

## 6. 测试及冻结不变证明

71项回归覆盖：四种环境漂移分别拒绝、原环境通过、参考冲突/来源损坏拒绝、旧绑定失效；正常/Replay模拟及数据/模型异常；来源/年龄/缓存更换错误；非PASS及非有限输入；原样算法拒绝；在线写、离线评价、checkpoint写/损坏、已完成结果损坏；ABORTED禁止重启/汇总；中断恢复完成；末尾封装失败隔离汇总；所有日志介质失败时stderr路径。

[保护文件哈希](results/g1r_e2_prelaunch_integrity_20261116_r06/protected_before.json)及Git差异确认：Hard/Soft/Set源码、B.1适配器、校准器、阈值、protocol_v2.json、simulation/engine.py和model.py均未改。三门限仍为7.130518504393956、0.20737147161542802、0；U=0.051261；1%正常风险、5%概率约束及八个事件未改。

10条已存Debug创新×3方法共30组：score逐项相等，proposal/action最大绝对差均为0，raw/派生/gate状态及证书逐项相等，无放宽容差。测试期数据生成拦截器只允许固定fixture seed 0，任何非零Seed生成均报错；正式Seed生成调用为0。正常141420000—141420199和攻击141430000—141430199未被使用生成数据。没有重新校准，没有运行正式E2，没有运行E3；G2/G5不修改。

## 7. 命令和启动风险

以下仅为接口说明，未执行正式运行命令：

~~~powershell
$py = 'C:\Users\zhongxin\shixidoc\mypaper\.venv\Scripts\python.exe'
& $py -m reviews.g1r_risk_constrained_recovery.code.g1r_e2_runner.cli --show-authorization-bindings
# 仅在负责人签发/授权生成与新绑定完全一致的文件之后：
& $py -m reviews.g1r_risk_constrained_recovery.code.g1r_e2_runner.cli --formal-e2 --authorization '<负责人签发的授权JSON绝对路径>' --out 'reviews/g1r_risk_constrained_recovery/results/g1r_e2_run_<获批新RunID>'
~~~

- 原校准/R12基准与实时环境：通过；旧代码/配置绑定失效。
- 合法算法拒绝、运行故障归因、完整性、中断恢复：通过，证据范围见上。
- 冻结算法、阈值、八事件及正式Seed：保持；没有正式数据性能结论。
- 存储故障与强制终止：保留上述物理边界，不承诺无法实现的全部日志持久化。
- Set覆盖/动作率和正常误动作率：仍待获批的E2，P0通过不是E2通过。
- 正式E2授权：未签发。E3：未授权。

**建议：可以交研究负责人审核并签发新五项绑定的E2授权；本次交付后停止，不自行创建有效授权或启动正式实验。**

