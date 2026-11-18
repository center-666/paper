# P5.5 审阅入口

**当前应先读：[三篇正式全文补读与更新裁定](P5.5_fulltext_supplement_and_decision.md)。**

用户补充的 Guo 2020、Zhao 2024、Badr 2017 正式PDF已取得并按公式核读。旧版三项全文 OPEN 已关闭。**这不等于P5.5整体PASS**：既有DBP对应与一般Gaussian采样行为近邻仍然保留；没有开启论文重构或新阶段。

- [补读来源、版次、页码、SHA256](sources_fulltext_supplement.json)
- [补读报告包SHA清单](supplement_integrity.json)
- [首次审查报告](P5.5_final_novelty_audit.md)：记录取得三篇正文之前的结论，保留不改。
- [首次检索记录](search_evidence.json)：包含命中条目、获取失败与6份已核近邻全文哈希，不把当时失败改写为成功。

只读核验：

```powershell
python -B reviews/ack_budget_v1_theory/p55_final_novelty/verify_supplement.py
```

本地若保留相同Zotero路径，可加 `--local-pdfs` 复核三份PDF哈希。默认核验不依赖第三方PDF，不执行估计器或历史测试。旧资产完整性按Git基准差异核对，允许本次清单内的新文件，禁止既有文件改变。清单文件本身由Git提交固定，不对自身做循环SHA。

当前分支：ack-v1-p5-5-final-novelty-audit。当前补读基于首次P5.5提交57e3f0b1。第三方PDF未上传。
