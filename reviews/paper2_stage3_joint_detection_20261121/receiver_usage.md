# 接收端原型使用说明

[receiver_detector.py](receiver_detector.py)提供只含联合J1的接收端原型，不依赖仿真器、真实状态、真实攻击幅值或攻击起点。每个接收端创建一个对象；同一对象连续处理所有时刻，静默也必须调用。

初始化参数为公开模型A、R、Z、候选幅值、固定混合权重和误报预算alpha。示意：

    from receiver_detector import JointReceiverDetector
    detector = JointReceiverDetector(A=0.82, R=0.20, Z=2.0)

每拍先固定实际prior mean与variance、反馈center。可信事件和实际载荷到达后、候选估计生产输出提交前调用：

    result = detector.observe(
        sent=sent,
        innovation=received_payload - prior_mean if sent else None,
        prediction_variance=prior_variance,
        center_offset=feedback_center - prior_mean,
    )

静默时创新必须是None，不伪造0载荷。时钟按调用次数从0计数，不能漏掉静默拍；停止再启动或重复处理同一拍会改变已证明协议。输出log_evidence为对数检验证据，first_alarm_time为首次越过log(1/alpha)的物理时间。它不是攻击后验概率，不自动修正状态估计。

候选状态只用事件和公开增益递推，不能传入仿真真实偏差。原型持续消费当前输出，即使首次报警后也可继续更新证据；实际部署应定义何时重启并重新分配误报预算，不能每次重置仍共用原1%全时域声明。

固定输入验证 [receiver_interface_checks.json](receiver_interface_checks.json) 对S1/U1各600拍逐项与冻结实验J1一致，对数证据最大差为0。原型是冻结J1计算的接口化副本，未改变实验方法。

[软件微基准](receiver_benchmark.json)在本机Python环境、其他实验并行运行时，用固定输入分别测5组×2000次更新。中位CPU时间约70–78微秒/拍，中位墙钟时间约76微秒/拍；三候选的四个持久NumPy数值数组共96字节。该数字不含Python对象、临时数组和原估计器内存，也不是硬件实时性或最坏执行时间保证。

需要保留的实施条件：

- 当前原模型量化的是预测反馈，发送载荷仍按连续量建模。若载荷也按有限字长编码，应积分每个bin的概率，不能直接沿用连续密度比。
- 触发参数、协方差递推、反馈中心必须与健康模型一致。现有证明没有覆盖模型失配、饱和、丢包误标或篡改事件位。
- 联合密度有零测零点；实现保留数学正负无穷，对不定0/0显式报错，不用epsilon夹断改核。浮点输入或中心误差的敏感性见 [precision_sensitivity_note.md](precision_sensitivity_note.md)。
- 原型用于检测研究。没有新鲜可信锚点或恢复规则，报警不表示可以安全回滚，也不保证总MSE下降。
