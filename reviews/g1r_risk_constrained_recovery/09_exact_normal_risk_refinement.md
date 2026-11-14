# 09 Task 3：正常条件风险的精确收紧

日期：2026-11-14。基准7f1a33a。**结果属于情况B：在R/J0=1%、alpha=5%不变时，新统一幅度上限高于1%攻击收益的必要幅度，旧幅度排除被解除。** 不制定v2，不运行E2/E3，不修改v1、旧Run、攻击场景或滤波器。

标记：DERIVED/PROVED=本轮推导及复核；STANDARD=条件期望、Gaussian条件分布和上尾重排等标准工具；NUMERICAL=确定性浮点积分及矩阵计算，不是样本实验；OPEN=尚未验证。

## 1. 读取的是正常C_0eta，不是受攻C_0z

直接读取原NPZ中的e0_loading=L0和eta_loading=Leta，均值为0：

\[
C_{0\eta}=L_0L_\eta^T,\quad
\Sigma_\eta=L_\eta L_\eta^T,\quad
B_0=C_{0\eta}\Sigma_\eta^{-1},\quad
m_0(z)=B_0z.
\tag{1}
\]

原NPZ的Sigma_e0_z按24个攻击模型保存，是Cov(e0,z^a_h)，不能直接拿来作为正常C_0eta。本轮从全部24套模型交叉检查

\[
C_{0\eta}=\Sigma_{e0,z,h}-\Sigma_{e0,\theta,h}O_h^T.
\tag{2}
\]

最大绝对差3.4694e−18。由原加载复算Sigma_eta差0。另以Lm=B0 Leta检查Sigma_m=Lm Lm^T及残差加载(L0−Lm)与Leta的交叉矩，最大差分别6.9389e−18和7.3726e−18。

\[
\boxed{\Sigma_m=C_{0\eta}\Sigma_\eta^{-1}C_{\eta0}
=\begin{bmatrix}
.034590500404&.013976252339\\
.013976252339&.010013268439
\end{bmatrix}.}
\tag{3}
\]

其特征值约.003691518702、.040912250141，迹.044603768843，占J0=.257680803902的17.3097%。P0−Sigma_m为正定；本模型中83%左右的健康误差二阶矩不能由这段z预测。

这只是正常工况及固定创新窗口的性质。它与主Replay参数/创新典型相关约.067是不同的统计量，不能混为同一“相关性收益”。

## 2. 精确风险恒等式与信息条件

取e0=hat x_1^0(217)−x217，输出为hat x^c=hat x^0−u(z)。u对本地z可测且二阶可积，则塔式法则给

\[
\begin{aligned}
J_c-J_0
&=E_0[\|u\|^2-2(e0)^Tu]\\
&=E_0[\|u(z)\|^2-2m_0(z)^Tu(z)].
\end{aligned}
\tag{4}
\]

**DERIVED / PROVED / STANDARD。** 证明关键是E[(e0−E[e0|z])^T u(z)]=0，不是令e0与u独立。m0在本固定零均值Gaussian模型中由式(1)精确给出。

如果动作还依赖独立正常校准集Dcal，E[e0|z,Dcal]=m0(z)仍成立；式(4)可对校准集和测试轨迹共同取期望。split-conformal给的5%是这种边际约束，不能改称每个已实现校准集都满足条件5%。

若动作读取z以外的本地量测/估计/载荷数值，必须改用对应完整动作信息集的条件均值；不能沿用本报告较小的Sigma_m。固定公共日程、模型及接收时间不增加随机观测，原协议的三个候选动作均被限定为z的函数。本结论只针对d216、目标217，不推广到随机停止或累计恢复窗。

## 3. c_alpha与紧的统一风险证书

令T=||m0(z)||，A为实际非零动作事件，P0(A)≤alpha，||u||≤U，则

\[
J_c-J_0\le\alpha U^2+2U E[1_A T]
\le\alpha U^2+2U c_\alpha.
\tag{5}
\]

定义q满足P(T>q)=alpha。对任意A有

\[
E[1_A T]\le q\alpha+E[(T-q)_+].
\]

连续非退化T下取A={T>q}等号成立，因此

\[
\boxed{c_\alpha=E[T1_{T>q}]
=q\alpha+\int_q^\infty P(T>t)\,dt.}
\tag{6}
\]

这里c_alpha是**未归一化尾部一阶矩**，不是E[T|T>q]。后者还需除以alpha，不能误用于式(5)。

进一步，式(5)对所述全部动作类是锐的：取u=−U m0/||m0||·1_{T>q}，其非零概率alpha、幅度U，正常风险增量恰为alpha U²+2U c_alpha。这个动作仅为最坏风险的数学见证，不是新补偿算法，也未实现或运行。

故在只利用“动作依赖z、非零概率≤alpha、统一幅度≤U”这些信息时，新的最大统一幅度证书为

\[
\boxed{U_{new}=
\frac{\sqrt{c_\alpha^2+\alpha R}-c_\alpha}{\alpha}
=\frac{R}{\sqrt{c_\alpha^2+\alpha R}+c_\alpha}.}
\tag{7}
\]

程序使用后一形式避免相消。对所有具体算法仍需另外验证非零概率和输入权限，不能把本解析证书当作已经校准过的方法。

标准Cauchy还给出独立于尾部积分的备用证书：

\[
c_\alpha\le\sqrt{\alpha\operatorname{tr}\Sigma_m}
\le\sqrt{\alpha J_0}.
\tag{8}
\]

这证明U_new不小于原上限。收紧条件是使用正确动作信息集和联合统计，并未放宽R或alpha。

## 4. 二维Gaussian积分及数值误差

令lambda_1≥lambda_2>0为Sigma_m特征值，v(phi)=lambda_1 cos²(phi)+lambda_2 sin²(phi)。标准二维Gaussian的方向均匀、半径服从Rayleigh，于是

\[
S(t)=P(T>t)=\frac2\pi\int_0^{\pi/2}
\exp[-t^2/(2v(\phi))]d\phi.
\tag{9}
\]

解S(q)=alpha后

\[
c_\alpha=\frac2\pi\int_0^{\pi/2}
\left[q e^{-q^2/(2v)}+
\sqrt{\pi v/2}\,\operatorname{erfc}(q/\sqrt{2v})\right]d\phi.
\tag{10}
\]

独立核对使用椭圆Gaussian范数的径向密度

\[
f_T(t)=\frac{t}{\sqrt{\lambda_1\lambda_2}}
e^{-t^2(1/\lambda_1+1/\lambda_2)/4}
I_0\!\left(\frac{t^2}{4}|1/\lambda_2-1/\lambda_1|\right),
\tag{11}
\]

分别积分f_T及t f_T。程序用指数缩放的I0e避免数值溢出。两种方法均为确定性积分，不调用随机数。

另在[0,pi/2]分65536个单调区间，对S与尾部一阶矩作左右Riemann和，并将根求解容差加入q端点。由v递减可在**精确算术**下界定离散误差。报告的区间使用普通NumPy/SciPy浮点值，不是经过有向舍入证明的形式化区间算术；QUADPACK误差也只是数值估计，不标成严格舍入证书。

|量|自适应积分点估计|单调离散上下和区间|
|---|---:|---|
|95%范数分位q|.401352198929|[.401350378532, .401354019294]|
|c_alpha|.0238525390271|[.0238515924903, .0238534855926]|
|U_new|.0512612560387|[.0512594192272, .0512630929199]|

极坐标和Bessel径向积分的c差3.47e−18；包含局部根误差的c误差估计约5.85e−14，径向积分自身的c误差估计约7.43e−14。以各向同性Rayleigh闭式、秩1半正态闭式、秩0零风险交叉项作退化测试，全部通过。完整容差在运行前的[计算计划](sources/task3_normalrisk_20261114/calculation_plan.json)及Run冻结文件中。

重要的是，情况B还可以仅凭式(8)的较保守闭式证书判定，不依赖上述尾部积分最后几位或Riemann区间的浮点误差。

## 5. Task 3.3：与原场景所需幅度比较

保持J0=.257680803902、Ja=8.85609382318、R=.00257680803902、alpha=.05。原1%攻击收益的必要幅度仍为

\[
U_{req}=\sqrt{J_a}(1-\sqrt{.99})=.0149169810930.
\]

|正常风险证书|交叉项系数c|统一幅度上限U|是否仍低于U_req|
|---|---:|---:|---|
|原全误差Cauchy|.113507886048|.011322552638|是|
|仅条件均值Cauchy|.0472248710124|.0268992740204|否|
|条件均值上5%尾部，式(6)|.0238525390271|.0512612560387|否|

U_new/U_old≈4.52736，U_new/U_req≈3.43644。**判定B稳健成立**：即便不用精细尾部积分，较保守的条件Cauchy上限也大于所需幅度。

用U_new代入旧L2收益必要上界，得到约3.41540%，而不是旧U下的.75950%。这仍然只是允许该幅度的理想动作改善上界，不是任何Set/Soft/Hard的实际改善，也不说明1%改善一定能实现。

## 6. 决策与研究边界

Task 3.1通过：正常交叉矩正确提取并与原系数/24套受攻模型一致。

Task 3.2通过：Sigma_m、尾部c_alpha及U_new可计算，给出了积分形式、误差估计、单调离散区间和闭式退化测试。

Task 3.3属于B：**相同1%正常期望风险预算下，旧统一幅度排除可以解除。** v1的旧上限和原停止结果仍有效，不重写历史；本轮没有生成v2协议。

唯一建议是保留“利用正常条件风险结构约束历史补偿”的下一阶段论证资格。下一步若制定v2，需明确所有方法使用相同新证书或同一动作风险约束，再冻结动作与校准规则；这不是本轮的算法开发任务。

尚未证明：集合覆盖是否足够紧、实际非零率是否可用、正常实际MSE变化、攻击MSE改善、先验失配优势或论文创新。联合Gaussian投影与尾部重排都是成熟工具，这次数学收紧不能单独包装为核心创新。

不执行动作特定风险优化，不改变原攻击/通信/增益/预算，不启动E2/E3，不追加seed。任何未来正常滤波改善须与攻击恢复收益分开评价，本轮没有这些性能数据。

## 7. 可复现交付

代码：[exact_normal_risk_refinement.py](code/exact_normal_risk_refinement.py)。
Run：[g1r_task3_normalrisk_20261114_r01](results/g1r_task3_normalrisk_20261114_r01/summary.json)。
完整C_0eta、Sigma_eta、B0、Sigma_m和残差误差矩见[normal_risk_moments.json](results/g1r_task3_normalrisk_20261114_r01/normal_risk_moments.json)。

复现使用新Run ID，拒绝覆盖旧目录：

    .\.venv\Scripts\python.exe -B -X utf8 reviews/g1r_risk_constrained_recovery/code/exact_normal_risk_refinement.py --out reviews/g1r_risk_constrained_recovery/results/g1r_task3_normalrisk_reproduction_01

本轮0新随机轨迹、0下载；新Run只包含矩阵、数值积分及校验结果，不是新防御性能实验。
