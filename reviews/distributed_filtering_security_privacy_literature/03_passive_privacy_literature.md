# 03 被动窃听与隐私保护：全文证据与空白

## 1. 先区分三类目标

差分隐私（DP）约束相邻数据集的输出分布，通常以 \((\epsilon,\delta)\) 定义；信息论隐私通常以互信息、条件熵或估计误差衡量；密码学安全依赖密钥、认证和计算假设。三者不能互相替换，也不能用“加入 Gaussian 噪声”同时声称三种保证。

## 2. 已核实的安全—隐私直接文献

### Wang et al. 2025：已知/未知隐私噪声协方差

Wang et al., Automatica 173 (2025) 112071, DOI 10.1016/j.automatica.2024.112071。当前读本是 arXiv:2405.16905v2 作者稿，全文 15 页，正式版尚未逐式比版。

PDF pp.3–4 式(1)–(19)：互联子系统、Gaussian 过程/量测噪声和攻击者修改控制/量测。p.4 Assumption 1 要求局部可观/可控相关秩条件。p.5 式(20)–(25)利用邻居状态和耦合模型构造残差并做 GLRT。

p.6 式(26)发送

\[
\theta_{ij}(k)=\hat x_i(k)+\alpha_{ij}(k),
\]

其中 \(\alpha_{ij}(k)\) 是零均值 Gaussian 隐私噪声。pp.6–8 式(29)–(42)堆叠状态/发送轨迹，以互信息衡量隐私；轨迹噪声协方差采用按时间块的 \(I_K\otimes\Sigma_\alpha\)，即模型中每个时间使用独立噪声样本。Theorem 1 给隐私噪声协方差与攻击检测性能之间的权衡。pp.8–12 式(43)–(62)、Theorem 2 和 Proposition 1 处理未知 \(\Sigma_\alpha\)：沿用错误白化会改变虚警和非中心参数，使用正常 secondary data 估计协方差并构造 GLRT/CFAR；需要足够多干净样本和相应统计独立性。

**不能直接继承：** 该文的未知协方差问题已经研究过，不能把“估计未知噪声协方差”作为新点；但其 \(I_K\otimes\Sigma_\alpha\) 与本项目缓存包被重复外推的 rank-deficient 轨迹协方差不同。是否能在接收端合法信息下构造非退化风险证书仍 OPEN。

### Ye et al. 2025：False Noise Attack Detection

Ye et al., Automatica 179 (2025) 112387, DOI 10.1016/j.automatica.2025.112387，作者大学托管正式排版 PDF 18 页。pp.4–5 式(9)–(21)在微电网分布式控制量中注入合法差分隐私噪声；噪声由递减 Gaussian 状态 \(\theta_{i,k}\) 生成，差分形式带有跨迭代相关结构。p.5 Assumptions 1–2 需要两跳字段转发、内部价格/储能参数和一定投票条件。

pp.5–7 式(22)–(37)使用系统模型消去差分噪声，形成残差；pp.7–8 式(38)–(50)用历史残差能量熵和多数投票检测 false-noise/FDI。Theorems 1–4 只在指定 Gaussian 噪声、模型和攻击假设下给渐近检测结论；并不保证任意攻击分布、任意一跳估计包或 Yang 型闭环 MSE。p.9以后重点是检测，攻击移除后的融合恢复不是本项目可直接继承的结果。

### Peng et al. 2025：统计—时间安全融合

Peng et al., IEEE Sensors J. 25 (2025) 29966–29981, DOI 10.1109/JSEN.2025.3581080，PDF pp.3–10 式(1)–(3)、(17)–(40)、(44)–(75)。它在扩散 RLS 中对邻居参数估计使用当前 sort/median spatial reference，再用 temporal smoothed reference 和 generalized correntropy 统计特征调节融合。它明确面对 noisy interference 和 adversarial sensor network。

但其参数迭代索引、双类 cooperative/non-cooperative estimate 和每轮多标量发送不同于 Yang 的共同状态、缓存年龄和事件间隔。它证明的是鲁棒扩散估计的相应误差性质，不能直接转化为 Yang 缓存 MSE 定理；“统计—时间融合”本身已是直接先例。

## 3. 传统隐私保护工具的迁移边界

Mo & Murray 的 privacy-preserving average consensus、动态 mask、state decomposition/dynamic mask、eavesdropping-aware DKF 和 differential privacy fusion 都属于需要单独区分信息权限的工具。当前项目尚未在工作区找到这些文献的完整原文，故不填定理号和公式号。不能用二手综述代替全文。

一般迁移关系如下：

- 动态 mask 可以隐藏初始状态或通信轨迹，但若接收节点仍需做攻击检测，mask 的可消除性和攻击者可见性必须同时说明；
- DP Gaussian 机制给的是邻接数据集分布保证，不自动给闭环状态估计 MSE 上界；
- 信息论互信息可以随噪声增大而下降，但不能直接变成攻击可检测性或安全融合性能；
- 若同一个随机扰动随缓存包多拍外推，联合噪声为低秩结构 \(\Gamma=\mathcal A\Sigma_\xi\mathcal A^T\)，不能用把重复观测当独立样本的普通协方差估计；
- 没有可信密钥、可信种子或可验证协方差时，攻击项与隐私噪声在统计上可能不可辨识。

这些是 DERIVED/OPEN，不是已证明的新算法。

## 4. 目前真正未解决且可核查的点

最具体的空白不是“加入隐私噪声”，而是：在一跳 Yang 缓存协议中，发送包携带合法隐私扰动，接收端在缓存期间重复使用并按系统矩阵外推；当隐私协方差只知道一个集合或上界时，如何构造不把重复使用误当独立样本的可部署融合风险证书，并将其与攻击风险区分开。

它必须与协方差膨胀、CI/ICI、Wang 的未知协方差 GLRT 以及 Peng 的统计—时间融合比较。若最后只能得到“重新计算联合协方差”或现成 CI，方向不成立。
