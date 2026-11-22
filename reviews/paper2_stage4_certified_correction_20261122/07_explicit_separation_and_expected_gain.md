# 显式亲和度界与最终期望MSE改善：可复算常数

本文件补全最新附件的“有限幅值字典→功能收缩→期望收益”链，另给一个不依赖网格最大值的亲和度上界。全部为解析式和确定性外向舍入计算，没有性能仿真。

## 1. 移动零点给出可计算的统一分离

沿用01中的共同条件核，设幅值 \(a_1,a_2\in[0,b_{\max}]\)、\(|a_1-a_2|\ge\eta>0\)，先验偏差 \(d_i\in[-D,0]\)、\(S\in[S_-,S_+]\)、\(|r|\le\delta_q\)。记
\[
M_\phi=(2\pi S_-)^{-1/2},\quad
m_\phi=(2\pi S_+)^{-1/2}
\exp\!\left[-\frac{(\delta_q+\tfrac32b_{\max}+D)^2}{2S_-}\right],
\]
\[
m_\eta=m_\phi(1-e^{-Z\eta^2/8}),\qquad
w_\eta=\min\left\{\frac\eta2,\sqrt{\frac{m_\eta}{2ZM_\phi}}\right\}.
\tag{1}
\]
以第一个发送密度零点 \(u_0=r+a_1\) 为中心，取 \(|u-u_0|\le w_\eta\)。则
\[
f_1(u)\le M_\phi Z w_\eta^2/2\le m_\eta/4,
\quad |u-r-a_2|\ge\eta/2,\quad f_2(u)\ge m_\eta.
\]
后一个高斯下界使用 \(|u-a_2-d_2|\le\delta_q+b_{\max}+w_\eta+D
\le\delta_q+\tfrac32b_{\max}+D\)。所以
\[
1-\mathcal A(K_1,K_2)
=\tfrac12\|\sqrt{K_1}-\sqrt{K_2}\|_2^2
\ge\tfrac12(2w_\eta)(\sqrt{m_\eta}-\sqrt{m_\eta/4})^2
=w_\eta m_\eta/4.
\]
得到明确的全参数盒上界
\[
\boxed{\mathcal A(K_1,K_2)\le
\overline a_\eta:=1-w_\eta m_\eta/4<1.}
\tag{2}
\]
这利用一个局部密度区间，刻意保守；它不是最优收缩率，也不是把有限网格中最大的亲和度当作全局上界。

## 2. 有限字典的收缩式与起点遗忘

01的起点约定为旧候选 \(k\le t-L+1\)，最近候选 \(t-L+2\le k\le t\)。攻击年龄 \(n=t-k_\star+1\ge L\)。设幅值字典大小J，真实原子参考权重为 \(\pi_\star\)，并用(2)同时控制真实幅值对0及字典其他幅值的分离。则
\[
\varepsilon_{t,L}\le\min\left\{1,
\frac{(J-1)(t+1)\overline a_\eta^n+
(L-1)\overline a_\eta^{n-L+1}+\overline a_\eta^n}
{\sqrt{\varepsilon\pi_\star}}\right\}.
\tag{3}
\]
这里未来全部起点和永久健康合并一次；“晚起点但幅值错误”在开始前对0分离、开始后对错误幅值分离，故可用全部n拍指数。不是把静默时没有物理注入误认为每拍必然发送；分离针对包含静默原子与发送次密度的完整核。

01用了幅值全集的粗上限B；当比较剩余的同幅值 \(b_\star\) 候选时，可以改用更紧的同幅值上限 \(b_\star c_B\)。旧起点与真实起点均在截断前启动，故
\[
|\theta_t(k,b_\star)-\theta_t^\star|\le b_\star c_B\rho^L.
\tag{4}
\]
在至少 \(1-\varepsilon-\varepsilon_{t,L}\) 概率下，真实参数保留且坏候选全部排除，因而
\[
0\le\theta_t^\star-L_t\le b_\star c_B\rho^L.
\tag{5}
\]
此处L_t为**有限反演字典的精确下确界**。数值程序若只返回更保守的近似z，还需控制 \(\inf_C\theta-z\)，才能继承该收缩速率。

## 3. 发送机会把功能收缩转为期望风险改善

取最小整数L满足 \(c_B\rho^L\le k_-/2\)。真实发送时 \(\theta_t^\star\ge b_\star k_-\)，且条件发送概率至少
\[
p_s=1-[1+Z(p_-+R)]^{-1/2}.
\]
所以令 \(v_\star=(b_\star k_-/2)^2\)，由覆盖、候选排除和发送事件的并合界（不要求独立），有
\[
\mathbb E L_t^2\ge v_\star[p_s-\varepsilon-\varepsilon_{t,L}]_+.
\]
结合02同一monitor输出校正恒等式，得
\[
\boxed{
\mathbb E[(x_t-m_t^a)^2-(x_t-m_t^r)^2]
\ge v_\star[p_s-\varepsilon-\varepsilon_{t,L}]_+
-2\varepsilon B_{\max}^2.}
\tag{6}
\]
若
\[
\varepsilon<\frac{v_\star p_s}{v_\star+2B_{\max}^2},
\tag{7}
\]
则固定字典和真起点下 \(\varepsilon_{t,L}\to0\)，故从某一有限时刻起，式(6)严格为正。它证明的是理论精确下界校正最终降低真实无条件MSE，不是恢复到无攻击轨道，也不是512拍可用的结论。

## 4. S1/U1预算与保守时间

取 \(b_{\max}=0.25\)，复算得到：

| 模型 | L | c_B | rho | b=.05时epsilon上限 | b=.10时epsilon上限 | b=.25时epsilon上限 |
|---|---:|---:|---:|---:|---:|---:|
| S1 | 6 | 0.956938 | 0.724253 | 0.01123% | 0.04486% | 0.27722% |
| U1 | 12 | 1.061296 | 0.868202 | 0.01692% | 0.06752% | 0.41556% |

6和12只控制同幅值旧起点污染差，并非检测/认证时延。检测误报alpha=1%与校正置信失效epsilon应分别设计。

为量化保守性，固定精确参考混合：健康权重1/2，三幅值等权，\(w_k=1/[(k+1)(k+2)]\)，真起点200，校正epsilon=0.001。对强攻击b=.25，幅值最小分离eta=.15。外向区间计算给：

| 模型 | Hellinger缺口下界 \(1-\overline a_\eta\) | 本充分界给出的攻击年龄 |
|---|---:|---:|
| S1 | 约6.45e-6 | 4,398,227拍 |
| U1 | 约5.85e-6 | 4,813,844拍 |

这些时间通过(3)/(6)计算，并验证从该年龄后多项式×指数项单调下降。它们是非常宽松的充分上界，**不是实际认证时间预测，也不是512–2048拍恢复不可能的下界**。弱/中档在epsilon=0.001时连(7)都不满足，代码明确返回“该充分风险预算不通过”，没有虚构时延。

[compute_separation_bounds.py](compute_separation_bounds.py)使用50位外向Decimal区间给出常数及排除误差的可靠端点，[separation_bounds.json](separation_bounds.json)保存完整值。π使用已知双端十进制包围；exp/ln/sqrt按Decimal正确舍入契约外扩一ULP。其认证语义仍依赖该算术实现，非形式化定理证明。

这使阶段四的缺口更具体：有限字典理论链已闭合，但现有显式速率远未证明工程时域内有效。随后08给出稠密精确参考下连续幅值的存在性收缩，10补充有限参考下包络；连续幅值的数值认证时间和实际求解效率仍未完成。继续工作应收紧真实条件参数域和函数级排除上界，不能用大量轨迹替代缺失证明。
