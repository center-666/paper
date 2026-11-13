# 09 缺失全文请求

以下材料在当前工作区尚未确认可供逐式阅读。已有 Ye 2025、Wang 2025、Peng 2025、Yang/Wen/Zhou 等 PDF 不要重复下载。

## 优先级 1：隐私保护基础直接竞争

1. **Mo and Murray, “Privacy Preserving Average Consensus,” IEEE Transactions on Automatic Control 62 (2017) 753–765. DOI: 10.1109/TAC.2016.2564339.**
   - 需要核对：动态/随机掩码的生成式、窃听者信息集、共识收敛与隐私定义、是否需要 trusted node 或安全终端。
   - 下载入口：https://doi.org/10.1109/TAC.2016.2564339 。
2. **Si, Li, Yuan, Jiang & Wei, “Privacy-Preserving Distributed Kalman Filtering Based on State Decomposition and Dynamic Mask,” IEEE Transactions on Aerospace and Electronic Systems 61 (2025) 5839–5852. DOI: 10.1109/TAES.2024.3524215.**
   - 需要核对：状态分解、mask 是否跨时间复用、接收端是否知道 mask、MSE/隐私保证。
   - 下载入口：https://doi.org/10.1109/TAES.2024.3524215 。
3. **Liang, Lam & Lin, “Secure Estimation With Privacy Protection,” IEEE Transactions on Cybernetics 53 (2023) 4947–4961. DOI: 10.1109/TCYB.2022.3151234.**
   - 下载入口：https://doi.org/10.1109/TCYB.2022.3151234 。
4. **Yu, Yang, Ding, Yang & Wang, “Dual-Protection Method Against Eavesdroppers for Distributed State Estimation,” IEEE Transactions on Signal and Information Processing over Networks 11 (2025) 427–438. DOI: 10.1109/TSIPN.2025.3563774.**
   - 需要核对其双层保护究竟是加密/掩码/通信调度，及是否处理攻击与隐私共存。
   - 下载入口：https://doi.org/10.1109/TSIPN.2025.3563774 。

5. **Moradi, Venkategowda, Talebi & Werner, “Privacy-Preserving Distributed Kalman Filtering,” IEEE Transactions on Signal Processing 70 (2022) 3074–3089. DOI: 10.1109/TSP.2022.3182590.**
   - 开放存档入口：https://hdl.handle.net/11250/3039905；正式 DOI：https://doi.org/10.1109/TSP.2022.3182590 。需要核对隐私定义、噪声/掩码是否跨时复用、窃听者信息集和估计误差保证。
   - 当前自动访问只到机构存档登记页，未获得可核对的 PDF；不能据此写全文结论。

## 优先级 2：交叉与最新工作

6. **Wan, Yu, Fu & Wen, “Privacy-Preserving Distributed Resilient Event-Triggered Platoon Control Under Hybrid Cyber Attacks,” IEEE Transactions on Systems, Man, and Cybernetics: Systems 56 (2026) 3976–3987. DOI: 10.1109/TSMC.2026.3662411.**
   - 当前只有检索元数据；下载入口：https://doi.org/10.1109/TSMC.2026.3662411 。需要正式全文确认事件触发、隐私噪声、混合攻击和定理对象。
7. **Yan, Zhang, Xu & Chen, “Distributed Confidentiality Fusion Estimation Against Eavesdroppers,” IEEE Transactions on Aerospace and Electronic Systems 58 (2022) 3633–3642. DOI: 10.1109/TAES.2021.3124194.**
   - 这是与分布式融合最接近的窃听竞争文献；下载入口：https://doi.org/10.1109/TAES.2021.3124194 。
8. **Nasiri et al., “A Trust-Aware Consensus Mechanism for Post-Attack Restoration of Power System Distributed State Estimation,” 2026.**
   - 当前 Zotero 有 PDF，但本轮尚未完成公式级精读；若要保留候选 C，请让我按全文核查其恢复状态、认证假设和误恢复保证。
9. **Xu et al., “Secure State Estimation: A Novel Retransmission and Roll-Back Mechanism,” 2026.**
   - 当前 Zotero 有 PDF，但未纳入本轮核心15篇；如要再研究主动恢复，请保留正式 PDF 和 DOI 元数据。

## 用户需要做的事

请优先确认第 1–4 项 PDF 是否已在 Zotero；若已存在，直接告诉我 Zotero 条目或附件路径，我不会重复下载。若没有，请通过已登录 Edge 下载正式 PDF，放入 `reviews/distributed_filtering_security_privacy_literature/sources/` 或 Zotero，并告知文件名。拿到文件后我会逐式补充页码/公式号，不以摘要替代。
