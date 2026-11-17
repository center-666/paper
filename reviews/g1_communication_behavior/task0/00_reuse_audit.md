# Task 0：G1 通信行为研究资产复用审计

日期：2026-11-17。性质：只读资产审计与执行准备，不是实验计划注册、性能验收或 Go/No-Go 决策。

标记：**FACT**＝本轮读取的代码、配置、既有结果直接支持；**DERIVED**＝在明确条件下由这些材料推导；**OPEN**＝证据或负责人决定尚缺。表格各行按“标记”列理解；没有把可能性写成已观察的效应。

## 1. 审计基准与保护边界

**FACT。** 本轮报告新增于隔离 worktree `C:/Users/zhongxin/shixidoc/mypaper_g1r_e2_status_contract`，分支 `g1r-e2-status-contract-20261115`，HEAD `788204a388155c9604348fc09d6ce510691c3fc4`，remote 为 `https://github.com/center-666/paper.git`。未查询远程最新 HEAD，不宣称本轮完成远端同步核验。开始时该 worktree 有未跟踪的 G8/G9 草稿，已保留。

**FACT。** 用户当前主目录 `C:/Users/zhongxin/shixidoc/mypaper` 在 `main`，HEAD `490e5b8f1212004407a0cdbfde224bf90a691da4`，存在 G5 未提交改动及其他临时文件。未切换、清理或修改该工作区。两个 worktree 的 engine、model、config、cache_monitor、sequential_cache 字节摘要相同；清单见 [02_parameter_manifest.json](02_parameter_manifest.json)。

**FACT。** 上一轮新增的 `mypaper/simulation/yang_full_communication_reference.py` 是未跟踪的独立参考文件，未接入共享核心，本轮不将其作为新的正式基线。用户粘贴 MATLAB 中的 `A=diag(1.11,1.13)`、随机 H、五条有向边等也未被替换进 G1 配置。当前核心仍是已有 Yang-form 改编，不能称 Yang 2014 全文严格复现（`simulation/model.py:1,42–47`）。

## 2. 必读材料的实际读取及定位

以下路径均相对于隔离仓库，另标 `main:` 的是主工作区只读历史文件。这里登记与本任务直接相关的代码及报告；不声称逐行读取了三个大目录中每个重复 JSON 分片或所有文献。

| 标记 | 资产 | 本轮读取内容及定位 |
|---|---|---|
| FACT | `simulation/engine.py` | 完整文件；`simulate`，尤其55–79、80–135、153–188；`basic_metrics`197–223 |
| FACT | `simulation/model.py` | 完整文件；`Model.build`24–39、`nominal_gains`42–75、`generate_data`87–102 |
| FACT | `simulation/config.json` | 完整配置；默认模型6–14、攻击30–33、运行场景35 |
| FACT | `simulation/cache_monitor.py` | 完整文件；`CacheMonitor.fit`77–178、`scores_batch`180–197、保存/加载232–260 |
| FACT | `simulation/sequential_cache.py` | 完整文件；`PhaseStatistics.fit`50–85、`SequentialController.update`135–176、`finish`178–181 |
| FACT | `reviews/fdi_replay_20261112/` | `g1_experiment_plan.md`全文、`g1_decision.md`全文、`identifiability_audit.md`全文、`project_evidence.md`全文；`g1_existing_code_audit.json`参数及统计审计；`sources/prior_result_index.json`与三份序贯/跨包/秩亏原结果报告全文 |
| FACT | `reviews/g1_retroactive_recovery/` | 07传播验收、08权限审计、18最终Replay结果全文；`code/p0_verified.py:difference/Log/features`46–109；`minimal_recovery_screen.py:build_model/common_schedule`59–82；`receiver_gls_writeback.py`1–149的候选、拟合、归责接口；`compare_deghat_outputs.py:event_sensitivity`90–117；`final_replay_run.py`1–130的冻结/日程/参数流程及 `frozen_plan.json` |
| FACT | `reviews/g1r_risk_constrained_recovery/` | 07联合Gaussian模型、21正式E2、22独立覆盖、26正式E3报告全文；03/10/11合同的模型和信息权限节、17运行器设计；`protocol_v2.json`；E2 `scenario_builder.py`全文和 `online_proposal.py`白名单；E3 `scenario_builder.py`全文 |
| FACT | G7-R0 | `reviews/g7_sod_conditioned_retrospective_detection/01_core_problem_audit.md`全文622行；重点§2、§4、§6.5、§7.3、§10 |
| FACT | 辅助执行代码 | `cache_screen.py`收集器和控制器1–86；`run_study.py`完整文件；`run_sequential_validation.py`完整文件；`reference_exploration_plan.json`、`sequential_validation_plan.json`、`cusum_carry_plan.json`、`partial_observability_probe_plan.json`；`trigger_consistency_probe.py`全文 |
| FACT | 主工作区历史原件 | `main:simulation/runs/2026-11-10_five_node_v2/`的配置、报告、VERSION_NOTES及engine/model源码快照；闭环clean/Replay NPZ只核对容器字段与形状；`main:simulation/validation_runs/2026-11-11_sequential_strong_v1/{gap8,irregular}/config.json`及carry的gap8配置 |

**FACT。** 上述 strong/carry 的部分配置和早期闭环NPZ在隔离worktree缺失，但在主工作区可读取，已在参数清单记录绝对路径及SHA256，没有复制、补造或重新生成。主工作区历史快照engine/model与当前核心哈希不同；本轮直接读取快照确认旧SoD判据、发送后参考更新、Replay次序一致，不以“文件同名”声称完整版本等价。

## 3. 十二项问题逐项回答

| # | 标记 | 审查回答 | 直接证据 |
|---|---|---|---|
| 1 | FACT | 非初始化：`||hat_x_j(t)-last_send_value_j||² > send_delta_squared` **或** `t-last_send_time_j >= max_interval`。默认阈值平方0.12、timeout10；t=0全发。严格大于不是大于等于。 | `engine.py:62–75`；`config.json:13–14` |
| 2 | FACT | 使用当前拍量测更新前的 `hat=estimates[:,t]`。虽然先计算innovation/base，但触发读取hat，不读取base或y(t)。 | `engine.py:55–68` |
| 3 | FACT | 当拍发送决定、t0强制和`sends`记录完成后，立即以发送端自身hat更新last_send_value/time；发生在链路载荷替换之前。静默不更新；参考值不是A外推后的旧估计。 | `engine.py:70–80` |
| 4 | FACT | Replay在发送决定及发送端参考更新之后，只对目标边fresh的样本替换incoming。不会回溯改本拍发送决定。 | `engine.py:73–81,92–105` |
| 5 | DERIVED | r拍收到替换包，同拍覆盖缓存并用于更新，首个可变接收估计为r+1。原Yang且首次单边差δ时 `d_i(r+1)=epsilon*A*δ`。若δ=0、映射退化等，可无非零污染，不能强行称每包都污染。 | `engine.py:155–174`；G1-R 07传播审计§预测器与参考严格分离；`model.py:42–75` |
| 6 | DERIVED | 闭环SoD下最早r+1拍可能改变被污染接收节点i自身的出链路发送事件；r拍i的发送已决定。是否实际变化取决于阈值裕量与timeout，未获得数值证据。外生schedule下发送事件不会因此变化。 | `engine.py:55–80,174` |
| 7 | FACT | 先形成节点级`transmit(S,N)`，再用`fresh=transmit[:,src]`映射到边。一个节点的所有出链路共用发送机会；目标边被替换不意味着同sender其他出边载荷也被替换。0→1的接收者1的出边为edge1=1→0、edge2=1→2。 | `engine.py:27,76–78,97`；`config.json:11` |
| 8 | FACT | 对非local方法，`schedule=None`启用SoD+timeout+t0强制。`method='local'`提前continue，没有网络发送。 | `engine.py:59–72` |
| 9 | FACT | 非None schedule直接复制`schedule[:,t]`，覆盖跨阈与timeout逻辑；t0仍强制全发。`config`里保留阈值不代表运行用过SoD。 | `engine.py:62–72`；E2构景器135–143 |
| 10 | FACT | 没有网络延迟队列、随机链路丢包或乱序。fresh等于发送端事件，当拍可靠接收。缓存age是距接收时刻，不是传输延迟。 | `engine.py:76,155–159`；G7§2.2 |
| 11 | DERIVED | 可复用Yang更新、缓存保持/外推恒等式、固定模式响应计算与首次影响时序。闭环模式分叉后不能继续复用单一公共O/G或Σ；须分别维护两臂的发送参考、时钟、接收缓存、年龄和模式，并处理触发选择。 | `p0_verified.py:46–71`；G1-R 07末段；联合Gaussian报告§1/§2；G7§7.3 |
| 12 | FACT / DERIVED | 现有评分器不把自身出链路发送事件作为显式评分输入。全网Run.sends可离线看到；在线节点能根据完整自身估计历史、阈值、timeout及初始规则重构自身发送。入边fresh不能直接当自身出边fresh；不能借全网数组读取其他节点私有事件。 | `engine.py:163,188`；`sequential_cache.py:135–176`；`cache_screen.py:48–68`；G1-R `receiver_gls_writeback.py:88–149` |

## 4. 状态更新、闭环分叉与传播资产适用范围

**FACT。** 原Yang路径（`method='yang'`，无改变权重的monitor）为

\[
\hat x_i(t+1)=A\hat x_i(t)+K_i(t)[y_i(t)-H_i\hat x_i(t)]
+\epsilon A\sum_{e:j\to i}[c_e(t)-\hat x_i(t)],\quad
c_e(t)=A^{t-r_e}q_e.
\]

依据：`engine.py:55–58,153–174`。缓存保留raw载荷，不清空过期缓存；发送参考保持原数值，而接收缓存参与融合时按年龄外推，二者不能混用。

**DERIVED。** 使用同初态和噪声的两条原Yang轨迹，令 `d=hat_x^a-hat_x^0`，各臂在t完成接收后的对齐缓存为`c_e^a,c_e^0`，逐拍恒等式仍为

\[
d_i(t+1)=[A-K_i(t)H_i-\epsilon\deg_i A]d_i(t)
+\epsilon A\sum_{e\to i}(c_e^a(t)-c_e^0(t)).
\]

但闭环通信不同后，缓存差不能只用公共fresh乘sender差刷新。设两臂收包前已外推到t的缓存为`c^{a,-},c^{0,-}`，对应sender发送标志为`S^a,S^0`，在没有新的载荷篡改的时刻：

\[
c^{a,+}-c^{0,+}=S^a d_j+(1-S^a)(c^{a,-}-c^{0,-})
+(S^a-S^0)(\hat x_j^0-c^{0,-}).
\]

这是接收重置式逐项相减，不是新传播实现或创新定理。最后一项在公共日程时消失，模式分叉时依赖健康轨迹，说明原“仅公共矩阵+δ”的单响应预测不再封闭。r拍需另加目标边Replay载荷差；不得继续把每个新发送都当成新的攻击。

**DERIVED。** 在第一个发送模式差异出现之前，原公共日程线性差分递推仍适用；模式分叉当拍起须处理上述额外项。即使给定完整闭环模式可建立线性分支，该模式由噪声/攻击选择，其条件统计也不是原外生日程的无条件Gaussian。G7§4和§7.3已明确这一边界。

## 5. 既有结果能够与不能够支持什么

**FACT（参数分层）。** 以下只转录历史版本，不选定下一阶段模型；Q均为0.02I、P0为I、epsilon为0.08、五节点双向环、阈值平方0.12、timeout10、零初始估计。实际H/R取值优先级以`model.py:27–28`为准。

| 历史层次 | A | H | R | 实际通信/攻击 |
|---|---|---|---|---|
| 默认/早期five_node_v2 | 1.01I | diag(s_i,s_i)，s=[1,.8,1.2,.9,1.1] | 各节点0.05I | 早期同时有健康参考日程和闭环SoD；200–249多次Replay，第8个前序真实发送包 |
| G1 sequential strong/carry | [[1,.1],[0,1.01]] | diag(1,.15)、diag(.15,1)、diag(1,.15)、diag(.15,1)、.7I | 各节点0.05I | 外生gap8/irregular；strong Replay为t−80，carry实际只跑FDI场景 |
| G1秩亏压力 | 同上三角A | 节点0/2/4为diag(1,0)，1/3为diag(0,1) | 各节点0.05I | 外生日程；FDI压力对照，不是闭环单包Replay |
| G1-R传播及E2/E3模型 | 同上三角A | 与strong异质H相同 | 各节点0.05I | T=280，固定gap8；P0主事件r200/s136/q208；E2/E3八事件、年龄32/64/96，源时刻r−age |

参数来源逐文件路径、SHA256、有效矩阵展开及协议引用见02清单的`model_profiles`和`E2_E3_fixed_protocol_reference`。上述版本不是一份统一config；特别是显式H_matrices已覆盖仍残留的H_scales字段，不能误用后者。

| 标记 | 既有资产/数字 | 本任务使用边界 |
|---|---|---|
| FACT | 早期five_node_v2有reference_schedule和closed_loop两种协议；32测试Seed；200–249内每个机会Replay第8个前序包。 | 可证明工程曾启用SoD并保存`sends`；不能证明单包Replay的事件差异或辅助检测收益。原报告§模型与权限/数据与校准，原run_study.py:128–153 |
| FACT | G1 sequential strong：192测试Seed，12主比较5项通过、完整cell仅1/4；carry补充step为3/4，half-step无稳定优势。 | 外生日程、带裁剪/衰减/隔离的MSE对照，非被动Yang的闭环通信检测。G1 g1_experiment_plan.md§2及两原报告 |
| FACT | G1-R P0：48旧Seed、单包r200/s136/q208、固定gap8；Replay全时域节点差最大误差2.305e−13。 | 支持固定模式传播正确性；报告末段明确未验证SoD模式分叉。G1-R 07全文 |
| FACT | G1-R 100-Seed：主场景91报警、85正确归责，健康10/100报警；固定日程。 | 这是未知候选接收事件的单决策检测/归责结果，不是通信特征检出率。G1-R 18§检测、正常代价和通信 |
| FACT | E2：400Seed、20批完成；公共集合覆盖主场景200/200，独立4800组合零差异。 | 恢复集合覆盖及动作门槛，不能当SoD通信检测证据。G1-R 21§主门槛、22全文 |
| FACT | E3：COMPLETED、NO_GO_PERFORMANCE；Set主场景MSE9.6618472242，相对Yang9.8996305110下降2.40194%，未达Hard/Soft优势。 | 真实恢复评价；不等于攻击检测成功、闭环通信改变或发送侧信道有效。G1-R 26§3–4、§8 |
| FACT | G7-R0：NO-GO；旧代码用经验联合矩和episode最大值，非错误的独立卡方阈值。 | 继承否定把SoD条件分布/选择效应/条件阈值包装为新贡献的结论。G7§3、§10 |
| OPEN | 单次Replay、被动原Yang、真实闭环SoD下，节点1发送是否改变、改变多少、残差外是否增加实用价值。 | 本轮没有生成数据或计算这组性能，不从上述不同协议拼接肯定结论。 |

## 6. 信息价值与部署边界

**FACT。** `SequentialController.update`和`MonitorController.update`虽有`local_hat`参数，但实际评分使用measurement减aligned cache；未保存自己的last_send状态，也没有发送行为统计。G1-R全前缀归责只用接收记录、本地创新和公开固定schedule；E2/E3在线输入仅12维z、公开模型、门限、方法。

**DERIVED。** 若节点i的合法信息已包含完整自身估计历史`hat_x_i(0:t)`、公开触发规则及初始化，则自身发送历史`S_i(0:t)`是其确定性函数，不增加相对于这个完整信息集的统计信息。若原检测器只保留有限残差窗，它可能是被压缩掉历史的摘要，是否改善该特定检测器是OPEN；不能先称独立证据、再把两个边际似然相乘。

**DERIVED。** 同一sender的多个出边fresh是同一个节点广播事件的重复映射，不能当两个独立证据。自身发送事件可由本机通信栈知晓，不需读取出边接收者的私有量测；读取全网Run仅限离线审计。

**OPEN。** Task1尚需负责人指定基准模型版本、单包发生机会、历史来源规则、被动采集权限和评价单位，详见 [05_open_questions.md](05_open_questions.md)。本报告不自行选择更有利的配置、增加阈值或签发实验授权。

## 7. 本轮完成与停止

**FACT。** 本轮只读文本、JSON、既有NPZ容器字段/形状并计算文件SHA256；未导入运行器执行入口，未调用`simulate`、`generate_data`或随机数生成函数，未创建实验Run、未新增Seed、未重校准、未开发检测器。仅新增本目录六个交付文件。受保护资产校验范围及结果载于02清单。

**FACT。** 不commit、不push，不修改既有G1/G1-R/E2/E3、G2/G5、engine/model/config或上一轮参考文件。完成Task0后停止，等待研究负责人审核与Task1授权；不作下一阶段Go/No-Go。
