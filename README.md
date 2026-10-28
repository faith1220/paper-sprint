# PaperSprint · 论文快跑

*A lightweight workflow from paper mechanisms to experiments and manuscripts.*

从论文技术组合到实验验证与论文成稿的轻量科研工作流。

把同领域 2～3 篇论文中的主要技术，组成一个来源清楚、验证可负担、叙事有证据的方法。

默认 `journal-practical` 模式，面向普通一区／二区期刊的务实研究：**一个强基线 + 两项互补机制**，最多三项新增机制。已知技术组合、轻量适配和应用验证都可以成为研究起点，不要求 TPAMI／Nature 级的创新幅度。组合是否有效由实验回答；分区体系由项目配置，录用由期刊决定。

这是一个可运行的本地 MVP：Python 标准库 CLI、研究模板和 Codex／Claude Code 可直接读取的技能。它负责结构校验、协议冻结、消融矩阵、实验登记、预算累计和证据就绪报告。论文检索、全文阅读、模型实现和训练需要人或 agent 接入实际工具；没有隐藏的自动论文 API。

## 五分钟运行演示

需要 Python 3.10 或更新版本。进入仓库根目录，不需要 `pip install`、API key 或 GPU。

```bash
python -m paper_composer --help
python -m paper_composer demo demo-run
python -m paper_composer validate demo-run --ready
python -m paper_composer ablations demo-run
python -m paper_composer report demo-run --output demo-report.json
python -m unittest discover -s tests -v
```

`demo-run` 应是尚不存在的新目录。演示生成明确标记为 **synthetic** 的论文、数据、配置和数值，用来走通协议与登记流程；报告不会把它判为真实论文证据。它没有训练模型，也没有复现任何论文。仓库内还附有已经运行的 [synthetic 示例](examples/synthetic/)：18 条记录，其中 12 条开发、6 条测试、3 条负结果。三项机制的八组矩阵可用以下新项目查看：

```bash
python -m paper_composer init three-module-plan --name three-module-plan --modules 3
python -m paper_composer ablations three-module-plan
```

## 开始真实项目

```bash
python -m paper_composer init my-study --name my-study --modules 2
python -m paper_composer validate my-study
```

初始化只创建待填文件。默认结构校验通过不代表研究计划完整；按照 [真实项目接入](docs/real-project.md) 填入材料后，用严格校验检查能否冻结：

```bash
python -m paper_composer validate my-study --ready
python -m paper_composer freeze my-study
```

之后用你自己的训练脚本先跑基线，再跑开发集消融。每次运行把真实结果写成登记 JSON，连同原始日志和配置保存到项目内：

```bash
python -m paper_composer record my-study --file result.json
python -m paper_composer select my-study --arm m1+m2 --reason "按预定开发集规则选择"
python -m paper_composer record my-study --file final-test-result.json
python -m paper_composer report my-study --output my-study-report.json
```

这里的 `result.json` 和 `final-test-result.json` 由实际运行生成，格式见 [结果接入说明](docs/real-project.md#结果登记格式)。`select` 要求开发集消融和基线检查满足协议；它固定选择并解锁基线与已选方案的最终测试。不能只复制以上命令跳过缺少的实验。

## 如何用 agent 协作

Codex 从 [AGENTS.md](AGENTS.md) 开始；Claude Code 从 [CLAUDE.md](CLAUDE.md) 开始。两者都按 [program.md](program.md) 的阶段推进，只读取当前需要的模块。技能存放在 `.agents/skills/`，直接读取即可，不需要全局安装。

可以给 agent 这样的任务：

> 阅读 AGENTS.md。我的方向是工业缺陷检测，预算为单卡 24 GPU 小时。先基于我提供的论文建立机制卡，最多提出三个组合候选，选一个强基线加两项机制的方案。没有读到的全文和没有运行的结果明确留缺口。

> 按 run-evidence 技能检查 my-study 的协议和预算，生成四组消融。先完成能在本地做的校验，再列出训练脚本需要接入的输入输出。

> 按 write-evidence 技能读 my-study 的报告和台账，组织问题、组合理由、证据和边界。只有计划或 synthetic 示例时，只写待填稿。

## 核心命令

| 命令 | 用途 |
| --- | --- |
| `init PATH --name NAME --modules 2` | 创建不覆盖已有目录的项目骨架；`--modules 3` 启用三项机制 |
| `validate PATH` | 校验结构，并报告冻结前缺口 |
| `validate PATH --ready` | 严格检查冻结所需字段与条件 |
| `ablations PATH` | 输出两项／三项机制的四组／八组全因子矩阵 |
| `freeze PATH` | 校验计划并保存协议 hash |
| `record PATH --file JSON` | 检查协议、运行身份、来源文件和预算，登记真实发生的运行 |
| `select PATH --arm ARM --reason TEXT` | 根据完整开发证据固定选择，解锁预定最终测试 |
| `report PATH [--output FILE]` | 输出 JSON 证据报告；`--output` 仅写入新文件，避免覆盖证据 |
| `demo PATH` | 创建并运行 synthetic 流程演示 |

消融 arm 为 `baseline`、`m1`、`m2`、`m1+m2`；三模块再包含 `m3` 及其组合。所有结果必须绑定协议 hash、配置、seed、split、代码版本、原始日志和实际 GPU 小时。失败与非提升不会被自动删除，已发生的超预算也要登记。

## 项目文件

| 文件 | 作用 |
| --- | --- |
| `brief.json` | 问题、贡献范围、期刊分区体系、硬件、预算、数据和指标 |
| `papers.json` | 机制、原文证据位置、来源和代码许可检查 |
| `candidates.json` | 强基线、模块、组合理由、近邻检索和选定候选 |
| `plan.json` | seed、可比性、基线容差、单次预算、停止和简化条件 |
| `claims.json` | 最终实验主张、来源论文、最终测试运行与适用边界 |
| `protocol.json` | 冻结后的协议身份 |
| `results.jsonl` | 逐次运行的追加台账 |
| `selection.json` | 已固定的开发集选择与测试解锁依据 |
| `artifacts/` | 数据划分清单、配置和原始日志等本地证据 |

可读的研究工作表放在 [templates/](templates/)，可按需复制到项目做阅读和讨论记录；CLI 读取的是上述 JSON，而不是 Markdown 工作表。待填 JSON 样本也放在 [templates/json/](templates/json/)。

## 证据与范围

`PLAN_ONLY` 表示当前只有计划；开发结果与最终测试分开；`SYNTHETIC_DEMO` 永远只是示例。只有符合协议的真实结果和论断映射具备所需材料时才可能出现 `EVIDENCE_READY`。这仍是文件与流程层面的就绪，不能证明实验真实、结论正确或论文可录用。预算触发停止时按报告先处理，不能继续无限尝试。

数据清单的互斥与 hash 可帮助发现划分或协议漂移，但无法检查训练脚本是否偷看测试数据，也不自动从日志提取或核实指标。本地 JSON 和 hash 也不是不可篡改审计。详细边界见 [证据规则](docs/evidence-policy.md)。

参考了 nature-skills、ARIS、autoresearch、AI-Scientist 和 scientific-agent-skills 的工作流思想。身份、stars 快照、许可证与具体取舍见 [参考审查](docs/reference-audit.md)；本仓库代码与技能文本为原创，不复制上游源码或长提示词。验证记录见 [测试记录](docs/testing.md)。

## 名称与兼容性

PaperSprint 是项目名称。Python 模块保留 `paper_composer`，现有 `python -m paper_composer` 命令继续可用；可选安装后的命令名为 `paper-sprint`，并保留 `paper-composer` 别名。这里的“快速”指减少重复整理和实验管理成本，不承诺录用，也不省略真实验证。
