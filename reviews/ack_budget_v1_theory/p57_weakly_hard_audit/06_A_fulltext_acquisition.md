# P5.7：文献 A 全文补齐记录

日期：2026-11-18。基线：de807527af90f2040e9402fafedc6287dbababa1。

## 1. 文件身份与来源

**FACT。** 已取得 Guillem Bernat、Alan Burns、Albert Llamosí 的 Weakly Hard Real-Time Systems，IEEE Transactions on Computers，50(4)，2001 年 4 月，308–321 页。首页作者、期刊卷期及印刷页 308、末页 321 已目视核对；共 14 页，各页均可渲染。题录 DOI 为 10.1109/12.919277，与 York/White Rose 机构记录对应。

- 实际下载 PDF：https://people.cs.pitt.edu/~melhem/courses/3530/papers/bernat.pdf
- 镜像所属课程页：https://people.cs.pitt.edu/~melhem/courses/3530/list.html
- 机构题录：https://eprints.whiterose.ac.uk/id/eprint/6199/
- DOI：https://doi.org/10.1109/12.919277
- 本地文件：C:/Users/zhongxin/Downloads/ACK_P57_literature/Bernat_Burns_Llamosi_2001_Weakly_Hard_Real_Time_Systems.pdf
- 文件大小：229696 字节。
- SHA256：3efffcb44c2366b987608786cc55e068cf4bc2cf6d8dfb382e4d4dae793667b2。
- 获取时间：2026-11-18T18:51:06.785608+08:00。

**FACT。** 第一次 Python urllib 获取遇到证书链验证错误，没有保存成品。随后 Windows curl 在正常证书校验下返回 HTTP 200、application/pdf；没有使用关闭 TLS 校验的选项。此记录不表示原 GMU 候选链接在所有环境中均失效。

## 2. 版本与审读范围

**FACT。** 取得的是具有正式期刊页眉、卷期、版权标记和完整印刷页序的刊版镜像。PDF 内部文字编码异常，直接文本提取出现大量控制字符；因此本阶段逐页查看 14 页渲染图，尤其核对 314–320 页的定义、公式和定理，而没有根据失真的文本检索作否定判断。

**FACT。** A 的状态现为 FULLTEXT：完整文件已取得并已阅读相关原文；其公式级审查见 [07_A_fulltext_equivalence_audit.md](07_A_fulltext_equivalence_audit.md)。FULLTEXT 是证据获取及审读等级，不是创新性结论。

**FACT。** A–E 五篇的 PDF 现均已取得。B–E 的文件路径、页数和哈希仍见 [05_received_pdf_manifest.json](05_received_pdf_manifest.json)；该文件保留其生成时 A 尚未定位的历史记录，由本补录更新当前状态。本轮没有改写前期清单，没有把第三方 PDF 或渲染图加入 Git，也没有自动向 Zotero 数据库导入新条目。

## 3. 阶段权限

**FACT。** 用户随后明确授权“文献找齐了就开始审阅”。本轮进入 A 文献审查，并按此前逐阶段停止要求在 A 阶段结束后等待审核；不自动完成 B–E，不修改旧稿，不开展实验、不提交或推送。其余文献的理论覆盖结论仍为 OPEN。
