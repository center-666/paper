# 序贯事件审计定理

以下是对后置独立全周期随机相位协议的直接理论推进。它使用已有的相位平均概率式，不运行仿真。

## 定理 1：健康鞅与误报界

令 \(\mathcal F_t\) 表示当前攻击动作已提交、下一随机相位尚未抽取的滤过。审计器只用事件位和名义协方差标签，不把下一相位放进得分。若条件化在已经抽出的相位上，健康条件均值一般不再为零。

假设健康协议下，给定 \(\mathcal F_t\)，下一静默事件满足
\[
\mathbb E_0[Y_{t+1}\mid\mathcal F_t]=\nu_t.
\]
定义
\[
Z_{t+1}=\nu_t-Y_{t+1},
\qquad S_n=\sum_{t=0}^{n-1}Z_{t+1}.
\]
则 \(S_n\) 是鞅差和，且
\[
\nu_t-1\le Z_{t+1}\le \nu_t,
\qquad b_t-a_t=1.
\]
因此对任意固定 \(N,h>0\)，
\[
\mathbb P_0\left(\max_{1\le n\le N}S_n\ge h\right)
\le \exp\left(-\frac{2h^2}{N}\right).
\tag{1}
\]
取
\[
h_N(\alpha)=\sqrt{\frac{N}{2}\log\frac1\alpha}
\]
即可得到预定时域内的健康误报上界 \(\alpha\)。若连续多时刻监测，可用Hoeffding超鞅
\[
M_n=\exp\left(\lambda S_n-\frac{n\lambda^2}{8}\right),\qquad \lambda>0,
\]
和Ville不等式得到anytime边界
\[
S_n\ge \frac{\log(1/\alpha)}{\lambda}+\frac{n\lambda}{8}.
\]
阈值随时间增长，避免固定阈值反复查看导致最终误报。也可采用alpha-spending，但须明确分配总误报预算。

## 定理 2：攻击漂移与报警前累计污染

在固定 \(b_{\rm ref},\delta_{\rm ref}\) 范围内，设后置相位定理给出统一常数 \(q>0\)，且
\[
1-\frac{F_{\delta,V(P_t^+)}(AD_t)}{F_{\delta,V(P_t^+)}(0)}
\ge qD_t^2.
\]
可由模型参数显式下界 \(\nu_t\)。令 \(r_0=R+Z^{-1}\)，
\[
P_{\max}=\max\{P_0,A^2r_0+Q\},\quad
\rho=|A|\max\left\{\frac R{Q+R},\frac{r_0}{Q+r_0}\right\},\quad
g_{\max}=\frac{P_{\max}}{P_{\max}+R}.
\]
若 \(\rho<1\)，偏差递推给
\[
|D_t|\le B:=\frac{g_{\max}b_{\rm ref}}{1-\rho}.
\]
再令
\[
V_{\min}=Z^{-1}+Q+R,\qquad
V_{\max}=Z^{-1}+A^2r_0+Q+R.
\]
直接对相位平均核差积分可得
\[
F_{\delta,V}(0)-F_{\delta,V}(AD)
\ge c_FD^2,\qquad
c_F=\frac{A^2}{2V_{\max}}
\exp\left[-\frac{A^2B^2+\delta_{\rm ref}^2}{2V_{\min}}\right].
\]
因此漂移 \(s(P)[F(0)-F(AD)]\ge s_{\min}c_FD^2\)，其中
\(s_{\min}=1/\sqrt{ZV_{\max}}\)。这一步直接使用核差，
并非把 \(s_{\min}\) 当作 \(\nu_{\min}\)；归一化形式中的 \(F(0)\) 已精确抵消。可取
\[
\kappa=
\frac{A^2}{2V_{\max}\sqrt{ZV_{\max}}}
\exp\left[-\frac{A^2B^2+\delta_{\rm ref}^2}{2V_{\min}}\right]>0.
\tag{2a}
\]
这个显式常数刻意保守。若 \(\rho\ge1\)，须另找偏差有界证明，不能直接用此长期推论。
则任意合法攻击下
\[
\mathbb E_\pi[Z_{t+1}\mid\mathcal F_t]
=\nu_t\left[1-
\frac{F_{\delta,V(P_t^+)}(AD_t)}{F_{\delta,V(P_t^+)}(0)}\right]
\ge \kappa D_t^2.
\tag{2}
\]

令
\[
\tau_h=\inf\{n\ge1:S_n\ge h\},
\qquad \tau_h=\infty\text{ if集合为空}.
\]
对任意整数 \(N\ge1\)，有
\[
\boxed{
\mathbb E_\pi\sum_{t<\tau_h\wedge N}D_t^2
\le \frac{h+1}{\kappa}.
}
\tag{3}
\]

### 证明

令 \(\widehat\tau=\tau_h\wedge N\)。由条件漂移式，
\[
\mathbb E_\pi S_{\widehat\tau}
=\mathbb E_\pi\sum_{t<\widehat\tau}
\mathbb E_\pi[Z_{t+1}\mid\mathcal F_t]
\ge \kappa\mathbb E_\pi\sum_{t<\widehat\tau}D_t^2.
\]
如果在 \(N\) 及以前越过阈值，越过阈值前的累计量小于 \(h\)，而最后一步的正增量不超过1，所以 \(S_{\widehat\tau}<h+1\)。如果直到 \(N\) 也没有报警，则 \(S_N<h\)。因此始终 \(S_{\widehat\tau}<h+1\)，合并即得式(3)。\(\square\)

## 解释

式(3)是从“总体TV可辨识”到“报警前污染能量可控”的第一步。它不需要独立episode，也不假设每一拍攻击同方向。它控制的是provisional/monitor支路的条件偏差能量，不自动控制协方差项或恢复后的完整MSE。

若另外假设攻击在窗口内持续满足 \(|D_t|\ge d_{\min}>0\)，则在固定时域 \(N\) 下，若 \(\kappa d_{\min}^2N>h_N\)，下尾Azuma给出
\[
\mathbb P_\pi(\tau_h>N)\le
\exp\left[-\frac{2(\kappa d_{\min}^2N-h_N)^2}{N}\right].
\]
因此达到健康误报 \(\alpha\) 和持续攻击漏报 \(\beta\) 的充分样本量阶数为
\[
N\ge \frac{(\sqrt{\log(1/\alpha)}+\sqrt{\log(1/\beta)})^2}
{2\kappa^2d_{\min}^4}.
\]
弱偏差下检测延迟按 \(d_{\min}^{-4}\) 增长。任意间歇攻击或任意小偏差没有统一有限检测延迟；能保证的仍是累计偏差能量预算，而不是及时报警。

如果采用硬回滚，报警前monitor污染可由式(3)控制；检测延迟期间的污染已包含在停止时刻之前。报警后风险须由可信检查点支路的风险包络单独给出。检查点必须来自认证锚点或预先定义的可信更新；不能把未认证接收载荷回放后称为可信恢复。

如果事件审计残差的方向被改成 \(Y_{t+1}-\nu_t\)，攻击漂移为负，应改用下穿阈值；本包统一采用 \(\nu_t-Y_{t+1}\) 的上穿规则。
