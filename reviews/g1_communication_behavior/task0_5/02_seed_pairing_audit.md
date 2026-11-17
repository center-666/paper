# Task 0.5.1：历史文件完整性及Seed配对审计

**FACT。** 审计对象严格限两份指定NPZ；未读取test_inputs.npz、nominal_gains.npz或其他轨迹文件。本轮另读取config、环境、完成记录、版本说明、报告、历史源码和per_seed_metrics.csv元数据以核验来源。完整字段顺序、shape、dtype、min/max、NaN/Inf见01_data_integrity_audit.json的npz对象；两臂均7字段、全部有限，weights全1、clipped全False。

| 文件 | SHA256 | Task0匹配 |
|---|---|---|
| yang__clean.npz | 82f52b118a9a948c72771b39a636b63180114aef9449d67b03617234237bc16c | 是 |
| yang__replay_packet.npz | ad92ba0f2974ce6189a76bd9d1d6897b62f711ed97639104e8142c09b381e766 | 是 |

## 配对证据链

**FACT。** 历史config.json的test_seeds为start=40000、count=32。sources/model.py:81–83以有序range展开；93–100为各Seed单独default_rng、生成初态及过程/量测噪声。只阅读该源码，未执行数据生成。

**FACT。** 哈希核验过的sources/run_study.py:131–153只生成一次testseeds和x/y，然后两种通信protocol、每方法每场景共用这些对象。同一次simulator返回的第s行和同索引Seed同步写入NPZ及per_seed_metrics.csv。两目标arm的CSV行Seed顺序均为40000–40031，逐行网络广播数、边消息数、注入次数和裁剪率与NPZ重算完全一致。

**FACT。** 历史run_study.py:136–144明确closed_loop传schedule=None；engine.py:59–74按当前估计、上次发送参考、timeout计算事件。clean/Replay共用同一模型及名义增益，攻击分支仅替换链路载荷，不改x/y。weights=1、无裁剪与原Yang方法一致。历史engine/model/run_study的实际SHA逐项等于environment.json记录，详情见01。

**FACT（配置副本差异已解释）。** Task0记录的配置是隔离worktree的LF副本，主工作区原件为CRLF；初次脚本直接比较这两个不同字节来源而暂停，随后证实只有155处换行差异，规范化换行后字节完全相同，JSON参数逐项一致。01保留两个原始摘要及暂停说明，没有改写原件或降低NPZ摘要校验。

**FACT。** 全32Seed首次注入之前及注入r当拍，全节点估计与发送数组逐元素完全相等，最大状态差0；不能只凭“都是32行”作配对推断。本轮通过源码来源链、Seed元数据和数值前缀一致性确认配对。

**边界。** 两目标NPZ本身未嵌入Seed/x/y，故原始噪声不在这两个文件内；本轮没有额外读取或重生噪声逐元素比对。配对结论是可审计的历史生成来源和数值一致性结论，不是外部数字签名认证。

## 注入语义和原件保护

**FACT。** 共603次注入，逐次核验目标sender确有发送，来源严格早于r且为该受攻臂sender此前第8个真实发送包，非注入处source=-1。cache_bad表示“当前缓存仍为直接替换载荷”，按fresh覆盖规则重构零不匹配；它不是当前估计污染标签。

**FACT。** 每Seed注入次数18 [13.75, 22.25]；范围9–33，首次注入时刻201 [201, 203]；范围200–208。这是窗口内多次Replay；单包局部公式只核验首次注入后的下一拍。

**FACT。** 保护清单记录输入和核心文件前后摘要，Git HEAD/已跟踪差异不变。本轮未调用simulator、generate_data、旧runner或任何随机数生成器。未修改NPZ、配置、原结果；没有commit/push。
