# P6.1：第一篇论文审查基线与模型

日期：2026-11-18。FACT＝原文/原稿事实；DERIVED＝明示推导或审稿判断；OPEN＝未关闭证据；HYPOTHESIS＝待验证设想。

## 1. 基线与授权

**FACT。** 对象是第一篇《随机触发估计的隐蔽攻击损伤界》，不是 ACK-V1 的 P6。GitHub main 和本地 main 均为 490e5b8f1212004407a0cdbfde224bf90a691da4。本轮从此提交创建 paper1-p61-theorem-literature-audit 独立分支/工作区；不覆盖原 main 中既有 G5 修改及其他未跟踪资产。

**FACT。** 两份用户附件要求优先定理级精读 Shang–Yu–Chen 2022 和 Guo–Zhou–Chen 2025，并核查指定直接近邻。用户补充 Zotero 后，Shang–Chen 2021 和 Guo 等 2023 也取得正式全文并纳入本轮。只新增审查报告，不改正文、代码、算法或配置，不运行随机实验；完成后按用户持续授权推送结果。

## 2. 过时信息与易混题录

| 附件/历史信息 | 本轮核实结果 |
|---|---|
| Shang 随机事件论文尚无全文 | 保留目录已有 8 页正式刊版，2026-10-10 下载，本轮重读 |
| Guo 2025 尚无全文 | 保留目录已有 9 页正式刊版，本轮重读 |
| 10.1109/TAC.2021.3125430 | 是另一篇 KL 线性创新攻击论文，67(11):6082–6089 |
| 随机事件论文正确 DOI | 10.1109/TAC.2021.3071948，67(4):2052–2059 |
| Guo 2023 与 Guo 2025 | 前者 Haibin Guo 等；后者 Ziyi Guo、Jing Zhou、Tongwen Chen，不是同一作者组 |
| 现稿完全没有对比这些权限 | introduction.tex 已区分源端滤波、攻击调度、可信实际反馈、联合 TV 与峰值；不能把附件全部修改建议当作尚未完成 |
| 部分观测/多步静默是空白方向 | 仓库已有 [数学审查](../theorem_audit.md) 与 [增量审查](../novelty_audit.md)，相关充分上界被定位为旧稿推论；本轮不重新立项 |

以上为 **FACT**；题录、版本与哈希见 06 JSON。没有根据附件中的二手摘要直接认领对方定理。

## 3. 当前定理的数学对象

**FACT。** [paper.tex](../../papers/latex_ecust_20261102/paper.tex) 引入 [theory.tex](../../papers/latex_ecust_20261102/ecust_typeset/theory.tex)。实际模型为固定有限维 n、有限目标 k：
\[
x_{t+1}=Ax_t+w_t,\qquad y_t=x_t+v_t,
\]
A 可逆，P0、R、Z 正定，Q 半正定；原始噪声及触发随机数独立。没有自然丢包、时延或估计驱动物理控制。

传感器获得可信的接收端实际预测 m_t^-，依据
\[
\gamma_t=0\iff U_t\le \exp[-(y_t-m_t^-)^\top Z(y_t-m_t^-)/2]
\]
决定是否发送。事件与反馈不可伪造，但实际预测可含过去载荷攻击的影响。攻击只能在发送后修改 y_t，逐路径满足 ||a_t||≤b，不能读未发送测量、隐藏状态、未来噪声或 U_t。

分析信息 \(\mathcal G_t^+=\sigma(S,\gamma_{0:t},Y^{true}_{0:t})\) 包含真实已发送数据及独立攻击种子；这是分析条件化，不是授予防御者的观测。损伤为
\[
J_k=\mathbb E_\pi\|x_k-m_k^+\|^2-\mathbb E_0\|x_k-m_k^+\|^2.
\]
记录为 H_{k+1}、γ_{0:k+1}、(P_k^+,γ_{k+1})，其中 P 是精确未量化名义协方差。主定理 thm:main 的范围是固定模型、n、k、b_ref，所有 0<b≤b_ref、0≤ε≤1：
\[
c\min(b^2,\varepsilon)\le V_j(b,\varepsilon)\le C\min(b^2,\varepsilon).
\]
常数可依赖前述固定量，不是无限时域或任意维数的统一常数。

## 4. 被排重的完整链条

**FACT。** eq:decomposition 与 eq:witness 给出
\[
J_k=\mathbb E_\pi\|D_k\|^2+\mathbb E_\pi\operatorname{tr}P_k^+
-\mathbb E_0\operatorname{tr}P_k^+,
\]
\[
\mathbb E_\pi[Y\mid\mathcal G_k^+]=s(P)e^{-D_k^\top H(P)D_k},
\quad Y=1_{\{\gamma_{k+1}=0\}},\quad w(P)=s(P)^{-1}.
\]
上界还需峰值导致的统一偏差界、H 正定及 TV 对偶；下界需共享随机符号的两拍动作及[原子/连续联合核](../../papers/latex_ecust_20261102/ecust_typeset/main_joint_kernel.tex)。[删减命题](../../papers/latex_ecust_20261102/record_design.tex)针对 H_k 和仅 γ_{k+1}，不证明全体记录设计中的最小性。

**DERIVED。** 比较必须保持触发中心、信息集、策略域、记录 σ-代数、概率约束、损伤目标及时间量词。相同的“历史”“协方差”“隐蔽”“TV/KL”术语不足以建立定理包含关系。

## 5. 证据边界

**FACT。** FULLTEXT 表示取得完整文件且核读被引用的模型、定理及相关证明，不表示本轮独立验算整篇所有公式。未得正文的来源仅作 METADATA/ABSTRACT，定理关系为 OPEN。原 PDF、抽取全文、渲染图均留在仓库外。

**OPEN。** 本轮不是本稿的完整独立数学验收，不自动扩大到部分观测或开发检测器。四个优先问题、剩余缺口及路线建议见 05 报告。
