# MVP 验证记录

验证日期：2026-10-28（PaperSprint 发布准备）。环境：Windows / PowerShell，Python 3.12.14。运行时仅使用 Python 标准库，没有安装依赖、访问 GPU 或执行真实训练。

## 单元与 CLI 测试

在仓库根目录执行：

```bash
python -m unittest discover -s tests -q
```

最终结果：**54 tests，11.796 秒，OK，exit 0**。测试通过子进程实际调用 CLI；坏输入断言要求 exit 2，不把 traceback 或任意非零退出视为通过。

覆盖初始化及报告输出防覆盖、两／三机制的 4／8 组全因子消融、来源／许可／近邻检查、冻结预算含最终测试与历史 pilot 成本、seed 和非有限数校验、数据划分交叠、协议漂移、配置与日志 SHA256、路径越界、重复登记、选型前测试拒绝、选型后开发集锁定、失败重试及超预算已发生成本保留、基线复现容差、论断证据链接和 synthetic 隔离。

`tests/fixtures.py` 的文献、数据和数值是虚构的软件测试夹具。为覆盖非 synthetic 代码分支，部分夹具显式以真实模式运行；这不意味着做过真实研究。测试不产出可用于投稿的数据。

测试使用仓库内 .test-tmp/ 隔离临时文件，不写入真实研究项目。

## 端到端演示

以下命令均已实际执行并成功；`demo` 目标必须是新目录：

```bash
python -m paper_composer demo examples/synthetic --modules 2
python -m paper_composer validate examples/synthetic --ready
python -m paper_composer demo .test-tmp/e2e-three --modules 3
```

| 模式 | 开发集消融组数 | 开发记录 | 最终测试记录 | 负结果 | 报告状态 |
| --- | ---: | ---: | ---: | ---: | --- |
| 两机制 | 4 | 12 | 6 | 3 | SYNTHETIC_DEMO |
| 三机制 | 8 | 24 | 6 | 3 | SYNTHETIC_DEMO |

两次报告均为 `evidence_ready=false`、`paper_ready=false`，GPU 小时为 0。数值由本地演示函数生成，没有训练、检索或论文复现。交付内保留两机制示例及原始 synthetic 记录；三机制运行位于忽略的测试目录，不随源码包交付。

## 技能验证与独立试用

```bash
python scripts/validate_skills.py
```

结果：**4 skills，frontmatter、名称和本地链接全部通过**。此脚本只校验本仓库简单的技能格式，不是通用 YAML 校验器，也不证明科研判断正确。

尝试执行可用 skill-creator 的原版 `quick_validate.py`，因当前运行时没有 PyYAML（`ModuleNotFoundError: yaml`）未能成功；没有为此安装第三方依赖。不能把替代检查描述为原版校验通过。

另由独立代理只读技能，使用“普通 JCR Q2、两篇摘要、单 seed 开发集 91.2 对 91.6、8 GPU 小时”的情景演练，未读取实现或单元测试、未联网、未训练。产出了待补机制卡、预算计划和待填稿，未因为增量小自动否决，也未把开发差值写成最终结论。试用发现并已修正两点：全文暂缺保留条件候选；冻结前 pilot 用独立台账并计入 prior 成本，不补造正式协议 hash。

## 验证边界

以上检查证明本地工作流和登记规则在覆盖场景下可运行。它们不证明文献真实性、许可证解读、训练过程真实、统计充分或论文符合某期刊要求。CLI 核对登记材料，不能阻止外部训练代码偷看测试集，也不提供不可篡改的第三方审计。

当前没有真实论文复现或真实实验结果。接入真实项目按 [real-project.md](real-project.md) 执行，最终由人核对原文、训练产物、统计与论断范围。
