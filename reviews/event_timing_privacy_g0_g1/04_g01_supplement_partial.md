# G0.1：新增近邻文献核对（阶段性，未完成）

基准 63d56b61；未运行轨迹、未修改引擎或论文。FACT 为已核原文或题录；OPEN 为证据不足。NOT DIRECTLY COVERED 不等于 NOVEL。

## Lu、Leong、Quevedo

FACT：正式文献 DOI https://doi.org/10.1002/rnc.4910；已读作者公开稿 https://arxiv.org/pdf/1910.03759 ，PDF SHA256 230ef1dc5360e0a5bf59c5768d2877d3c77a0ea44039435491237cc4c401c6f0。引用页码为该稿页码，不代表正式版排版。

FACT：作者稿第4页式(3)模型设合法接收和窃听接收为独立 Bernoulli；第5页式(4)使用接收后重置或预测协方差的递推，明确依赖调度指令与状态独立的假设。第6页式(6)的发送决策为合法接收端误差协方差 P_{k-1} 是否达到 f^t(Pbar)；同页 Problem 1 最小化长期平均合法估计协方差，约束窃听者平均误差协方差至少为 b。作者稿第13页附近 Theorem 5 给出窃听者协方差稳态分布递推，Theorem 6–7 给出截断与优化条件，参见原稿编号。

DERIVED：其阈值是接收端协方差阈值，而 G0/G1 是目标节点估计值与上次发送值的 SoD 距离阈值；其隐私度量是窃听者估计误差协方差，而候选是一拍事件相对私有符号的条件互信息。已检查的模型和问题定义中未见入站 FDI 改变受害节点下一拍 SoD 的机制。NOT DIRECTLY COVERED 仅针对上述具体对象；不能由此断言创新或完整排除其他定理。

## Le Ny、Hirche

FACT：Crossref 核实题名 Differentially Private Event-Triggered Sampling，DOI https://doi.org/10.1016/j.ifacol.2019.12.172。OpenAlex W2997084165 所载摘要明确说明未采样亦泄露信息，并提及随机阈值和 sparse vector 技术。摘要不构成全文公式核验。

OPEN：尚未取得可核读正文，无法提供其定义、公式、定理页码，也无法判断是否存在对主动触发操纵的严格等价结果。不能标为 NOT COVERED。作者机构页或出版页可供继续取得全文：https://doi.org/10.1016/j.ifacol.2019.12.172 。

## 已有主动攻击近邻

FACT：已有审查 02_fulltext_competitor_audit.md 对 Crimson 等 Automatica 2025 作者稿 §2.2–2.3、式(9)–(11) 区分主动干扰丢包与入站数值注入；对 Mason 2026 作者稿式(5)、(8)–(11) 记录时序观测、后验和信息泄露；对 Si 2025 正式版式(7)–(15) 记录掩码触发与认证。沿用其原文核查，不将既有审查当作完成全部主动操纵文献搜索的证据。

## 阶段状态

G0.1 未完成：Le Ny 全文公式级对照与主动触发操纵的定向补充仍 OPEN；G1 标量证明通过不意味着网络泄漏存在或新颖。没有开展健康轨迹、local-reference 或攻击实验。后续应核全文及指定近邻后再做健康轨迹协议，且分别记录阈值穿越、timeout、二者同时成立和发送并集。
