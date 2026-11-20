# 可信事件记录下的估计损伤界：内容冻结稿

本次投稿准备的唯一活动 PDF 为 [paper.pdf](paper.pdf)。精确反馈双预算界保留主定理，标量量化零 TV 损伤地板保留正文扩展；E0/E1 使用原保存证据。部分观测与窗口研究独立归档。

- [主文件](paper.tex)、[作者字段入口](metadata.tex)、[英文摘要](english_abstract.tex)、[参考文献](references.tex)
- [正文及附录源文件](sections/)、[可逆排版源文件](typeset/)
- [构建记录](build_validation.json)、[字体一致性核验](typography_validation.json)
- [终审报告索引](../../reviews/paper1_submission_final_audit_20261120/README.md)
- [冻结文件清单](release_manifest.json)

使用 XeLaTeX、ctex、Windows 中文字体和 Python 运行 build.py，可编译当前稿。构建需要读取仓库内已保存的 E1 验收状态，因此应从完整仓库使用，不能只复制论文目录。

脚本不运行实验。需要重绘图时，render_evidence.py 只读取固定 E1 汇总和既有区间，不重新生成轨迹或 bootstrap。

内容与版式已终校；作者、单位、通讯邮箱、基金与分类号按用户要求未填。本文未实际投稿，行政信息补齐前不能称为完整上传包。旧版本不覆盖；再次修改或编译后须重新核验并更新冻结哈希。
