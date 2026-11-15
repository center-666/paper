# G1-R Task C0：E2运行器设计与验收

日期：2026-11-15。工作分支：`g1r-e2-status-contract-20261115`。Task 5、v2协议、A/B审计及B.1状态合同版本均保持为任务书指定基线。本报告只验收E2执行系统；没有运行正式E2/E3，也没有生成预留Seed轨迹。

## 结论

**C0工程实现通过，建议提交负责人审核正式E2授权。授权前仍禁止正式运行。** 运行器使用原始 `simulation.model` 数据生成接口和 `simulation.engine.simulate(..., method="yang")`；未重写Yang滤波器或修改共享仿真文件。默认CLI路径为dry-run，正式模式要求外部授权文件并逐项核对代码、协议、门限、Seed和实验配置绑定。授权缺失或失效时，在创建Run目录和生成数据之前退出。

最终dry-run包为[g1r_e2_runner_dryrun_20261115_r12](results/g1r_e2_runner_dryrun_20261115_r12/)，运行器代码快照提交为`eed41930f74eb08ddf35e50b2e8c2a00d9a815f0`。R01—R12均保留；R03保留了源哈希阶段发生异常的部分失败输出，后续Run没有覆盖它。R09—R11是较早代码快照上的dry-run，R12绑定最终代码提交。

## 结构与信息权限

运行器代码位于[code/g1r_e2_runner](code/g1r_e2_runner/)：`config_loader`从协议、B.1包、Task 5校准manifest和冻结矩阵校验配置；`scenario_builder`只调用既有模型构造、数据生成与Yang simulator；`online_proposal`把12维创新、只读公共模型、门限和方法交给既有状态适配器；`offline_evaluator`在在线Proposal记录落盘后才读取真实事件、Replay来源/年龄及健康配对影响；`batch_runner`管理20个批次；`checkpoint_manager`验证逐Seed分片哈希并拒绝覆盖；`result_writer`原子写入结果；`integrity_checker`检查行数、配对、状态与幅度；`statistics_reporter`执行冻结统计门槛和分层统计；`authorization_guard`实施正式实验锁。

在线接口为不可变 `OnlineInput(z, frozen_public_model, threshold, method)`，不包含Seed、事件、年龄、Replay来源、真实污染、真实状态或健康反事实。公共矩阵及事件字典递归转为只读映射和只读数组。在线结果另存为带记录哈希的Proposal JSONL，离线评价器不能修改它。离线真实覆盖由事件兼容椭球并集计算，与Chebyshev中心求解状态分开，因此中心求解失败不会自动抹掉几何覆盖结果。

R12的`fixture_timing.json`以固定fixture seed 0验证了冻结主场景：edge 0即`0→1`，在200时发送的载荷来自136时刻的真实已发送包，年龄64；208时后续合法新发送替换缓存；污染从状态201开始，节点1首次受污染状态也是201；接收端使用211—216创新，并以217为目标。还对8个冻结事件乘3个年龄逐个核实真实来源发送、Replay时刻、实际年龄、缓存替换时刻及单次载荷替换。24个事件—年龄组合共用同一fixture轨迹，仅用于确定性时序检查。

## 批处理、结果和统计

未来正式运行按冻结Seed顺序执行：正常、攻击各200个Seed，每组10批、每批20个Seed。每个攻击Seed保留8事件×3年龄×3方法共72行；统计单位仍是Seed，事件和年龄被明确标为同Seed相关分层。每个Seed先写不可变在线proposal，再另存离线评价CSV；checkpoint只有在在线和离线分片均写入并哈希后才标记完成。中断后可验证并续用完成分片；孤立分片仅可由确定性重算得到相同字节时复用；不同内容、重复行、重复Seed、缺失Seed、缺失事件年龄方法组合都会报错。失败与拒绝保留在原行和统计分母中，不替换Seed。

全部20个批次完成后才允许汇总。统计器要求正常和攻击主场景分别恰好覆盖冻结的200个Seed，非零动作使用门限后的实际动作范数；覆盖、攻击非零动作及正常非零动作使用原E2分母和单侧95% Clopper-Pearson界。还输出每方法的求解拒绝/门限拒绝，以及逐事件、逐年龄的覆盖、非零率、拒绝率和独立Seed数量。最终汇总会再从20个批次CSV独立复算，并与内存统计逐项哈希比较。统计输出仅是E2检测/动作率，不能替代E3估计恢复结论。

正式运行需要外部负责人授权JSON，字段为`scope="E2"`、`authorized=true`、非空`owner`、`authorization_id`及5项`bindings`。运行器不会创建或签发此文件；对本次已完成的源码快照，负责人提供的授权文件SHA256还会记录在Run配置中，恢复运行要求owner、授权文件SHA和全部bindings与Run初始配置一致。执行

```powershell
python -m reviews.g1r_risk_constrained_recovery.code.g1r_e2_runner.cli --show-authorization-bindings
```

只读打印当前绑定值；R12绑定记录为：代码`b8a0b0e7905fd6d99e491d689ea9add53454130d04eacb02185a749a61d2ccec`，协议`7c7a2589c1f7d136886ea5a1d4c1664552d7d463cbd143f5fb0e8c455b3fbeab`，阈值`3c1255122f15c1efb9eaee284e00135247da2b16961c7b50c0ecbb3ecd244e00`，Seed清单`8dd8d513d0bcff0ee80b5aa3dd797a2f49df2e5655aba40d2024645e37ddd946`，实验配置`34f9404f6f53fe9c40d630bacc194e15d268de4cbe921cf1430c297a783f33c2`。这些哈希只说明授权文件该绑定什么，不构成授权。仓库内的`authorization_template.json`明确`authorized=false`且为空绑定，不能用于开跑。

正式命令形态为：

```powershell
python -m reviews.g1r_risk_constrained_recovery.code.g1r_e2_runner.cli --formal-e2 --authorization <owner-issued-e2.json> --out reviews/g1r_risk_constrained_recovery/results/g1r_e2_run_<new-run-id>
```

这只是接口说明，本轮没有创建该授权文件或调用该命令。实际生成的R12 `dry_run_manifest.json`明确记录`formal_e2_executed=false`、`formal_e3_executed=false`、`official_seed_generation=false`。单独执行`--formal-e2`但不提供授权的拒绝测试以退出码2停止，且目标Run目录不存在。

## 验收结果

| 项目 | 证据 | 结果 |
|---|---|---|
| 冻结Yang及时序 | R12固定主场景及24格fixture时序记录；模型配置逐项比对Task 5配置 | 通过；复用共享engine/model |
| Hard/Soft/Set与适配器 | 32项runner确定性测试、5项B.1适配器测试、30组既有proposal等价证据 | 通过；门限和`U=0.051261`不变 |
| 在线离线隔离 | `OnlineInput`字段白名单、不可变Proposal记录、离线真值单独对象和泄漏测试 | 通过 |
| 求解失败与覆盖 | solver reject fixture、并集覆盖独立评价测试 | 通过；失败记录仍占分母 |
| 批处理/断点/去重 | 固定20×20计划、重复/缺失Seed与行测试、20个合成checkpoint分片恢复实测 | 通过；未使用研究Seed |
| 统计独立复核 | CP beta分位与二项尾方程交叉核对、冻结计数边界；另以虚构Seed的200+200行、20个CSV批次端到端重算 | 通过；无仿真/正式Seed；coverage=190、attack action=100、normal action=12和reject分母均按预期复算 |
| 结果完整性 | R12 artifact SHA、源文件哈希、`.gitattributes`禁行尾转换 | 通过；dry-run资产可逐字节校验 |
| 正式执行锁 | 无授权、错误授权、伪造回执和配置篡改测试；CLI拒绝运行测试 | 通过；授权缺失时没有生成轨迹或Run目录 |
| 正式Seed保护 | R01含400个Seed的既有碰撞扫描；dry-run只读取已存在Task 5 Debug缓存，fixture仅用seed 0 | 通过；本任务没有读取这些Seed生成数据 |

冻结源码和运行环境：R12记录Python 3.14.9、NumPy 2.5.4、SciPy 1.18.1及完整`numpy.show_config()` BLAS文本；R12的Git HEAD为`eed41930f74eb08ddf35e50b2e8c2a00d9a815f0`。共享`simulation/engine.py` SHA256为`05fb3f19d457e103d7c1665ccd1087ea4b27076d6a39b57ac7e0d16cfdb35c97`，`simulation/model.py`为`5b674a4cc274fca42d52d00f15490d5e3952231df98146a90cb28a62b4a9aeca`；运行器逐文件复核均相同。B.1 R01包artifact SHA及来源文件SHA也均通过。

测试命令和结果：runner 32项、B.1 adapter 5项、确定性/统计12项、底层估计器几何5项通过；gap-8数据机制fixture的固定seed重现与Replay时序核验通过。runner第32项用虚构Seed的200+200行CSV执行完整的20批独立统计复算，并验证求解拒绝仍保留在冻结分母。全部runner Python文件通过`py_compile`。R12复用10条已缓存Debug特征（5正常、5 Replay），输出30个Hard/Soft/Set proposal；另用fixture seed 0输出75条proposal（1正常场景加24个攻击事件年龄场景，各3方法）。该fixture使用既定生成器和固定seed 0，只作dry-run；没有生成正式研究Seed轨迹。

## E2启动检查表

| 启动前条件 | 当前检查 |
|---|---|
| runner源码、协议、门限、Seed清单和实验配置绑定 | 已实现；可用`--show-authorization-bindings`只读生成当前五项摘要 |
| 正式授权由负责人单独提供，`authorized=true`且绑定完全匹配 | 尚未提供；当前模板无效，正式模式将拒绝 |
| 400个Seed列表与冻结协议一致且历史扫描无冲突 | 已由只读审计核验；扫描范围之外的外盘/备份不在声明范围 |
| Python/NumPy/SciPy、BLAS、Yang共享源码、矩阵及模型配置哈希 | R12 `source_hashes.json`记录并通过逐文件复核 |
| proposal/日志/失败归档路径及每Seed去重 | 已通过固定接口和断点/重复测试；R12 dry-run中没有正式Seed行 |
| 20批次计划与独立统计复算 | 计划为20批；使用虚构Seed端到端验证批CSV复算。正式汇总仍要求全部正式批次及Seed |
| E3授权 | 不包含在E2授权中；仍需单独批准 |

当前建议状态：**技术准备通过，E2正式执行等待负责人签发并复核授权文件；本次任务未授权、未启动。**

## 性能与存储估算

R12在缓存输入上测得单条特征的三方法proposal约0.0074秒；20条特征、60次proposal约0.428秒。20个合成checkpoint分片的读取、SHA核验和恢复约0.032秒，20分片均恢复。`tracemalloc`峰值约323KB，指Python跟踪分配，不是进程RSS。proposal记录平均约1116字节、最大1368字节；按dry-run fixture CSV测得行均约443字节。按未来15000次proposal和三份离线行记录粗估，主结果约36.7MB，尚未计失败案例归档和文件系统开销。

总运行粗估约116秒（约0.032小时），规划区间约1—4分钟。这个估算把Debug运行中不能归到proposal的时间按生成数据及Yang更新次数归一化；它不是正式运行性能保证，实际耗时受机器、磁盘及SLSQP数值路径影响。运行器不降低求解精度或迭代限额。

## 最终启动判断

运行器结构、共享Yang调用、隔离接口、冻结场景/Seed计划、失败保留、checkpoint、统计及授权锁均达到C0技术验收要求。**建议负责人审核并另行签发正式E2授权；本报告不授权E2。** 当前仍保留的研究风险是Set集合覆盖和正常/攻击非零动作率未知，必须通过获批的E2正式实验判断。E3仍需独立授权。

提交：`a68706ff658e1085d46bfad81585f9e210b761ff`、`435d1bb8b207822f6eaa42bfd8c3ddebee707590`、`2689660e56b9253bdce2c3bdf43c6763c8fb022d`、`6cc84e325231d623f5fd964e82c011263f8a290e`、`eed41930f74eb08ddf35e50b2e8c2a00d9a815f0`；R12包生成于`eed4193`代码提交之后。最终报告及R09—R12证据为后续独立提交；主工作区的G5改动未触碰。
