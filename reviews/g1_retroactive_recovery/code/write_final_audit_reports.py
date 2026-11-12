"""Update current reports from validated P0 artifacts; never overwrite run outputs."""
from pathlib import Path
import json
import hashlib

B=Path(__file__).resolve().parents[1]
RUN="g1r_p0_verified_20261113_v1"
P=B/"results"/RUN
assert json.loads((P/"acceptance.json").read_text(encoding="utf-8"))["status"]=="PASS"

def write(name,text):
    (B/name).write_text(text.strip()+"\n",encoding="utf-8")

write("07_full_horizon_propagation_audit.md",r"""
# P0-1：全时域独立传播验收

2026-11-13；审查基准db7dabd8cbb9b425482bc9693b065fd25865d720。
最终证据：[配置](results/g1r_p0_verified_20261113_v1/config.json)、
[机器验收](results/g1r_p0_verified_20261113_v1/acceptance.json)、
[源码哈希](results/g1r_p0_verified_20261113_v1/source_hashes.json)。

**EXPERIMENTAL：固定外生日程的全时域验收通过。**
48个原测试seed 9900000–9900047，两种攻击；r=200、q=208、T=280。
预测器从初始化零差递推，唯一事件在r，逐分量比较范围为更新201–280。
容差1e-10在本Run生成前写入配置。它是工程回归阈值，**不是推导出的舍入误差上界**；
此前中间结果已见过，这次重跑不属于盲预注册或新的独立性能确认。

## 预测器与参考严格分离

纯函数difference(model,schedule,delta,event_edge)没有x、y、clean、attacked、日志或未来差分输入。
后续发送只用预测器自己的sender估计差刷新缓存；静默保持缓存。
时钟从t=0按公共日程递推，因此r之前各边的接收年龄正确。
每拍缓存按A^age外推，所有入边一致性项与本地反馈共同更新节点估计差。

FDI注入[1.2,-0.8]；Replay只用sender0实际发过的t=136包替换t=200包。
事件前两条轨迹相同。攻击量只作为差分系统输入，不是部署检测器知道的量。
完整仿真和缓存回调仅在纯函数运行结束后作离线参考。

r收到age=0包后同轮加入epsilon A delta-m，首次变化在估计状态r+1。
q的新发送未经再次篡改，但可能携带网络反馈污染；缓存反事实差不自动归零。

## 覆盖和误差

| 全部48seed最大绝对误差 | FDI | Replay |
|---|---:|---:|
| 节点状态分量 | 2.019e-13 | 2.305e-13 |
| 原始缓存分量 | 2.019e-13 | 1.975e-13 |
| A^age对齐缓存分量 | 2.024e-13 | 2.051e-13 |
| q前状态 | 7.844e-14 | 7.105e-14 |
| q及之后状态 | 2.019e-13 | 2.305e-13 |

network_components.csv保存76,800条节点—时间—分量行；
cache_components.csv保存153,600条边—时间—分量行，含raw/aligned预测与参考、误差、接收时刻、年龄；
sender_transmissions.csv保存全部实际sender0发送的预测污染、参考及误差。
q替换前后分别由迭代207/208/209记录覆盖。

两个单位攻击方向另与完整仿真比较响应矩阵，状态最大误差<1.886e-13、缓存响应<1.642e-13。
这一检查发现并修复本轮中间版本S A^T误写A S的错误。

## 撤回

mapping_01/02是循环公式检查；_03回灌仿真sender差；_04虽然自行预测但仅range(R,q)，
**不能验证q后**。之后sender差的旧仿真直接观察可以保留，但不能说旧独立递推也验证了它。
_05导出中止；_06错误CSV；_07/08为全时域中间结果。最终统一入口改为20261113_v1。
旧JSON伪CSV原件保留，新格式迁移另存目录。所有旧Run不可计为新增独立样本。

通过范围限公共外生日程、固定名义增益、线性更新；
未验证闭环Send-on-Delta模式分叉、非线性保护器或未知攻击归责。
""")

write("08_information_permission_audit.md",r"""
# P0-2：接收端权限及修正收益

2026-11-13。最终Run：[g1r_p0_verified_20261113_v1](results/g1r_p0_verified_20261113_v1)。
**权限修复通过；性能只作探索，不是Deghat复现。**

## 撤回与修复

旧output_channels_02直接读取run.estimates[sender,t]，包括未通信时刻。
其augmented组改标额外内部状态信息对照，不能作为同权限基线。
_01未实际启用分歧分支。两者原结果保留。
本轮中间output_channels_04–07已修复缓存来源，但响应矩阵误用S A^T，
因此其修正MSE无效；旧p0_final_audit_02–05漏检该错误，PASS结论撤回。
最终Run先验证两个单位响应与完整仿真一致，再计算MSE。

合法特征函数只接受(local_y,own,received_aligned,H)。
innovation为y_i-H_i hat_x_i；缓存分歧为sum_j(aligned_received_ji-hat_x_i)。
回调直接读取实际收到的缓存预测，不用原始未篡改包重建特征，
不传攻击标签、source time、攻击量、true state或sender内部estimate。
callback返回全1，正常估计与vanilla Yang完全一致。
全48seed检查静默时raw缓存保持、aligned按A预测；未来d之后输入置NaN不影响d之前特征。
全网公开模型/固定日程以及已知候选边、时刻仅用于离线计算事件响应，仍是较强模型知识。

## 同窗口A/B比较

沿用64训练、48校准、48测试seed，ridge=.02，正常校准95%分位数，测试不调参。
A为本地innovation；B增加合法缓存分歧。状态恢复窗217–260。
MSE为每拍状态误差平方范数和（**没有除以状态维数2**），网络再对5节点平均。

| Replay下方法 | 正常误修正率 | 报警率 | receiver excess | network excess |
|---|---:|---:|---:|---:|
| 200–216 A | 4.17% | 93.75% | -0.003048 | -0.001216 |
| 200–216 B | 6.25% | 100% | 0.000074 | 0.000051 |
| 209–216 A | 2.08% | 81.25% | 0.009752 | 0.002766 |
| 209–216 B | 0% | 97.92% | 0.000875 | -0.000462 |

全窗B-A接收MSE差+0.003123，95%配对区间[-0.002718,0.008963]；
后窗B-A差-0.008877，区间[-0.017907,0.000154]；均跨零。
全窗FDI的A/B报警率18.75%/100%，receiver excess为-0.001675/+0.000074，
说明高检出不自动等于低MSE。
正常误修正MSE变化分别为-0.000048、-0.000128、+0.000778、0；
前三者描述区间跨零，不是无误修正损失保证。
负excess可能来自交叉项和抽样波动，健康Yang不是MSE最优下界。

FPR未匹配、窗口信息数不同、测试seed被重复研究，不能作公平算法排名。
区间按48seed配对、条件于拟合协方差、未多重校正。报警仅为预设d对预设事件评分，
不是未知事件在线检测率。

## 修正方式与成本

本次是因果可计算的影子输出扣除：受攻网络继续运行，d时估计的影响从后续显示输出扣除。
没有回写节点/缓存，没有广播协议；receiver可以本地形成影子输出，
全网影子输出仅离线评价，不能声称全网已部署恢复。

特征复用原消息：新增检测消息0字节；每seed179次广播、358条边消息、5728载荷字节。
full A/B历史272/544字节，post A/B为128/256字节；
拟合数组约10608/39712/2688/9472字节（不含Python和公共响应表）。
48seed估计/影子输出批计算约0.26–0.35毫秒，不含拟合、数据采集、路由，
不是在线单节点延迟。稠密Cholesky白化仍需历史数据，
不能把信息矩阵+得分48B当作整个算法常数内存。
全网协同修正的额外通信未实现，不能给出0成本的部署主张。
""")

print("Wrote 07/08 from final verified run.")
