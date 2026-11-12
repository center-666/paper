"""Revise claims from fixed calibration and test evidence; preserve numbered theory."""
from pathlib import Path
import json,re
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
EXP=BASE/'ack_accuracy_matched_20261109'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
r=load(EXP/'results.json');cert=load(EXP/'certificates.json')['certificates']
source=(BASE/'ack_submission_preparation_20261108/paper.tex').read_text(encoding='utf-8')
text=source.replace('匿名投稿准备稿\\quad 2026-11-08','大修讨论稿\\quad 2026-11-09')
text=text.replace('结果表明，该机制可在所考察攻击条件下实现可认证的通信与精度权衡。',
    '共同证书保证均方有界，实测误差代价由数值实验评价。进一步采用独立样本校准普通触发阈值，异相日历下普通触发以略低误差获得更少尝试，当前证据尚不支持所提机制具有更优的通信与精度折中。')
text=text.replace('Sun、Peng和Shen利用历史ACK指标切换触发阈值',
                  'Sun、Peng和Shen利用滑动时间窗口中的历史ACK统计检测攻击并切换触发阈值')
text=text.replace('Historical ACK statistic and threshold switching','Sliding-window ACK statistic and threshold switching')
needle='本文的理论贡献集中于历史占用到安全动作范围的转换。'
start=text.index(needle);end=text.index('\n\n',start)
text=text[:start]+r'''主动抑制发送及记忆事件触发也已有研究。Guo等允许主动舍弃连续时刻报文，并分析Bernoulli DoS下的估计协方差与控制性能\cite{Paper_FUS46_2020}。Zhao等利用历史状态信号、双缓存和动态记忆触发处理非周期DoS下的安全控制\cite{Paper_FUS50_Zhao2024}。因此，历史ACK、窗口记忆和主动少发本身均不作为本文的独立贡献。

本文的主要贡献候选为硬物理滑窗预算下的固定截止安全等待边界。根据未来截止窗仍有效的阻断占用，给出最大可保证初始等待长度，并通过覆盖重叠滑窗的合法攻击延拓证明必要性。Gaussian正概率论证和跨成功记忆增量分别作为模型补充与直接推论。锚点不变量及共同均方有界性支撑通信机制与固定增益估计器的兼容性。实验评价同时包含同阈值消融和独立校准的普通触发基准，通信成本优越性按实际比较结果限定。''' +text[end:]
text=text.replace('This study & Confirmed blocking occupancy',
 r'''Guo et al.\cite{Paper_FUS46_2020} & Active packet dropping over consecutive steps & Bernoulli DoS, estimation covariance and control cost\\
Zhao et al.\cite{Paper_FUS50_Zhao2024} & Transmitted-state memory, dual buffers and dynamic triggering & Aperiodic DoS, stability and $H_\infty$ performance\\
This study & Confirmed blocking occupancy''')
text=text.replace('5\\%为探索阶段预先采用的平均误差变化筛查值，本文逐组同时报告，',
 '5\\%为探索阶段对全部样本、节点和时刻聚合平均误差变化的筛查值，不是每组或每节点的约束，')
text=text.replace('异相日历下，完整记忆的失败数较立即发送增加371次，',
 '贪心攻击下，减少的24652次尝试中，失败减少3780次、成功减少20872次，后者约占84.67\\%。异相日历下，完整记忆的失败数较立即发送增加371次，')
text=text.replace('通信效果由总尝试净差体现。',
 '通信效果由总尝试净差体现。这些结果主要体现成功信息更新频率降低，不能将总省包全部归因为失败重试减少。')

matched=r'''\subsection{独立校准固定阈值的比较}
为检查普通触发参数调整能否替代当前实验中的资源收益，另取主种子2026110901生成20组独立校准样本，每组240拍。完整记忆仍使用$\theta=0.2$。基准保持立即发送，阈值候选集在执行前固定为$\{0.20,0.21,\ldots,0.40\}$。每类攻击分别选择校准平均误差最接近完整记忆的阈值，之后锁定，在原50组测试样本上评价。贪心攻击选择$0.28$，异相日历选择$0.25$。这是按攻击条件分别离线校准的固定参数参考，不需要在线读取攻击状态，也不构成一个统一阈值的部署方案。

校准阶段，贪心下候选和所选基准的平均误差分别为1.335645、1.337834，日历下为1.278336、1.277368。测试集是已有样本的审稿追加比较，未用于本轮阈值选择。事前将测试聚合误差相差0.5\%以内作为描述性的接近标准，并报告全部结果。此标准不替代统计等效性检验或应用精度要求。

\input{matched_table.tex}

异相日历下，普通触发以128367次尝试得到平均误差1.273858，完整记忆为129982次和1.277224。候选比校准基准多发1.258\%，误差高0.264\%，五个节点的聚合误差也均较高。因而该测试条件没有提供预算记忆更优的经验资源折中证据。贪心下，候选比校准基准多发2.440\%，但误差低1.251\%，误差偏差超过事前0.5\%标准，应解释为两个不同的折中点。

\input{matched_nodes.tex}

以独立运行作为统计单位，候选相对校准基准的每组净省包均值，贪心下为$-61.52$次，近似95\%配对$t$区间为$[-80.52,-42.52]$，仅9/50组省包。日历下为$-32.30$次，区间为$[-43.61,-20.99]$，13/50组省包。候选减基准的平均误差差及其区间，分别为$-0.016865$、$[-0.029229,-0.004501]$，以及$0.003366$、$[0.000053,0.006679]$。逐组最大相对误差退化分别为5.581\%和2.466\%，超过5\%的组数为1和0。这些统计量条件于已选择阈值，不涵盖重新选择校准样本的变异，也不是全攻击类结论。

阈值改变后，比较矩阵$M$保持不变，式\eqref{eq:comparison}中的阈值输入随之改变。重新用有理数计算相应全时刻包络，并检查初值包含，结果见表\ref{tab:matchedcert}。调大阈值使该理论上界变大，不能将新基准归入原$\theta=0.2$的同一数值证书。
\input{matched_certificate.tex}

这一对照没有推翻固定截止安全等待定理，也没有证明预算记忆在所有场景均无资源价值。但当前证据未通过相近实际误差下的通信优势检验。本文因此仅主张精确安全动作边界、相应网络有界性及限定基准的数值行为，不主张通信成本最优或普通阈值调整无法替代的精度资源优势。

'''
# Find actual comparison equation label instead of assuming its name.
labels=re.findall(r'\\label\{([^}]+)\}',source)
if 'eq:comparison' not in labels:
    matched=matched.replace(r'式\eqref{eq:comparison}',r'定理\ref{thm:bound}的比较式')
    if 'thm:bound' not in labels:
        matched=matched.replace(r'定理\ref{thm:bound}的比较式','式(20)')
text=text.replace(r'\subsection{后续发送、异质缓存与实现核验}',matched+r'\subsection{后续发送、异质缓存与实现核验}')
text=text.replace('当前证据支持具有公共误差保证的通信与精度权衡。',
 '追加的独立校准基准比较没有支持更优的经验资源折中。异相日历下，普通触发在略低误差下还减少了尝试，贪心下误差匹配未达到预定接近标准。共同理论证书认证均方有界，不能将同阈值下的省包直接扩展为同实际精度优势。')
text=text.replace('These results demonstrate a communication--accuracy trade-off within the stated finite-horizon experiments and the common error certificate.',
 'A further baseline threshold is selected using twenty independent calibration samples for each attack condition. On the existing test samples, the calendar-calibrated immediate sender uses fewer attempts and has a slightly lower empirical error than the proposed mechanism. The greedy comparison does not meet the predefined error-closeness screen. Thus the results support the fixed-deadline safety characterization and mean-square boundedness, but do not establish a superior empirical communication--accuracy trade-off.')
text=text.replace('The deadline-based rule preserves a common mean-square certificate and reduces communication attempts\nin the tested distributed estimation network.',
 'The rule preserves mean-square boundedness. A separately calibrated immediate-sending baseline\nlimits the empirical communication--accuracy advantage claimed for the mechanism.')
text=text.replace('两批验证共600套闭环、2880000个边时刻，',
 '既有两批验证共600套闭环、2880000个边时刻，')
text=text.replace('一般参数的保证由理论证明给出。',
 '新增100套校准基准测试闭环也从日志独立重放，并重新核对已有200套候选及普通基准闭环，目标均为$x_2,\\ldots,x_{241}$。一般参数的保证由理论证明给出。')
text=text.replace('\\section*{图文摘要}\n\\begin{center}\n\\includegraphics[width=\\linewidth]{figures/greedy_results.pdf}', '\\section*{图文摘要}\n\\begin{center}\n\\includegraphics[width=\\linewidth]{figures/matched_tradeoff.pdf}')
(HERE/'paper.tex').write_text(text,encoding='utf-8')

lines=[r'\begin{table}[htbp]\centering\small',
r'\caption{独立校准后在原测试集上的结果\\ Table~\thetable\quad Test results after independent calibration}\label{tab:matched}',
r'\begin{tabular}{llrrrrr}\toprule',
r'Attack & Protocol & $\theta$ & Attempts & Failures & Successes & MSE\\\midrule']
for attack,name in [('greedy','Greedy'),('calendar','Calendar')]:
    for key,protocol,th in [('calibrated_immediate','Calibrated',r[attack]['theta']),('full','Full memory',.2)]:
        v=r[attack][key];lines.append(f"{name} & {protocol} & {th:.2f} & {v['attempts']} & {v['blocks']} & {v['successes']} & {v['mse']:.6f}"+r'\\')
lines.extend([r'\bottomrule\end{tabular}',r'\end{table}'])
(HERE/'matched_table.tex').write_text('\n'.join(lines),encoding='utf-8')
lines=[r'\begin{table}[htbp]\centering\small',
r'\caption{校准比较中的逐节点平均误差\\ Table~\thetable\quad Mean error by node in the calibrated comparison}',
r'\begin{tabular}{llrrrrr}\toprule Attack & Protocol & Node 1 & Node 2 & Node 3 & Node 4 & Node 5\\\midrule']
for attack,name in [('greedy','Greedy'),('calendar','Calendar')]:
    for key,protocol in [('calibrated_immediate','Calibrated'),('full','Full memory')]:
        lines.append(name+' & '+protocol+' & '+' & '.join(f'{v:.6f}' for v in r[attack][key]['node_mse'])+r'\\')
lines.extend([r'\bottomrule\end{tabular}',r'\end{table}'])
(HERE/'matched_nodes.tex').write_text('\n'.join(lines),encoding='utf-8')
lines=[r'\begin{table}[htbp]\centering\small',
r'\caption{各阈值下重新计算的节点均方上界\\ Table~\thetable\quad Recomputed node mean-square bounds}\label{tab:matchedcert}',
r'\begin{tabular}{lrrr}\toprule Threshold & Nodes 1,3,5 & Nodes 2,4 & Node average\\\midrule']
for th,c in cert.items():
    v=c['node_MSE'];lines.append(f"{th} & {v[0]:.3f} & {v[1]:.3f} & {sum(v)/5:.3f}"+r'\\')
lines.extend([r'\bottomrule\end{tabular}',r'\end{table}'])
(HERE/'matched_certificate.tex').write_text('\n'.join(lines),encoding='utf-8')
refs=(BASE/'ack_submission_preparation_20261108/references.tex').read_text(encoding='utf-8')
refs=refs.replace(r'\end{thebibliography}',r'''\bibitem{Paper_FUS46_2020}
GUO L, YU H, HAO F. Event-triggered control for stochastic networked control systems against Denial-of-Service attacks[J]. Information Sciences, 2020, 527, 51--69. \doi{10.1016/j.ins.2020.03.045}.

\bibitem{Paper_FUS50_Zhao2024}
ZHAO M, QIN W, YANG J, et al. Security control for cyber-physical systems under aperiodic denial-of-service attacks: A memory-event-triggered active approach[J]. Neurocomputing, 2024, 600, 128159. \doi{10.1016/j.neucom.2024.128159}.
\end{thebibliography}''')
(HERE/'references.tex').write_text(refs,encoding='utf-8')
pattern=r'\\begin\{equation\}(.*?)\\end\{equation\}'
assert re.findall(pattern,source,re.S)==re.findall(pattern,text,re.S)
oldrefs=set(re.findall(r'\\bibitem\{([^}]+)\}',refs))
assert set(re.findall(r'\\cite\{([^}]+)\}',text))<=oldrefs
assert r'\overline\Phi' in text
print('Revised claims, tables, references. All numbered equations preserved.')
