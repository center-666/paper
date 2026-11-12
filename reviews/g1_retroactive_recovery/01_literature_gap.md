# 历史包追溯与估计污染修正：文献排重与代码审计

初稿日期：2026-11-12；本轮审计修订：2026-11-13。范围是邻居估计包被链路替换、直接缓存输入结束后才发现异常时，受影响分布式估计能否恢复。全文来源 DOI 和核读页码见 sources/README.md。

## 当前判断

历史 Replay 在当前双向环模型中留下缓存后网络污染，攻击有效性成立；post-cache GLS / influence-capsule 的独立方法增量未成立，建议停止其论文主贡献开发。

Deghat et al. 2019 是最强直接近邻。Automatica 99:369–381, DOI 10.1016/j.automatica.2018.10.052，公开作者稿 PDF pp.3–9。原文 p.3 式(4)把受攻观测器表示为：

\[
\dot{\hat x}_i=A\hat x_i+L_i(y_i-C_i\hat x_i)
+K_i\sum_{j\in V_i}H(\hat x_j-\hat x_i)+F_i f_i.
\]

p.3 Remark 明确指出，链路 i<-k 把邻居估计改成 xhat_k+ell_ik 可令 F_i=K_i H、f_i=ell_ik 纳入其攻击输入模型。Theorems 1–2（PDF pp.6–7）给动态输入跟踪和耦合 LMI 条件；Theorem 3（pp.8–9）对校正估计 xhat_i^c=xhat_i+xhat_e_i 给 admissible bias inputs 下的渐近恢复与 H-infinity 性质。原文为固定连续观测器网络，未显式处理当前离散年龄缓存、周期/事件触发模式和有限记忆成本。此差异不足以自动构成创新，必须做同协议适配比较。

## 直接近邻

| 文献与定理定位 | 已有内容 | 对本问题的具体限制 |
|---|---|---|
| Zhang et al. 2022, Automatica 141:110262, DOI 10.1016/j.automatica.2022.110262；PDF pp.2–10，Theorems 1–4 | 对 CPS 完整性攻击用后续输出和 H-infinity fixed-point smoother 回估攻击前等效增量；定理保证指定 stealthy 类下的回溯检测和幅度/延迟界。 | 目标是检测，不是重写分布式当前状态；但回溯使用后续量测和 smoother 已是直接先例。 |
| Zhang et al. 2023, IEEE/CAA JAS 10(4):898–915, DOI 10.1109/JAS.2023.123177；PDF pp.5–12，Theorems 1–5、Algorithm 1 | 间歇 stealthy attack 的 backward residual、fixed-point smoother、协方差重置、鲁棒阈值和可检测性条件。 | 是回溯报警，不是估计轨迹修正；固定点平滑不能列为新工具。 |
| Tabatabaei et al. 2025, Automatica 180:112460, DOI 10.1016/j.automatica.2025.112460；PDF pp.3–11，Theorems 3.1、3.2、4.1 | 对 LSS 子系统间通信 FDI 用 UIO/Luenberger observer 重构信号、攻击和状态，并用于安全控制。 | 需要子系统模型、可检测/rank 和 coupling 条件；架构不同，但“链路信号重构并补偿”已有直接竞争。 |
| Caballero-Águila et al. 2025, Information Fusion 120:103044, DOI 10.1016/j.inffus.2025.103044；PDF pp.3–8，Theorems 1–3 | 量化、时相关噪声及随机 deception/DoS 下的分布式 filter/fixed-point smoother。 | 统计攻击模型不同，但分布式后向平滑和交叉协方差递推已有。 |
| Yang et al. 2014, Automatica 50(8):2070–2076；Yang et al. 2019, Automatica 102:34–44；Zhou et al. 2022, Automatica 138:110151 | 分别提供 Yang 随机激活估计器及对当期邻居估计 FDI 的保护/残差门控。 | 不是历史回滚器，但必须测其现有保护已经抑制多少 Replay 污染。 |
| Güzey & Güzey 2026, SMP&T 152:103318；Zhang & Yang 2026, JFI 363:108914 | Trust-aware tracking 的迟滞恢复；残差交换、窗口检测及 watermark。 | 架构不同，但信任/恢复与额外残差信息不可另包装为新组合；需计量额外通信。 |
| Sun et al. 2025, Automatica 176:112243；Huang et al. 2024 TCyb；Xing et al. 2025 TIFS；Ge et al. 2026 TCyb | 攻击可检测/可辨识条件、sensor measurement Replay 分析、历史 innovation 隐蔽攻击设计。 | 不是当前接收端缓存历史修正器；说明攻击权限、历史信号和可辨识性须严谨区分。 |

IEEE TASE 2025 DOI 10.1109/TASE.2025.3555488 与 2026 Nonlinear Analysis: Hybrid Systems DOI 10.1016/j.nahs.2026.101725 当前只获元数据/摘要，未作全文方法判断。


## 当前实验与方法排重

最终P0结果为g1r_p0_verified_20261113_v1，详见07/08。固定外生日程全时域、
两单位响应、合法缓存通道已通过独立验证。mapping_04仅到q前；output_channels_02
越权使用未发送sender状态；本轮中间04–07响应矩阵方向错误，性能及旧P0假通过均撤回。

同窗口合法cache分歧与local的MSE配对区间跨零，正常误修正风险未匹配，
不能声称已有公平算法优越性。完整窗口与post窗口数据量不同，仅作信息量诊断。
GLS同窗递推等价是标准代数，不是原Deghat式(18)动态detector。
P1逐式映射见09：辅助误差估计通信、离散cache增广、H∞条件和持续白噪声差别
使当前尚未形成忠实性能适配。没有把“无法直接套原LMI”称为数学上不可能离散化。

维持终止当前GLS/influence-capsule独立创新，保留基础恢复机制；最终决策见10。
