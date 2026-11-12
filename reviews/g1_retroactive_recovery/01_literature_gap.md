# 历史包追溯与估计污染修正：文献排重及修订审计

日期：2026-11-12。范围为邻居状态估计包在链路上被替换、其直接缓存驻留结束后才发现异常的分布式估计恢复问题。全文来源、DOI和核读页码见 [来源索引](sources/README.md)。

证据标签：LITERATURE 为原文结论；DERIVED 为项目模型推导；EXPERIMENTAL 为本地试验；OPEN 为未解决。

## 当前判断

历史 Replay 风险会延续到被替换缓存之后，但当前 post-cache GLS / 灵敏度扣除没有显示独立方法增量。最强直接竞争是 Deghat et al. 2019：原文明确把邻居估计链路偏置等效成接收节点观测器攻击输入，并用分布式攻击跟踪器修正估计。当前连续闭环网络的后续未篡改传输还会携带发送者估计的间接污染，因此其网络级 tracker 更接近实际传播。

递推攻击输入估计的终值与同一完整窗口 batch GLS 数值相等，最大差 \(2.84\times10^{-14}\)。这是标准递推最小二乘充分统计量恒等式，不是新算法。G1-R 当前应**停止作为独立论文主贡献开发**。如需判断现有网络防御是否覆盖 Replay，只可把 Deghat tracker 的离散缓存适配作为竞争基线复核，不得先包装成候选创新。

## 定理级直接比较

| 论文与定位 | 攻击对象、信息与方法 | 原文保证 | 相对 G1-R 的边界 |
|---|---|---|---|
| **Deghat et al., 2019, Automatica 99:369–381, DOI 10.1016/j.automatica.2018.10.052。** 作者稿 PDF pp.3–9；p.3 式(4)/Remark，pp.4–6 式(5)–(22)，p.8 式(30)/Theorem 3。 | 观测器状态受加性攻击输入 \(F_i f_i\) 驱动。节点使用本地创新 \(\zeta_i=y_i-C_i\hat x_i\) 和邻居分歧 \(\bar\zeta_i=\sum_jH(\hat x_j-\hat x_i)\)，以动态模型 \(G_i(s)\) 跟踪攻击输入，并用分布式 \(H_\infty\) 观测器估计网络状态误差。p.3 Remark 明确指出链路 \(i\leftarrow k\) 把 \(\hat x_k\) 替换为 \(\hat x_k+\ell_{ik}\)，可令 \(F_i=K_iH,\ f_i=\ell_{ik}\) 纳入其模型。攻击类 p.4 式(5)–(9)含常值加指数暂态与有限能量输入；节点需本地量测、邻居估计和模型。 | Theorem 1（p.6）给 detector 误差能量性质及附加稳定条件下渐近跟踪；Theorem 2（p.7）给耦合 LMI 设计条件；Theorem 3（pp.8–9）对 \(\hat x_i^c=\hat x_i+\hat e_i\) 给 admissible biasing inputs 下渐近恢复和 \(H_\infty\) 误差保证。 | 最直接算法挑战。单次缓存替换的直接链路偏置是有限支撑输入，属于有限能量攻击类；但其定理假设固定连续观测器网络，没有显式建模 \(A^{age}\) 缓存外推、异步更新、Send-on-Delta 模式切换、迟到报警和有限记忆成本。反向边的网络级误差跟踪可能覆盖后续 sender estimate 污染，不能仅以架构名称不同排除。 |
| **Zhang et al., 2022, Automatica 141, 110262, DOI 10.1016/j.automatica.2022.110262。** PDF pp.2–10；p.3 攻击模型，p.7 式(24)/Theorem 1，pp.8–10 Theorems 2–4。 | CPS 控制/传感通道完整性攻击，包括 replay、covert、zero-dynamics。后续输出测量经 H-infinity fixed-point smoother 回估攻击前时刻的等效增量。 | Theorem 1 给指定 stealthy attack 下的回溯残差及等效增量界；Theorems 2–4 给有限窗 smoother、阈值鲁棒性及可检测幅度/延迟条件。 | 未来量测回看历史攻击已有直接先例；目标是检测，不重算 Yang 网络估计器或修复其当前状态。 |
| **Zhang et al., 2023, IEEE/CAA JAS 10(4):898–915, DOI 10.1109/JAS.2023.123177。** PDF pp.1–12、15；pp.5–7 Theorems 1–2，pp.7–12 Theorems 3–5/Algorithm 1。 | 间歇 stealthy integrity attack；以固定点平滑从后续传感测量估攻击前等效量，并重置协方差。需稳定/Lipschitz 条件和已知扰动/噪声界。 | Theorems 1–2 给理想回溯检测性质；Theorem 3 给分段 fixed-point smoother 的 \(H_\infty\) 性质；Theorems 4–5 给无攻击鲁棒阈值与指定攻击条件下的检出保证。 | 与 Zhang 2022 同族，目标是回溯报警，不是重写分布式当前状态；固定点平滑器不能作为新工具。 |
| **Tabatabaei et al., 2025, Automatica 180:112460, DOI 10.1016/j.automatica.2025.112460。** PDF pp.3–7、9–11；Theorems 3.1、3.2、4.1。 | 大规模子系统通信输出 \(\tilde y_{ki}=y_k+\Gamma_{ki}\)。用 UIO/Luenberger observer 重构通信信号、攻击和状态，并用于控制；需子系统模型、可检测性/rank 与 coupling 条件。 | Theorem 3.1 给 non-stealthy FDI 下渐近重构；Theorem 3.2 给安全控制稳定性；Theorem 4.1 给特定 stealthy FDI 下全/部分状态重构条件。 | 通信信号重构与恢复已有直接相近职责；其 physical coupling/LSS 架构不同，但需核查离散化后能否覆盖 Yang 网络，不能只以架构差异排除。 |
| **Caballero-Águila et al., 2025, Information Fusion 120:103044, DOI 10.1016/j.inffus.2025.103044。** PDF pp.3–8；Theorems 1–3。 | 分布式随机系统、量化/时相关噪声及随机 deception/DoS；用 early filters 组合最优 distributed filter/fixed-point smoother，需交叉协方差和随机攻击模型。 | Theorems 1–3 给 early filtering/smoothing 与最优分布式 filter/smoother 协方差递推。 | 后续观测的分布式平滑已有；不是实际缓存攻击事件的在线轨迹修正器，需作为 smoothing 基线。 |
| **Sun et al., 2025, Automatica 176:112243, DOI 10.1016/j.automatica.2025.112243。** PDF pp.4–7，证明 pp.9–13。 | 提升系统攻击 mode、输出零化子空间与 mode discernibility。 | Theorem 1 给攻击脆弱性的充要条件；后续结果给检测/辨识条件。 | 是检测理论边界，不提供历史估计修正器；提醒区分攻击可观测性和来源归责。 |

Yang et al. 2014（Automatica 50(8):2070–2076, DOI 10.1016/j.automatica.2014.05.025）是诚实随机激活/联合误差协方差基线；Yang et al. 2019（Automatica 102:34–44, DOI 10.1016/j.automatica.2018.12.027）和 Zhou et al. 2022（Automatica 138:110151, DOI 10.1016/j.automatica.2021.110151）对当期邻居估计 FDI 用随机保护/本地残差门控。它们不回滚过去估计，但需测试是否已抑制当前 Replay 损失。

## 闭环传播审计

当前仿真器在发送迭代 \(r\) 立即消费该包并更新状态 \(r+1\)。若缓存载荷差为 \(\Delta m\)，在迭代 \(t=r+a\) 的直接单边共识增量为

\[
\Delta u_i(t)=\varepsilon A A^a\Delta m,\qquad a=0,\ldots,q-r-1.
\]

因此 age 为零表示不额外外推，不表示共识项乘零。迭代 \(r\) 当场将 \(\varepsilon A\Delta m\) 加入下一状态 \(\hat x_i(r+1)\)；状态索引 \(r\) 自身尚未受影响。直接替换输入在 \(q\) 后结束，但总网络状态差不必归零：q 包虽未被再次篡改，其 sender estimate 可已被反向边污染。

修订后的独立传播 Run ID 为 g1r_deghat_mapping_audit_20261112_04。递推器仅在 r 注入一次事件载荷差；之后所有未篡改发送均使用递推预测的 sender estimate 差，不从攻击/健康仿真轨迹回灌差值，再逐拍与两条完整仿真比较。48个相同seed、固定 gap8 下，Replay 后续9次 sender 估计均偏离健康反事实；q后 receiver/network 差 RMS 为2.748/2.840。单次 FDI 对应 sender 最大后续偏差0.033、receiver RMS 0.050。直接首更新误差低于 \(2.0\times10^{-14}\)，全网络递推逐拍误差低于 \(7.9\times10^{-14}\)。Run 03 虽有相同摘要量级，但其后续未篡改发送使用了攻击/健康仿真估计差作回灌输入，不能称独立递推；Run 01/02 的公式核验也属于循环核验。03留档，04为有效闭环映射审计。

Deghat 原文描述 observer-node compromise。将链路扰动写成接收端误差方程中的等效输入是 input-output 映射，不代表攻击者实际控制了节点状态或发送端；整个反向传播仍须 network-level tracker 处理。Run g1r_deghat_mapping_audit_20261112_01/02 的早期公式核查将预期和“实测”值由相同表达式构造，是循环核验，已作废；数据仅归档，不作证据。最终审计是 03。

## 递推 GLS 强基线

Run ID g1r_attack_input_tracker_20261112_02 将完整 \(r{:}d\) 联合残差经固定训练协方差 Cholesky 白化，递推累积信息矩阵/得分。其终值与同窗口 batch GLS 差 \(2.84\times10^{-14}\)，是标准递推最小二乘恒等式，**不是 Deghat H-infinity/LMI tracker 的复现**。Replay 下完整窗口递推的 receiver/network recovery excess 为 \(-0.00328/-0.00129\)，只用 \(q+1{:}d\) 的 post-cache GLS 为 \(0.01007/0.00281\)。两者窗口信息不同，不能据此宣称递推方法性能胜出；此结果只说明 post-cache GLS 是标准输入估计的截窗实现。同窗递推与 batch 的数值等价则足以否定“递推记忆本身是新算法”。

## 2024–2026 补查与结论

额外输出通道筛选 Run g1r_deghat_output_channels_20261112_02 将接收端本地 innovation 与本地 innovation 加邻居 disagreement 分别输入正常校准的 GLS。Replay 完整窗下，加入 disagreement 后 receiver/network recovery excess 均值为 \(-0.000636/-0.000314\)，本地 innovation-only 为 \(-0.003048/-0.001216\)；48-seed 配对差区间跨零，未显示稳定 MSE 优势。其 offset 参数估计误差更小但未转化为 MSE 改善。该试验用已知边/时刻，不是 Deghat 的 H-infinity observer 实现，只核实其所用的两类输出确有不同信息。

Güzey & Güzey 2026（SMP&T 152:103318）组合中心融合 bearing 的 NIS/似然信任、滞回恢复与 WLS/IRLS；Zhang & Yang 2026（J. Franklin Inst. 363:108914）交换局部残差检测 FDI，实时残差信息版本用 private Gaussian watermark。这些非历史回滚器，但相关组合不新。Huang et al. 2024 研究 sensor-measurement Replay；Xing et al. 2025 与 Ge et al. 2026 研究历史 innovation 隐蔽攻击，均不是接收端历史状态修正。IEEE TASE 2025 DOI 10.1109/TASE.2025.3555488 和 2026 DOI 10.1016/j.nahs.2026.101725 当前只有元数据/摘要，未据题名推断其方法；若后续仍研究，应优先获取 TASE 全文。

**结论：**准确缓存协议的资源化迟到修正问题尚无已核实的完全同型定理，但标准攻击输入跟踪、固定点平滑和增广误差传播重叠很高。当前 post-cache GLS / influence capsule 没有显示不可由现有方法替代的能力，停止作为论文主创新开发。最多继续一次离散 Deghat tracker 的同协议适配，目的仅为竞争基线审计。
