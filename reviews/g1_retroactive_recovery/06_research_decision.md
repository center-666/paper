# G1-R 研究决策与下一步任务书

日期：2026-11-12。本文件给出第二轮复核后的当前决定；第一轮“保留 A 做限期验证”已被本轮强基线与代码时序复核取代。

## 五个问题

**1. 历史估计包离开目标缓存后，现有方法是否完整解决？**

未找到与五节点 Yang-form、Send-on-Delta 年龄缓存、单链路真实历史包 Replay、迟到发现及资源计量完全同协议的即插即用定理。但方法职责高度重叠。Deghat et al. 2019 PDF p.3 Remark 明确把邻居估计链路偏置写成观测器攻击输入，Theorem 3（pp.8–9）对 admissible biasing inputs 给网络估计修正/渐近恢复；Zhang 2022/2023 利用未来测量与 fixed-point smoother 回溯攻击前等效量；Tabatabaei 2025 用 UIO 重构链路信号并作安全补偿；Caballero-Águila 2025 给分布式固定点平滑器。不能声称“后续测量回看历史”或“网络估计攻击修正”本身新。

**2. 能否用后续本地量测修正而不恢复原始包？**

可运行的 GLS 原型已经做到：在已知边/事件时刻及固定模式下，用后续创新估计过去事件对当前估计的等效影响。但它使用 oracle 事件定位，且全网修正需要额外广播。进一步把完整窗口创新作因果 Cholesky 白化并递推信息矩阵/得分后，终值与同窗口 batch GLS 最大误差为 \(2.84\times10^{-14}\)；Replay下完整窗口估计比 post-cache-only GLS 更好。这是标准序贯 GLS/未知输入估计对有限窗口的应用，不是独立新机制。

**3. 至少能证明什么？**

- PROVED / STANDARD：固定发送/缓存模式下的增广线性影响传播恒等式。
- PROVED / STANDARD：用总估计误差条件均值修正不增加均方误差；估计攻击分量时不自动成立，存在交叉项。
- PROVED / STANDARD：完整联合协方差下，因果白化递推 GLS 的终值等于 batch GLS。
- CONDITIONAL：若增广模式族统一指数收缩，则有限历史截断误差几何下降；当前闭环 Send-on-Delta 条件尚未证明。
- DISPROVED：无攻击时误归责并施加非零修正可增加 MSE。

尚无与新方法绑定的非平凡新定理。

**4. 最有希望的学报创新与最大风险是什么？**

此前候选“有限记忆 influence capsule + post-cache GLS”现不再作为独立论文候选。直接风险是 Deghat 网络误差跟踪可覆盖链路偏置及双向网络污染，而递推 GLS 已数值等价于标准 batch GLS。闭环审计还显示，下一次未经篡改的发送载荷并不保证是健康 sender estimate：Replay 后双向环 sender 后续9次估计均偏离健康反事实。最大风险是候选只对已知攻击边/时刻修正，且把未计费广播或理想化固定日程当作免费资源。

**5. 下一步做什么？**

不继续开发 post-cache GLS/influence-capsule 新模块。若项目负责人仍需确认现有分布式防御覆盖程度，只做一个小型竞争基线适配：

1. 将 Deghat 网络误差/攻击输入跟踪结构离散适配到当前固定 Yang-form 缓存模型；明确它不是原论文 H-infinity/LMI 结果的直接复现。
2. 与完整窗口递推 GLS、post-cache GLS、fixed-lag drop-and-replay、迟到隔离做同seed配对；匹配正常误修正率并逐项计存储、通信、计算。
3. 先用已知事件边/时刻核查机制，再单独评估未知事件定位；再考虑闭环触发。
4. 若递推 GLS 或 Deghat 适配解释收益，记录负结果并归档 G1-R；只有缓存切换带来可证明的有限时域/同资源差异时才重新讨论选题。

该任务是强基线排重，不是新方法立项；不启动大规模仿真或正式写作。

## 新证据与重要口径修正

当前代码在发送迭代 r 收到数据后，立即用 age-0 包计算一致性项并更新状态索引 r+1。因此直接链路扰动是 \(\varepsilon A\Delta m\)，age=0 不是“乘法零”。驻留迭代 r+a 的直接项是 \(\varepsilon A A^a\Delta m\)。q 时停止的是攻击者对该边载荷的再次替换，不是全网状态污染。

有效的独立 Run g1r_deghat_mapping_audit_20261112_04 只在攻击包事件处注入一次差值，此后未篡改发送均由递推器自己的 sender estimate 差生成；完整五节点递推逐拍与攻击/健康仿真比较，最大误差低于 \(7.9\times10^{-14}\)。Replay 后9次 sender 估计均有间接污染，q后 receiver/network 轨迹差 RMS 为2.748/2.840；单次突变 FDI 的后续传播小得多。Run 01/02是代数循环核验；Run 03回灌了仿真sender差，属于诊断而非独立预测，均不作闭环递推证据。

Run g1r_deghat_output_channels_20261112_02 用本地 innovation 与本地 innovation 加邻居分歧做 GLS 筛选；Replay 下完整窗口 augmented 输出恢复 receiver/network excess 约为 \(-0.000636/-0.000314\)，但使用已知事件边/时刻，且不是 Deghat 的动态 H-infinity tracker 复现。Run 01 因通道名条件错误未加入邻居分歧，保留作失败运行，不作证据。

Run g1r_attack_input_tracker_20261112_02 表明完整窗口因果白化递推与 batch GLS 完全等价至数值精度。Replay下完整窗口递推 receiver/network recovery excess 为 \(-0.00328/-0.00129\)，post-cache GLS 为 \(0.01007/0.00281\)；正常测试误修正率分别6.25%与2.08%。事件边/时刻均已知，测试小且固定外生日程；这只能否定“递推GLS是独立创新”，不是 Deghat tracker 的完整适配。

Run g1r_deghat_output_channels_20261112_02 将邻居 disagreement 加入线性回归后，offset estimate 更接近模拟注入，但48个seed的 receiver/network MSE 配对差区间均跨零。故当前也没有证据说明仅把 Deghat 可用的 disagreement signal 拼入 GLS 就会带来稳定恢复收益。

另一个筛选比较把 Deghat 使用的邻居 disagreement 与本地 innovation 拼接后做 GLS。Replay 完整窗口下，它使 offset 参数估计更接近模拟扰动，但48个seed的 MSE 配对差区间跨零；没有证明增加此输出会改善恢复。因此不能把“加一项邻居分歧观测”作为方法增量。

## 五维评价

| 维度 | 当前判断 | 理由 |
|---|---|---|
| 问题是否已被直接解决 | 精确缓存协议未见同型定理；机制重叠高 | Deghat链路偏置/网络修正，Zhang回溯平滑，Tabatabaei链路重构 |
| 方法增量 | 未成立 | post-cache GLS是标准GLS截窗，递推形式等价batch |
| 理论 | 标准条件结果可证；新理论未建立 | 有限记忆界依赖未证闭环收缩条件 |
| 工程验证 | 可执行 | 当前模型与攻击可复用，但未知事件和闭环触发未验证 |
| 中文学报可发表性 | 当前不支持独立新稿 | 强基线未被击败，事件定位与修正通信成本未处理 |

## 最终决定

**停止候选 A 作为独立论文主贡献开发。** Replay 风险成立，但当前 GLS/influence-capsule 没有显示无法由标准未知输入跟踪、递推 GLS 或固定点平滑替代的能力。只允许继续一次小型 Deghat 离散缓存适配作为竞争基线审计；若它解释结果，归档 G1-R。攻击有效性成立，不等于方法新颖；方法新颖未成立，因此论文可发表性当前不支持。

只有在未知事件定位、双向污染、闭环触发和完整通信/存储成本下，出现 Deghat-inspired tracker 与标准 smoother 无法解释的可重复有限时域收益，并有缓存模式特定误差界，才重新考虑该方向。
