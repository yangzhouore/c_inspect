# 阶段 2：离线评估基准

## 计划与适用性检查
1. 用四个固定案例评估现有模拟 Agent，不改变其研究逻辑。
2. 检查报告内容、工具顺序、停止行为，并保存 JSON 基准。
3. 测试评分器确实能发现错误，再接入现有 GitHub CI。
4. 独立分支提交，运行远程 CI，创建 PR 并保留人工审核。

现有 `research(..., live=False)` 可以复用，无需增加依赖、数据库或子 Agent。
期望值由人工写在案例文件中，不从 Agent 输出自动生成。
研究依据：[OpenAI 评估指南](https://developers.openai.com/api/docs/guides/evaluation-best-practices)。
采用“案例 → 明确评分规则 → 运行 → 分析失败”的本地流程，不调用评估 API。

## 第一步：运行
在项目根目录执行：

```powershell
.\.venv\Scripts\python.exe -m evals.run
```

不需要 API Key；评估期间阻止网络连接和 DNS 查询，禁用上传追踪。
每个案例单独创建研究状态，通过实际 SDK Runner 执行模拟模型和本地工具。
评估命令不提供 live 模式。

## 第二步：阅读案例
打开 `evals/cases.py`，查看输入和人工定义的期望：

| 案例 | 预期行为 |
| --- | --- |
| known_company | 搜索、读取、报告包含各业务的功能、收入方式和模拟来源 |
| normalized_company | 公司名称的空格和大小写不影响结果 |
| unknown_company | 只搜索，说明没有本地资料，不编造已知业务 |
| blank_input | 在调用工具之前以 ValueError 拒绝输入 |

## 第三步：理解评分
打开 `evals/run.py` 的 `grade` 函数。每个案例必须通过全部六项检查：
预期成功/错误、必要文本、禁用文本、工具顺序、回合上限、是否应该生成报告。
失败会显示对应规则，命令返回退出码 1，使 CI 可以阻止回归。
意外异常记为失败并继续其他案例，只保存异常类型，不保存原始错误信息。

## 第四步：保存和比较
仓库中的 `evals/baseline.json` 是本阶段的参考结果。
修改代码后，保存到另一个文件进行比较，避免覆盖参考基准：

```powershell
.\.venv\Scripts\python.exe -m evals.run --output evals/latest.json
git diff --no-index evals/baseline.json evals/latest.json
```

`latest.json` 被 Git 忽略。JSON 包含案例、报告、工具顺序、回合数及 SDK 版本。
预期修改了案例或行为时，人工检查差异后才能有意识地更新基准。
CI 每次运行评分规则，不自动覆盖或更新基准。

## 学到了什么及边界
- 单元测试检查评分器是否正确；评估集检查整个 Agent 流程是否符合预期。
- 模拟模型按预设逻辑行动，所以这个分数衡量离线回归，不代表真实模型能力。
- 文本匹配只能检查列出的内容，不能证明所有结论都有证据。
- 真实模型质量、资料缺失、冲突来源及提示注入评估留待后续阶段。
- 下一阶段可以在这个基准上引入结构化报告，然后比较变化。
