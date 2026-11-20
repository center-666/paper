# 局部反射攻击的联合记录与下一拍载荷：解析审查

日期：2026-11-20；基准提交：ad592aaacdb4e8e767e2d6b3f0d4dfd80e27c352。

**数学裁决：PASS，限下述标量、\(k=0\)、单次攻击和明确记录。** 本报告是解析推导及自查，并非外部同行评审或形式化认证。未运行仿真；新任务期间不修改论文稿件，上一任务尚未提交的大修工作仍保留。

## 模型、攻击和记录

令 \(x_0\sim N(0,P_0)\)、\(m_0^-=0\)、\(y_t=x_t+v_t\)、\(x_1=Ax_0+w_0\)，其中 \(v_0,v_1\sim N(0,R)\)、\(w_0\sim N(0,Q)\)、\(U_0,U_1\sim{\rm Unif}[0,1]\)。假设 \(A\ne0\)、\(P_0,R,Z>0\)、\(Q\ge0\)，物理噪声、初态和触发随机数相互独立。物理过程不受估计反馈控制，排除自然丢包。反馈使用原无饱和半开格量化器
\[
c_t=Q_\delta(m_t^-),\quad
Q_\delta(m)=2\delta\left\lfloor\frac{m+\delta}{2\delta}\right\rfloor,
\quad \gamma_t=0\iff U_t\le e^{-Z(y_t-c_t)^2/2}.
\]
发送后才允许修改载荷。接收端发送更新和一致静默更新均使用原协议，协方差标签由事件递推。记
\[
K=\frac{P_0}{P_0+R},\qquad S_0=P_0+R,\qquad
P_s=\frac{P_0R}{P_0+R},\qquad S_1=A^2P_s+Q+R.
\]
固定任意 \(b,\delta>0\)，选择
\[
0<r<\min\{b/2,\delta/|AK|\},\qquad
a_0=-2y_0\,\mathbf1_{\{\gamma_0=1,\ |y_0|<r\}},\quad a_t=0\ (t\ge1).
\tag{1}
\]
事件先确定；仅当真实发送后，攻击方才读取该拍已发 \(y_0\)。故动作对原策略信息域 \(\mathcal G_0^+\) 可测，静默时无需读取未发送量测，且 \(|a_0|<b\)。它不读取真实状态、触发随机数或未来噪声。

用 \(\zeta_t=\tilde y_t\) 表示接收载荷，静默时记 \(\zeta_t=\bot\)。严格定义
\[
R_B=(\gamma_0,\gamma_1,c_0,c_1,P_0^+),\quad
R_C=(R_B,\zeta_0,P_1^+),\quad R_D=(R_C,\zeta_1).
\tag{2}
\]
\(P_1^+\) 由事件和已知模型确定，作为冗余可信标签。\(R_C\) 不包含下一拍连续载荷 \(\zeta_1\)、下一次更新后的预测或反馈 \(c_2\)。目标MSE增量 \(J_{0,\delta}\) 比较同一量化协议的受攻与健康运行。

## 目标载荷同律及下一事件联合核

\(c_0=0\)，目标发送子概率密度为
\[
f(u)=\phi_{S_0}(u)[1-e^{-Zu^2/2}],\qquad f(u)=f(-u).
\tag{3}
\]
这里 \(\phi_S\) 为方差 \(S\) 的中心高斯密度。设 \(\tau(u)=-u\) 于 \(|u|<r\)，其余 \(\tau(u)=u\)。它是保持反射区及其补集的对合，Jacobian绝对值为1，因此对所有有界可测 \(h\)，
\[
\int h(\tau(u))f(u)\,du=\int h(z)f(z)\,dz.
\tag{4}
\]
故 \((\gamma_0,\zeta_0)\) 的完整混合分布相同；目标静默原子也不变，而非只匹配一阶或二阶矩。

有两种条件化不能混淆。在**共享物理路径** \(y_0=u\) 下，反射区内健康与受攻的下一预测分别为 \(AKu\) 与 \(-AKu\)，均位于中央格；所以在共享物理噪声与触发随机数的耦合下，\(R_B\) 逐路径相同。但 \(\zeta_0\) 变号，\(R_C\) 不逐路径相同。

要证明 \(R_C\) 同律，应条件在同一个**记录载荷** \(\zeta_0=z\)。反射区内健康隐藏真实量测为 \(z\)，受攻为 \(-z\)；两运行接收端的实际预测都是 \(AKz\)，而下一真实测量均值分别为 \(\pm AKz\)。给定发送及 \(y_0=u\)，事件概率因子仅依赖 \(u\)，故高斯后验给出
\[
x_0\mid(y_0=u,\gamma_0=1)\sim N(Ku,P_s),\quad
y_1\mid(y_0=u,\gamma_0=1)\sim N(AKu,S_1).
\tag{5}
\]
当 \(|z|<r\) 时，两运行的下一触发中心 \(c_1=Q_\delta(AKz)=0\)，且
\[
\Pr(\gamma_1=0\mid z,\gamma_0=1)
=\frac{\exp[-Z(AKz)^2/(2(1+ZS_1))]}{\sqrt{1+ZS_1}},
\tag{6}
\]
对均值变号不变。反射区外策略恒等，目标静默时也不攻击。于是每个目标载荷值的下一事件条件核相同，结合式(4)得
\[
\boxed{\mathcal L_\pi(R_C)=\mathcal L_0(R_C),\qquad
\operatorname{TV}(\mathcal L_\pi(R_C),\mathcal L_0(R_C))=0.}
\tag{7}
\]
这是指定**联合记录**同律，不是两个边缘分布相同的推断。\(P_1^+\) 是事件的确定函数。下一未量化预测也是已有记录的函数：发送时 \(AK\zeta_0\)、静默时0，所以将它加入 \(R_C\) 也不会改变该结论；这不包括使用下一拍载荷后的预测。

## 真实目标MSE增量

共享物理路径，反射事件 \(E=\{\gamma_0=1,|y_0|<r\}\) 上健康估计为 \(Ky_0\)，受攻估计为 \(-Ky_0\)。由式(5)，
\[
\begin{aligned}
J_{0,\delta}
&=4K\,\mathbb E_0[x_0y_0\mathbf1_E]
=4K^2\int_{-r}^{r}u^2f(u)\,du\\
&=\boxed{4K^2\mathbb E_0[y_0^2\mathbf1_E]>0}.
\end{aligned}
\tag{8}
\]
这里使用条件高斯均值，未假设门控与健康误差独立。\(f\) 除零点外严格正，故积分正。目标事件和协方差标签分布未变，目标协方差项没有遗漏。载荷边缘分布虽相同，其与真实状态的耦合却发生变化。

## 下一拍连续发送载荷区分该见证

时间1不攻击，发送时 \(\zeta_1=y_1\)。取由 \(R_D\) 可判定的事件
\[
\mathcal F=\{\gamma_0=\gamma_1=1,\ 0<\zeta_0<r,\
\operatorname{sgn}(A)\zeta_1>0\}.
\]
记 \(q(v)=1-e^{-Zv^2/2}\)。式(5)给出严格差异
\[
\begin{aligned}
\Pr_0(\mathcal F)-\Pr_\pi(\mathcal F)
&=\int_0^r f(z)\int_0^\infty q(v)
[\phi_{S_1}(v-|AK|z)-\phi_{S_1}(v+|AK|z)]\,dv\,dz\\
&>0.
\end{aligned}
\tag{9}
\]
被积函数在 \(z,v>0\) 处严格正，故以有界事件直接得到
\[
\boxed{\operatorname{TV}(\mathcal L_\pi(R_D),\mathcal L_0(R_D))
\ge\Pr_0(\mathcal F)-\Pr_\pi(\mathcal F)>0.}
\tag{10}
\]
这已包含时刻1随机发送，不要求每拍都发送。也可直接写出完整差异：反射区内下一发送载荷子密度分别是
\(f(z)\phi_{S_1}(y-AKz)q(y)\) 与 \(f(z)\phi_{S_1}(y+AKz)q(y)\)；下一静默原子、反射区外和目标静默支路均相同，因此
\[
\operatorname{TV}(\mathcal L_\pi(R_D),\mathcal L_0(R_D))
=\frac12\int_{-r}^{r}f(z)\int_\mathbb R q(y)
\left|\phi_{S_1}(y-AKz)-\phi_{S_1}(y+AKz)\right|\,dy\,dz>0.
\tag{11}
\]
该证据揭示的是**目标载荷与下一连续载荷之间的跨时相关性**；不是单独比较下一载荷的边缘分布。事实上，在共享物理路径下，下一反馈码和事件相同且时间1没有攻击，所以 \(\zeta_1\) 本身逐路径相同；其边缘无法区分该攻击。已有 \(\zeta_0\) 后再加入 \(\zeta_1\)，才能读到式(9)的相关性变化。

作为可积矩的交叉核对，对 \(Y\sim N(\mu,S_1)\)，平方配方给出
\[
M(\mu)=\mathbb E[Yq(Y)]
=\mu\left[1-\frac{\exp[-Z\mu^2/(2(1+ZS_1))]}{(1+ZS_1)^{3/2}}\right].
\tag{12}
\]
括号严格为正，\(M\) 为奇函数。定义 \(\Psi=\zeta_0\zeta_1\) 在 \(\gamma_0=\gamma_1=1,\ |\zeta_0|<r\) 上成立，其他情况置0（不对 \(\bot\) 相乘）。则
\[
\mathbb E_0\Psi-\mathbb E_\pi\Psi
=2\int_{-r}^r f(z)zM(AKz)\,dz\ne0.
\tag{13}
\]
它的符号为 \(A\) 的符号，所有矩有限；与有界事件式(9)一致。式(13)仅用于独立代数检查，不据无界矩直接给TV数值界。

## 限制与决定

该见证证明：增加目标连续接收载荷，甚至其可重建的下一未量化预测，仍不足以普遍恢复零TV—零正损伤保证。它与旧随机符号见证不同：旧见证会改变目标载荷二阶矩，本反射保持整个目标载荷分布。下一连续发送载荷能够区分**本见证**，但并未证明它能排除所有其他合法攻击；若时间1继续攻击，也不能沿用上面的核。

本结果不适用于未经证明的一般 \(k\)、非零初始预测、其他量化相位或更长记录；不证明完整接收日志同律，也未得到增强记录的全策略安全条件或最优损伤。事实上，\(f(u)=(Z\phi_{S_0}(0)/2)u^2+O(u^4)\)，所以当前见证 \(r\downarrow0\) 时
\[
J_{0,\delta}=\frac45 K^2Z\phi_{S_0}(0)r^5+O(r^7).
\]
不能把它当作旧遥测记录 \(\Theta(\min\{b^2,\delta^2\})\) 见证的匹配阶数。数学通过不等于新颖性通过；本轮不修改论文、不新增实验、不启动三预算研究。

依据：[原攻击信息与模型](../../papers/paper1_trusted_record_integration_20261119/sections/02_model.tex)；[量化协议与记录](../../papers/paper1_trusted_record_integration_20261119/sections/04_quantized_extension.tex)；[旧格内符号见证](../paper1_quantized_feedback_floor_audit/01_cell_internal_attack_proof.md)。
