# 按实际条件亲和度累计的信息时钟

本节核查用户给定的信息时钟定理，保持阶段四精确参数似然及参考密度定义。置信失效概率eps与量化半步长delta分开。

## 1. 两级滤过下的鞅

当前中心在本拍事件/载荷之前确定。令 \(\mathcal F_{i-1}\) 为上拍已结束历史，\(\mathcal G_i\) 为再包括当前中心的事件前历史。当前中心的生成核在两个候选假设下相同，不产生额外似然比。

固定真实参数star与一个固定错误候选theta，定义
\[
a_i=\int\sqrt{K_{\star,i}K_{\theta,i}}\,d\mu,\quad
R_t=p_\theta^t/p_\star^t,\quad J_t=-\sum_{i=0}^t\log a_i.
\]
\(a_i\) 在 \(\mathcal G_i\) 可测，不必在中心揭示前的 \(\mathcal F_{i-1}\) 已知。条件积分给
\[
\mathbb E_\star[\sqrt{R_i/R_{i-1}}/a_i\mid\mathcal G_i]=1.
\]
对中心再用塔式法则，即
\[
M_t=\sqrt{R_t}e^{J_t},\qquad
\mathbb E_\star[M_t\mid\mathcal F_{t-1}]=M_{t-1}.
\tag{1}
\]
孤立密度零点无连续质量；固定候选的有限历史测度仍互相绝对连续。本节不能将当前载荷观察后选择的参数或亲和度当作可预测输入。

若固定参考混合满足 \(q_t\ge\pi_\star p_\star^t\)，而
\(C_t^\varepsilon=\{\theta:p_\theta^t>\varepsilon q_t\}\)，则在theta保留且J_t≥h时，
\[
M_t>e^h\sqrt{\varepsilon\pi_\star}.
\]
Ville因此给
\[
\boxed{\Pr_\star(\exists t:\theta\in C_t^\varepsilon,\ J_t\ge h)
\le\min\{1,e^{-h}/\sqrt{\varepsilon\pi_\star}\}.}
\tag{2}
\]
这是联合事件的概率上界，不能改写成“给定J_t≥h后的条件保留概率”仍有同一上界。

## 2. 经过认证的上亲和度可给保守信息时钟

若每拍有事件前可预测的 \(\widehat a_i\ge a_i>0\)，可取
\(\widehat a_i\leftarrow\min(1,\widehat a_i)\)，并设
\[
\underline J_t=-\sum_i\log\widehat a_i\le J_t.
\]
此时 \(\sqrt{R_t}e^{\underline J_t}\) 为非负超鞅，(2)仍成立。区间积分的数值上端，而非普通求积点值，才可以无额外误差预算地代入该保证。

全参数盒统一常数只是特例 \(\widehat a_i=\bar a\)。更窄的事件前协方差或候选偏差包络可能给更快增长的 \(\underline J_t\)，但仍需覆盖真实模型。

## 3. 不能越过的部署边界

精确J_t包含真实参数star，属于理论分析量，当前接收端不直接知道它。若希望使用在线参数集合计算时钟，须在本拍前形成合法集合，并确保真实参数保持其中；统计覆盖失败需单独计入总概率预算。不能用本拍载荷筛选候选后反向计算本拍亲和度，再声称(1)成立。

对多个固定错误候选可分配额外概率权重再并合。连续参数则需要区间上包络或统一过程控制，不能把有限候选并合公式直接用于不可数集合。若Q不含真实原子，阶段四08的近真参考和低阶交叉矩机制仍需保留，不能把 \(\pi_\star=0\) 代入(2)。

本节提供的是收紧认证时间分析的工具，不是已部署的“真实信息时钟传感器”，也没有恢复性能实验。
