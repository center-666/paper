# 09 缺失全文请求

更新：2026-11-14。本轮核查Zotero存储、项目、附件及常用下载目录。已有Ye、Wang、Peng、Yang/Wen/Zhou及本轮补齐的Mo–Murray、Moradi不要重复下载。下面保留早期清单编号，并明确标记已解决项。

**访问纠正：** 进一步检索旧归档发现，Si TIFS/TAES、Liang等曾经下载，旧路径位于当前不存在的E盘或 `C:\Users\26626\Zotero\storage\`。因此优先请求迁移已有PDF，而非重复下载。历史路径不等于当前已取得全文；详情见14号报告和 `sources/legacy_attachment_locations_20261114.json`。

**后续已解决：** Si TAES、Liang TCyb及2504000063也已取得并精读正式PDF，不再请求下载。最新版本/DOI见 [资产纠正](../final_candidate_feasibility/01_source_inventory_correction.md)。

## 已解决：Si TIFS 2025，不要重复下载

**Si, Kang; Li, Peng; Yuan, Zhi-Peng. “Secure and Privacy-Preserving Distributed Kalman Filtering for Sensor Networks With Event-Triggered Mechanism.” IEEE Transactions on Information Forensics and Security 20 (2025), 7438–7453. DOI: 10.1109/TIFS.2025.3588670.**

- 出版社入口：https://ieeexplore.ieee.org/document/11079751/ 。DOI：https://doi.org/10.1109/TIFS.2025.3588670 。
- **已解决并完成精读。** 用户新附件位于 `C:\Users\zhongxin\Zotero\storage\FYH5HRBR\`，16页正式版。版本/哈希见 `sources/si2025_tifs_access.json`，方法与定理见15号报告。
- 它与下列Si TAES 2025不是同一篇。已核查事件保持、动态mask、攻击字段、密码资源及MSE/隐私定理；不再请求本篇，也不扩展标题相似论文。
- 原旧附件 `C:\Users\26626\Zotero\storage\MPQQ5ICG\` 不可访问的记录保留，仅作为历史；已由新附件解决，不再要求迁移。

## 优先级 1：隐私保护基础直接竞争

1. **Mo and Murray, “Privacy Preserving Average Consensus,” IEEE Transactions on Automatic Control 62 (2017) 753–765. DOI: 10.1109/TAC.2016.2564339.**
   - **已解决，不需下载。** 取得作者公开34页稿并完成11号精读。来源：https://yilinmo.github.io/public/papers/tac2014privacy.pdf 。本地 `literature_review/distributed_security_privacy_20261114/mo_murray2017_author.pdf`。
2. **Si, Li, Yuan, Jiang & Wei, “Privacy-Preserving Distributed Kalman Filtering Based on State Decomposition and Dynamic Mask,” IEEE Transactions on Aerospace and Electronic Systems 61 (2025) 5839–5852. DOI: 10.1109/TAES.2024.3524215.**
   - 已补齐正式版14页并完成精读，Zotero268YWHMV，不再请求下载。
   - 下载入口：https://doi.org/10.1109/TAES.2024.3524215 。
3. **Liang, Lam & Lin, “Secure Estimation With Privacy Protection,” IEEE Transactions on Cybernetics 53 (2023) 4947–4961. DOI: 10.1109/TCYB.2022.3151234.**
   - 已补齐正式版15页并完成精读，ZoteroV7IZMDNA，归行为隐私，不再请求下载。
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

本轮指定三份PDF均已补齐，不要求新增下载或迁移；唯一候选已完成数学审查，判定NO-GO。其他条目保留旧清单，不因此扩大研究或重启恢复。

Si TAES、Liang及2504000063的旧E盘记录已由新Zotero附件取代，历史记录不删除，不再要求访问旧磁盘。

PDF和完整提取文本只保留在本地忽略目录，不将出版社全文推送GitHub。当前没有新增下载请求。
