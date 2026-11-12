# P1：Deghat 2019逐式映射与适配判定

2026-11-13。P0最终Run通过后执行结构核验：
[g1r_p1_structure_20261113_v1](results/g1r_p1_structure_20261113_v1)。
**本轮完成适配可行性审计，未形成可核查的Deghat离散缓存性能基线，停止性能宣称。**
这不是证明所有离散适配不可能，也不是证明文献算法无效。

## 原文核对

Deghat, Ugrinovskii, Shames, Langbort，Automatica 99 (2019), 369–381，
DOI 10.1016/j.automatica.2018.10.052。使用本地14页公开作者稿，以下为PDF页码。
本轮没有新增文献下载。

| 原文定位 | 方法/保证 | 当前模型不能直接继承的部分 |
|---|---|---|
| p.3，(1)–(3) | 连续plant、固定Li/Ki、精确实时邻居H hat_x_j；局部可不可检测 | 本项目A为离散转移，K_i(k)随时刻变化，邻居稀疏发送且缓存外推 |
| p.3，(4)及链路例 | Fi fi进入observer状态；链路偏置可令Fi=KiH映射 | 实际篡改载荷也改变detector的分歧输出，不能只增加状态输入 |
| p.4，(5)–(9) | f=f1+f2，偏置/暂态及L2部分；模型稳定时跟踪误差L2，附加条件渐近跟踪 | 有限支撑输入可属于能量类，但不能由此继承当前离散闭环定理 |
| p.4，(10)–(11) | epsilon_dot=Omega epsilon+Gamma nu，fhat=Upsilon epsilon；例G(s)=d/(s+2beta)I | 局部辅助模型可离散化，完整网络、缓存/重置和噪声传递仍需新设计 |
| p.5，(12)–(17) | 本地innovation和当前邻居estimate分歧，写成网络误差输出 | 静默时只有缓存，不能读取未发送hat_x_j(k) |
| pp.5–6，(18)–(22) | 联合跟踪ei及攻击模型状态；网络内部交换hat_e_j | 当前包仅hat_x_j，没有免费的辅助hat_e_j；缓存化辅助通信尚未设计 |
| pp.7–8，(24)–(29)、Thm2 | qi*pi_i<2alpha_i，Ei>0，耦合连续LMI和对应增益 | 离散缓存、直接攻击输出通道及相关噪声需新的增广设计/证书 |
| pp.8–9，(30)、Thm3 | corrected=hat_x_i+hat_e_i，前述条件下渐近恢复及H∞能量界 | 校正总误差而非仅攻击分量；不是有限延迟MSE最优结果 |
| pp.9–10，(31)–(34)、Thm4 | 原连续增广pair可检测性，包括原网络、攻击模型与子空间条件 | 当前离散cache pair需重新核对；原条件不能直接当作本系统证书 |

原式(18)结构（e=x-hat_x）：

$$
\dot{\hat e}_i=(A-L_iC_i)\hat e_i+K_i\sum_jH(\hat e_j-\hat e_i)
-F_i\Upsilon_i\hat\epsilon_i+\bar L_i(\zeta_i-C_i\hat e_i)
+\bar K_i\left(\bar\zeta_i+\sum_jH(\hat e_j-\hat e_i)\right),
$$
$$
\dot{\hat\epsilon}_i=\Omega_i\hat\epsilon_i+
\check L_i(\zeta_i-C_i\hat e_i)+
\check K_i\left(\bar\zeta_i+\sum_jH(\hat e_j-\hat e_i)\right).
$$

H hat_e_j是额外网络状态，不等于hat_x_j，也不能无假设由本地y恢复。
本轮GLS没有这些动态，也没有求解(29)，所以旧“Deghat-inspired GLS”不能称原文适配。

## 精确离散缓存误差模型

令b_e^-(k)=x_k-本拍收包前该边预测缓存，收包后b_e^+(k)，
e_i(k)=x_k-hat_x_i(k)，s_j(k)为实际发送标志：

$$
b_{ji}^+=(1-s_j)b_{ji}^-+s_j(e_j-a_{ji}),
$$
$$
e_i(k+1)=(A-K_i(k)H_i)e_i(k)
-\epsilon A\sum_j(e_i-b_{ji}^+)+w_k-K_i(k)v_i(k),
$$
$$
b_e^-(k+1)=A b_e^+(k)+w_k,
\qquad \zeta_i=H_i e_i+v_i,\quad d_i=\sum_j(e_i-b_{ji}^+).
$$

这给出30维节点误差/缓存状态（5×2+10×2）。
d_i对当拍收到的攻击有+a直接通道；不是只改状态输入而保持输出不变。
测量噪声同时进入innovation及下一步状态，不能假设两者独立。

结构核验沿用48seed，包含clean/FDI/Replay。以上误差、cache与输出方程
全时域最大误差4.279e-13。原瞬时邻居分歧与合法缓存分歧即使clean时最大差2.8625，
Replay时126.7915；不能直接替换。单位载荷攻击在当拍d_i产生的直接分量也验证为1。
噪声和真值仅在方程离线核验中使用，未运行可部署detector或性能基线。

## 不进行性能宣称的具体原因

1. 式(18)要求邻居辅助误差估计。若在同发送机会附加二维hat_e，358条边消息至少增加
   5728载荷字节，原5728字节变11456，仍未计协议/认证开销。
   这样还只有稀疏hat_e缓存，不是原连续实时hat_e；稳定性需重新设计。
   没有把中央全部误差估计当成免费本地信息。
2. 连续LMI不能直接用于本离散增益和cache resets。把离散A当连续生成矩阵做Euler会改plant；
   只对Omega求矩阵指数也不使整个网络/增益/输出等价。周期或切换离散H∞设计可以研究，
   但当前没有已核查的相应增益、可检测性及性能证书。
3. 原无限时域L2扰动条件不适用于持续Gaussian white noise。本工程过程与全部量测
   噪声每拍期望总能量0.54，无限时域不具有限总能量；
   不能继承“估计误差趋零”声称当前MSE趋零。有限时域能量界与MSE需另定义。
4. 旧GLS也不解决这些问题。换成普通回归或任意选增益后标成Deghat会掩盖适配缺口。

**P1结果：在当前不增加辅助信息且不重设离散缓存H∞设计的条件下，未完成忠实适配。**
不输出Deghat性能排名，不声称该文已充分覆盖或已被击败。
阻碍在协议和证明前提，不在缺少Python优化包。
依据研究负责人指令在此停止性能宣称；P1可行性审计完成，后续P2据此保持有限判断。
