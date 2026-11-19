# G0/G1阶段裁决与停止边界

## G1：PASS（限单次标量符号泄漏命题）

对Z~N(0,sigma²)、S=1{Z>0}、Gamma_b=1{|Z+b|>tau}，在0<b<tau下，攻击前I(S;Gamma_0)=0，攻击后I(S;Gamma_b)>0。sigma=1、tau=1、b=0.3时为0.0695319533 bits。条件概率、互信息和严格正值证明见01号报告；结果由确定性脚本复算，无Monte Carlo。

该结论仅是阈值事件对二元符号的泄漏。它不代表trigger对Z幅值没有正常泄漏，也不代表网络信息泄漏率；完整目标必须是给定同一合法历史、攻击者信息集与攻击机会后，比较Delta I=I(S;Gamma|H,a)-I(S;Gamma|H,0)。

## G0：附件指定三篇已完成有限排重；候选新颖性仍OPEN

- Mason已经明确覆盖状态相关调度导致的timing side-channel，且提供HMM熵泄漏度量和调度防御。
- Crimson的active eavesdropping是改变合法接收率的jamming/dropout与隐私编码，不是直接FDI，但remote估计下主动窃听和估计性能博弈已存在。
- Si已经组合event-triggered DKF、privacy mask、活跃窃听与tamper detection；它以签名阻断篡改包，未给本候选的一拍入站注入诱导下一trigger互信息式。

因果映射是潜在不同的研究对象，但仅凭这三篇未发现完全同式，不能宣称novel。G0不是全领域查新；已有仓库还列有event-triggered privacy、conditional event information、trigger attack等未在本轮逐篇全文审核的邻近工作。

## local-reference触发：可证性质及代价

若参考递推只用可信本地量测、公开固定参数与相同初值，且物理状态不由估计器输出反馈，则纯入站链路攻击没有进入参考递推。与健康轨迹耦合，可逐时归纳bar_x_i^a=bar_x_i^0，因此由它决定的下一发送事件轨迹相同。这消除攻击通过入站融合直接造成的额外trigger变化。

此性质不消除正常本地trigger本身对私有信息的泄漏，也不保证同一发送率、MSE或其它网络下游事件相同。需要按clean发送率校准门槛，并衡量攻击下的MSE/泄漏权衡；本轮不跑这项实验。

## 本阶段是否准入G2

标量可行机制通过，但G0只完成三篇指定文献的有限审查，且攻击机会、窃听观察、trigger公开性、初始锚点及episode信息度量仍未冻结。建议本次交付定位为**G0/G1预审通过机制、论文新颖性未决**；不把附件已列出的G2五节点小实验自动包含在本轮。负责人可在审核后单独授权G2，冻结一拍决策时序、真实SoD事件可观测性、有限/连续攻击约束、增量互信息估计和local-trigger同发送率基准。

## 权限记录

未生成新正式随机轨迹，未运行五节点攻击实验、未修改engine.py/model.py/config.json，未改旧结果或论文。只新增本目录的审查报告、来源清单和确定性标量核验代码。等待研究负责人审核。
