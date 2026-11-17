# Task 0：攻击与检测信息权限审计

日期：2026-11-17。FACT＝接口/协议事实；DERIVED＝由接口推导；OPEN＝待冻结或未验证。

## 1. 本任务允许的唯一攻击

**FACT（用户任务范围）。** 仅在一条有向链路的一次真实发送机会，用同一sender先前确实发送的原始历史估计载荷替换当拍正常载荷。攻击不修改传感器量测、物理过程、发送决定或发送机会，不读取接收者私有量测/未来状态。

**FACT（代码）。** `engine.py:80–105`的`replay_packet`和`replay_matched`都先检查目标边fresh。`replay_packet`通过`sends[:t,sender]`取第lag个前序发送，再用该历史时刻的估计作为载荷；当前模型是无编码的估计广播，且本任务攻击前无其他攻击，因此与真实历史广播值一致。Replay的是raw历史估计，不先乘A的年龄幂。

| 标记 | 能力或输入 | 当前实现与本任务边界 |
|---|---|---|
| FACT | 目标边 | 来自公开固定配置；incoming是按边复制，只有目标边被替换，非全节点Byzantine |
| FACT | 历史包保存 | `engine.py:92–99,129–134`；捕获真实发送序列，不从未发送时刻选包 |
| FACT | 当拍真实机会 | `fresh=transmit[:,src]`在替换之前确定；无send不攻击 |
| FACT | 当前量测/真值 | 固定lag Replay分支不读取y或x；simulate虽接收x，但该分支不用真值作选择 |
| FACT | 发送参考 | last_send_value/time在替换前更新，攻击不能直接写这些数组 |
| DERIVED | 后续触发变化 | 可由估计污染经Yang反馈间接产生；这是研究对象，不是攻击者获得触发控制权限 |
| FACT | 标签字段 | injected、replay_source、cache_bad是仿真离线标签；原监测回调不接收 |
| OPEN | 一次攻击的时间窗口 | 默认config的200–249会反复Replay，不符合单包要求。未来必须另获批确定单次机会及来源不足处理，不能直接运行原默认任务 |
| FACT | fixed age与packet lag | E2固定gap8可用age/8转换lag；闭环SoD下不成立，禁止偷换 |

**FACT。** `single_step`是首个机会加固定FDI偏置，不是单次历史Replay，不能以名称“single”替代本任务攻击。`replay_selector`支持更宽的自适应策略，接口还带此前投递payload和age（`engine.py:106–125`）；本任务没有授权这些额外策略，不将其作为默认攻击器。当前固定lag来源无需使用该接口。

## 2. 检测器合法与非法信息

| 标记 | 信息 | 可用范围/出处 |
|---|---|---|
| FACT | 本地y_i(t)、自身hat_x_i(t) | 原监测回调参数measurement/local_hat；`engine.py:163`；不得取其他节点私有量测 |
| FACT | 本节点收到的缓存、入边fresh、接收age | aligned/fresh/age，当前可靠即时通信下入边fresh对应sender发送，但不授权全网视野 |
| DERIVED | 本节点自己的发送事件 | 自己作发送决定，原则上可读取本机状态；当前回调未显式传self_send，完整自身估计历史和规则可重构 |
| DERIVED | 本节点last_send_value/time | 可从自己的发送历史维护，不能拿接收端last_receive代替 |
| FACT | 公开A/H/K、触发阈值和timeout | 当前模型与协议先验；不能动态读真实攻击标签来切模型 |
| FACT | 真实Replay来源、事件标签、δ、真状态 | 仅离线审计和性能评价；不能送进线上评分 |
| FACT | 健康配对轨迹 | 仅离线机制分析，不能把与健康发送的差作为可部署检测特征 |
| FACT | 未来量测/未来发送 | 禁止用于当前判断；只能等其实际到达后成为过去数据 |
| FACT | Run.sends全网数组 | simulator保存的离线日志，不是节点i默认可访问的全网事件总线 |

来源：`cache_monitor.py:53–60,180–197`；`sequential_cache.py:1–6,135–176`；G1-R `08_information_permission_audit.md:15–21`；`receiver_gls_writeback.py:54–69,88–149`；E2 `online_proposal.py:14–20,48–54,92–97`。

## 3. 现有接口的三项风险

**FACT。** 全网仿真回调的矩阵包含所有边，但各行对应其接收者。针对节点1的入边只能取edge0=0→1、edge3=2→1；其自身出边为edge1=1→0、edge2=1→2。不能把其他接收节点那两行的量测/缓存当作节点1额外合法信息（`config.json:11`、`engine.py:163`）。

**FACT。** `SequentialController.update`返回隔离标志乘年龄权重，`MonitorController.update`也返回隔离权重；engine会直接采用。原Yang方法名不能抵消callback的反馈效果（`engine.py:160–174`、`sequential_cache.py:176`、`cache_screen.py:68`）。旁路研究必须以不改变估计/通信为条件；本轮未接入或实现新日志。

**DERIVED。** 自身发送事件由完整自身估计历史决定，因此不能与基于同历史的残差证据默认独立。在仅有有限残差窗口的比较中，它可能提供摘要价值，但需同风险实证；这是OPEN，不是已确立新信息源。G7§4.4也已警告重复计算事件和载荷证据。

## 4. 审计结论与未授权项

**FACT。** 已有固定lag Replay分支具备“真实机会、真实历史包、单条边”的基础能力，但原默认宽窗口不保证只替换一次。已有E2/E3构景器通过start=end=r和注入计数校验实现单包，不过同时强制固定gap8，不能原样用来验证闭环通信变化（E2 `scenario_builder.py:172–188,298–345`）。

**OPEN。** 未来单次闭环构景、日志持久化和被动等价性检查由负责人决定是否授权；本轮未开发、未执行、未批准这些扩展。未发现可支持“现有检测器已经使用本节点出链路行为辅助检测”的源码证据。
