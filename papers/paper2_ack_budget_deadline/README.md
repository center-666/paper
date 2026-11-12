# 有限攻击预算下的 ACK 安全发送延后

## 状态

这是 `2026-11-09` 的 14 页匿名大修讨论稿快照，源自原工作区 `fusion_network_20261104/ack_major_revision_20261109/`。它不是已投稿版本。核心安全等待边界保留；相近误差基准没有支持通信资源优势，所以本文不声称更优的通信—精度折中。公开研究摘要见 [`research/RESEARCH_SUMMARY.md`](research/RESEARCH_SUMMARY.md)，项目级状态见 [`../../research/current_status.md`](../../research/current_status.md)。

## 文件

- `manuscript/paper.tex`：语义源稿。
- `manuscript/paper_typeset.tex`：排版源稿。
- `manuscript/output/paper_major_revision.pdf`：该版本阅读稿。
- `manuscript/references.tex`、表格和图：稿件依赖。
- [`research/RESEARCH_SUMMARY.md`](research/RESEARCH_SUMMARY.md)：冻结理论和强基准结论的公开摘要。
- [项目研究索引](../../research/README.md)：全仓研究和文献入口。

## 本地编译

源稿使用 XeLaTeX 和 ctex，原工作环境依赖本机字体/TeX 安装。可在此目录创建 `output/` 后运行：

```powershell
xelatex -interaction=nonstopmode -halt-on-error -output-directory=output -jobname=paper_major_revision paper_typeset.tex
xelatex -interaction=nonstopmode -halt-on-error -output-directory=output -jobname=paper_major_revision paper_typeset.tex
```

此快照不包含 50 组逐轨迹实验和环境依赖；复现限制与准确比较口径见 `research/`。作者身份、单位、通讯作者和基金信息在原研究中尚待确认，稿件保持匿名。
