# 03 数学问题与最小实现合同

日期：2026-11-14。状态：CONDITIONAL / 待全文排重及机制验收。这里规定可执行接口，不是已实现防御。

## 1. 保持的模型与信息

保持原五节点二维Yang-form、原增益、gap8外生日程、单次实际发送包Replay。系统、初态/噪声条件及合法信息沿用[此前模型说明](../cross_phase_identifiability_audit/01_scope_and_model.md)。本轮不重新验证传播。

节点1在d=216读取到y_1(216)，首个输出修正目标统一为t*=217。hat x(216)为用y(216)前的状态；不能拿G_216修正hat x(217)。

在线对象只包括

\[
\mathcal I_1(d)=\{y_1(0:d),\hat x_1(0:d+1),
q_{j1}(r),r\le d\text{ 且确有接收},\tau_{j1},A,H,K,\sigma\}.
\]

其中公共固定日程sigma是已知协议，不是其他节点私有轨迹。q为实际投递载荷。真状态、真h、theta、Replay来源、原始未篡改包及未来量测不得进入在线函数。

## 2. 已退出缓存的字典与观测

原冻结字典的10事件只保留q_h<216的8个：

|边|历史接收时刻r|下一收包q_h|
|---|---|---|
|0→1|176、184、192、200|184、192、200、208|
|2→1|178、186、194、202|186、194、202、210|

r208/q216和r210/q218不纳入“已退出缓存”主问题。真实事件若不在字典，覆盖保证不适用，必须单独标记字典漏覆盖。

第一实现采用共同纯post-cache创新

\[
z=\operatorname{col}_{k=211}^{216}(y_1(k)-H_1\hat x_1(k))\in\mathbb R^{12}.
\]

所有候选、Hard GLS和集合方案用同一z及Sigma；不加入缓存驻留残差。该窗比旧full-prefix 176—216信息少，不能直接沿用旧报警率/阈值。旧full-prefix结果保留作历史参照；若后续新增full-prefix基线，须明确它获得了更多证据，不能说被公平击败。

完整固定模式响应给真事件的逐样本恒等式

\[
z=\mu+O_h\theta_h+\eta^0,\qquad
\Delta_{217}=G_{h,217}\theta_h.
\tag{1}
\]

O、G由已验收传播函数和公共模型获得，不读取未来sender差。后续未再次篡改的包可以携带污染。(1)对真h成立；错误候选的剩余项不能叫健康创新。

## 3. 集合构造：完整的不依赖标签接口

### 3.1 最简标准构造

先冻结mu、Sigma及字典。令

\[
R_h(\theta)=(z-\mu-O_h\theta)^T\Sigma^{-1}(z-\mu-O_h\theta),
\quad \Theta_h=\{\theta:R_h(\theta)\le t_\beta\},
\quad D=\bigcup_hG_h\Theta_h.
\tag{2}
\]

t_beta可由独立正常轨迹的max_h R_h^0(0)顺序统计量得到。固定线性日程下真值残差等于健康反事实残差，允许Replay幅值与噪声相关。详细证明、同时覆盖和事件选择条件见[数学审计](02_mathematical_audit.md)。

已知正确Gaussian模型时也可用卡方并合界，无需新增训练；若mu/Sigma来自估计，必须把整个冻结评分置于校准流程，不能沿用精确卡方解释。集合推断本身是STANDARD。

若满秩，GLS中心hat theta_h及最小残差r_h给

\[
D_h=c_h+L_h\mathbb B,\quad c_h=G_h\hat\theta_h,
\quad L_hL_h^T=(t_\beta-r_h)G_h(O_h^T\Sigma^{-1}O_h)^{-1}G_h^T.
\tag{3}
\]

r_h>t_beta即空集。空并集必须拒绝，不能输出“零污染已确认”。若秩亏且ker O_h不能包含于ker G_h，则影响可能无界；不能靠事后clip伪造覆盖。

### 3.2 必须允许的标准强版本

使用K_h eta的参数误差椭球，再以兼容性残差筛事件，可以更紧；筛选与估计误差分配总beta，或将全部动作整体校准。不能只保留top-1/top-k却不计丢真事件风险。该版本是标准联合推断基线，不是待发明新理论。

独立Replay校准为可选验证口径，必须按年龄及事件/选源机制分别定义分布；不能把年龄64的覆盖宣传到32/96或任意攻击者。

## 4. 两个不同的优化对象，不能混称

### 4.1 附件提出的Chebyshev补偿

\[
u_U=\arg\min_{\|u\|_W\le U}\sup_{\Delta\in D}\|\Delta-u\|_W,
\quad\rho_U=\sup_D\|\Delta-u_U\|_W.
\tag{4}
\]

它保证真Delta在D时与健康反事实的距离不超过rho_U，**不保证相对受攻轨迹的真实MSE下降**。必须用受限rho_U；无约束半径可能不可实现。

单一中心对称椭球且中心可行时，(4)仍输出GLS影响中心；只加椭球而没有改变动作，属于附件明确排除的退化方案。

### 4.2 若要求真实损伤差证书

附件三门槛不构成非恶化证书。健康误差e0=hat x0-x满足||e0||_W≤B时，可用标准凸上界

\[
\Phi_B(u)=\|u\|_W^2+2B\|u\|_W-2\inf_{\Delta\in D}\langle u,\Delta\rangle_W.
\tag{5}
\]

Phi_B(u)≤0才是在集合及健康误差界成立时不增加单拍真实损失的充分条件。令p为0到conv D的投影、m=||p||_W，则最小化(5)的动作是

\[
u=0\ (m\le B),\qquad
u=\min(U,m-B)p/m\ (m>B).
\tag{6}
\]

这是对风险语义的修正，不是本轮已批准替换的算法结构；没有开发第二套防御。若未来选择(6)，不能同时宣传Chebyshev最优性。B须来自有依据的误差覆盖，不得令B=sqrt(Pbar)并当作逐样本界。

只凭D覆盖，无法保证攻击场景期望MSE改善；高概率非恶化也不是“给定接受后的95%安全”。这些是性能声明必须遵守的边界。

## 5. 正常风险预算与时间范围

若正常执行概率≤alpha，||u||_W≤U，真实健康误差二阶矩≤Pbar，则

\[
J_c-J_0\le\alpha U^2+2U\sqrt{\alpha Pbar}.
\tag{7}
\]

对alpha>0，规定正常增量预算R后，

\[
U\le[\sqrt{Pbar+R}-\sqrt{Pbar}]/\sqrt\alpha.
\tag{8}
\]

R、alpha、Pbar依据、W以及单拍或累计目标均须在E2/E3前冻结；本轮不假装这些参数已经得到负责人确认或实验选择。很小的U可能使恢复收益消失，是应报告的失败风险，不能在最终测试后放宽。

主机制先只修正t*=217的输出，不能用单拍理论支撑217—260的累计恢复。若评价整个恢复窗，需要每拍G_t、D_t、U_t并证明相同误报事件下的累计界；不得读取未来y。基于d时刻估计theta向前传播修正量是因果的，但未来模型及模式必须保持冻结外生日程。不同时间的集合中心并不一定对应同一个theta，需明确采用的是逐拍输出决策而非内部一致回写。

## 6. 资源及模块边界

M候选、p=n=2、m维创新：稠密共同白化存储O(m²)，O_h/G_h字典O(Mmp+Mnp)；每次GLS评分O(Mmp)（白化后），标准小维椭球/凸计算另报实际求解时间。若在线逐候选不同窗口，不能再称只存一套白化矩阵。

线上不发验证消息，仅用本地记录，新增通信0字节；离线训练/校准资源须另报。若保存本地checkpoint和历史收包用于回滚，其历史存储也必须计入基线。当前没有求解器实现、测时或存储实测，不能将复杂度公式写成已测优势。

拟议最小函数边界：build_dictionary(local_receive_log, public_schedule)、post_cache_features(local_measurement, own_estimate)、invert_sets(z, public_response, frozen_calibration)、choose_action(sets, frozen_budget)。不得向函数传整个run对象、攻击场景名、truth、true_event或replay_source。
