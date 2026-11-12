# 随机触发估计的隐蔽攻击损伤界

这是用户现有华理学报中文稿的精选源码快照，来源版本为 2026-11-03。当前匿名投稿准备稿，尚未记录为已投稿；不在此快照中改变理论结论、作者元数据或投稿状态。

## 论文与源码

- `paper_submission.pdf`：通栏投稿准备稿；`paper.pdf`：双栏阅读稿；`supplement.pdf`：补充证明和数值方法。
- `paper.tex`、`theory.tex`、`record_design.tex`、`numerical.tex` 等为编辑源；`ecust_typeset/` 为排版构建使用的生成 TeX。
- `figures/`、`vector_data/` 和 `record_study/` 保存作者制作图表及小型结果表/参数。
- `final_review/` 与 `review_checks/` 保存所选证明/行文复核摘要。带有本机 Zotero 库定位的审阅笔记未放入公开快照。
- [`../snapshot_manifest.json`](../snapshot_manifest.json) 记录所选文件的来源哈希和快照哈希；原始输入继续在本地工作区。

## 编译

需要 XeLaTeX、ctex、Times New Roman 和 Poppler。先确保 `xelatex`、`pdftotext`、`pdftohtml` 可从 `PATH` 找到；若需要指定 TeX Live，可设置 `TEXLIVE_BIN` 环境变量指向包含这些工具的目录。运行：

```powershell
python assemble_references.py
python prepare_ecust_math.py
python build.py
```

编译会产生 `.aux`、`.log`、`.synctex.gz` 等本地构建文件，这些不进入版本记录。原项目的一致性审计脚本依赖未纳入的旧稿基线，因此该快照适合编译和阅读，不冒称完整独立科学复现包或证明验证器。

作者、单位、通讯作者、基金和中图分类号需由作者据实补充。
