# 09 缺失全文请求

更新：2026-11-14。本轮核查Zotero存储、项目、附件及常用下载目录。已有Ye、Wang、Peng、Yang/Wen/Zhou及本轮补齐的Mo–Murray、Moradi不要重复下载。下面保留早期清单编号，并明确标记已解决项。

**访问纠正：** 进一步检索旧归档发现，Si TIFS/TAES、Liang等曾经下载，旧路径位于当前不存在的E盘或 `C:\Users\26626\Zotero\storage\`。因此优先请求迁移已有PDF，而非重复下载。历史路径不等于当前已取得全文；详情见14号报告和 `sources/legacy_attachment_locations_20261114.json`。

## 当前最优先：只新增这一项直接全文请求

**Si, Kang; Li, Peng; Yuan, Zhi-Peng. “Secure and Privacy-Preserving Distributed Kalman Filtering for Sensor Networks With Event-Triggered Mechanism.” IEEE Transactions on Information Forensics and Security 20 (2025), 7438–7453. DOI: 10.1109/TIFS.2025.3588670.**

- 出版社入口：https://ieeexplore.ieee.org/document/11079751/ 。DOI：https://doi.org/10.1109/TIFS.2025.3588670 。
- 出版社Crossref元数据已核验，登记见 `sources/si2025_tifs_metadata.json`；尚未取得全文，不作算法或定理结论。
- 这是与“事件通信+隐私DKF+安全”最直接的待核查工作，与下列Si TAES 2025不是同一篇。
- 重点核查：通信保持/缓存规则、隐私扰动时间相关、攻击权限、合法接收端掌握的参数、MSE/隐私定理。不再扩展到其他标题相似论文。
- 已找到旧附件记录：`C:\Users\26626\Zotero\storage\MPQQ5ICG\` 下该论文PDF，当前目录不存在。请优先迁移这一份。

## 优先级 1：隐私保护基础直接竞争

1. **Mo and Murray, “Privacy Preserving Average Consensus,” IEEE Transactions on Automatic Control 62 (2017) 753–765. DOI: 10.1109/TAC.2016.2564339.**
   - **已解决，不需下载。** 取得作者公开34页稿并完成11号精读。来源：https://yilinmo.github.io/public/papers/tac2014privacy.pdf 。本地 `literature_review/distributed_security_privacy_20261114/mo_murray2017_author.pdf`。
2. **Si, Li, Yuan, Jiang & Wei, “Privacy-Preserving Distributed Kalman Filtering Based on State Decomposition and Dynamic Mask,” IEEE Transactions on Aerospace and Electronic Systems 61 (2025) 5839–5852. DOI: 10.1109/TAES.2024.3524215.**
   - 需要核对：状态分解、mask 是否跨时间复用、接收端是否知道 mask、MSE/隐私保证。
   - 下载入口：https://doi.org/10.1109/TAES.2024.3524215 。
3. **Liang, Lam & Lin, “Secure Estimation With Privacy Protection,” IEEE Transactions on Cybernetics 53 (2023) 4947–4961. DOI: 10.1109/TCYB.2022.3151234.**
   - 下载入口：https://doi.org/10.1109/TCYB.2022.3151234 。
4. **Yu, Yang, Ding, Yang & Wang, “Dual-Protection Method Against Eavesdroppers for Distributed State Estimation,” IEEE Transactions on Signal and Information Processing over Networks 11 (2025) 427–438. DOI: 10.1109/TSIPN.2025.3563774.**
   - 需要核对其双层保护究竟是加密/掩码/通信调度，及是否处理攻击与隐私共存。
   - 下载入口：https://doi.org/10.1109/TSIPN.2025.3563774 。

5. **Moradi, Venkategowda, Talebi & Werner, “Privacy-Preserving Distributed Kalman Filtering,” IEEE Transactions on Signal Processing 70 (2022) 3074–3089. DOI: 10.1109/TSP.2022.3182590.**
   - **已解决，不需下载。** 开放存档：https://hdl.handle.net/11250/3039905；已取得16页AcceptedVersion并完成11号精读。本地 `literature_review/distributed_security_privacy_20261114/moradi2022_accepted.pdf`。
   - 历史访问问题已定位：不带明确JSON Accept头时返回NVA登记网页；按公开前端的 `filelink` 路由取得OpenFile，无需登录。完整来源及SHA256见 `sources/moradi2022_access.json`。保留此记录避免以后误报缺失。

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

请优先提供新增Si TIFS 2025全文，其次是第2项Si TAES 2025、第3项Liang TCyb 2023。其余保留为原清单，不要求一次全部下载。第8、9项已在Zotero，属于待读而非缺失，也不因此重启已结项恢复研究。

Si TAES与Liang旧原件目录为 `E:\硕士毕业论文\mypaper\reference paper\`，文件名分别是 `Privacy-Preserving_Distributed_Kalman_Filtering_Based_on_State_Decomposition_and_Dynamic_Mask.pdf`、`Secure_Estimation_With_Privacy_Protection.pdf`。若仍可访问旧电脑/磁盘，复制已有文件即可。

若已下载，告知Zotero条目/附件路径即可；否则通过已登录Edge下载到Zotero或被Git忽略的 `literature_review/distributed_security_privacy_20261114/`。不会将出版社全文随报告推送GitHub。
