# 工作流参考与许可证核对

核对日期：2026-10-27。下表星数是 GitHub 当日网页的四舍五入显示值，只用于识别项目，不代表科研质量或本仓库认可其全部主张。PaperSprint 的实现和技能文本是原创；未复制上游源码、长提示词，未运行任何上游安装脚本。

| 参考项目 | 当日 stars | 许可证核对结果 | 本仓库借鉴的思想 |
| --- | ---: | --- | --- |
| [Yuan1z0825/nature-skills](https://github.com/Yuan1z0825/nature-skills) | 51.0k | [Apache-2.0](https://github.com/Yuan1z0825/nature-skills/blob/main/LICENSE) | 机制卡记录方法组件、假设、数据流、证据定位；缺证据保留待填项 |
| [ARIS 上游](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep) | 18.2k | [MIT](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/main/LICENSE) | 先核对真实产物与数值再组织论断；区分流程完成与研究结论 |
| [karpathy/autoresearch](https://github.com/karpathy/autoresearch) | 98.7k | 本次未核实到许可证：根目录未找到 LICENSE / LICENSE.md，pyproject 未声明 | 固定评价协议、先跑基线、预算与 keep / discard / crash 台账 |
| [SakanaAI/AI-Scientist](https://github.com/SakanaAI/AI-Scientist) | 14.8k | [自定义 AI Scientist Source Code License v1.0，December 2025](https://github.com/SakanaAI/AI-Scientist/blob/main/LICENSE)，不是 MIT 或 Apache | 每个候选隔离产物，实验完成后组织写作 |
| [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | 54.8k | [MIT](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/LICENSE) | 检索、筛选与引用核验留痕；区分摘要和全文 |

## 身份澄清

`nature-skill` 名称有歧义。此处选择高星 `Yuan1z0825/nature-skills` 作为设计参考，并不声称已经确认它就是用户最初所指的项目。`lex8777/nature-skill` 当日仅 1 star，不把它的身份或作者与高星项目混用。`wangxp1008/ARIS` 是 fork（当日 0 stars），其 LICENSE 本次读取失败；这里引用已核实的上游。`K-Dense-AI/claude-scientific-skills` 已重定向至 `scientific-agent-skills`。

## 具体参考位置与取舍

- [nature-paper-card](https://github.com/Yuan1z0825/nature-skills/blob/main/skills/nature-paper-card/SKILL.md)：启发机制卡的输入输出、关键假设、公式位置、技术来源与 claim–evidence 关系。只读摘要的卡片不能伪装成全文精读。
- [ARIS result-to-claim](https://github.com/wanshuiyin/Auto-claude-code-research-in-sleep/blob/main/skills/result-to-claim/SKILL.md)：启发本地结果登记与论断引用检查。证据就绪不等于论文可录用。
- [autoresearch program.md](https://github.com/karpathy/autoresearch/blob/master/program.md)：启发冻结评价协议、baseline-first 与失败台账。本仓库使用可配置的总预算；不照搬 5 分钟训练、无限循环、自动回退工作树等执行方式。
- [AI Scientist launch_scientist.py](https://github.com/SakanaAI/AI-Scientist/blob/main/launch_scientist.py)：借鉴候选隔离与实验后写作的顺序，不复用代码或自动投稿行为。
- [K-Dense literature-review](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/literature-review/SKILL.md)：借鉴可追溯的检索与筛选记录，保持轻量，不强制系统综述级筛选。

## 本仓库边界

`journal-practical` 接受已知技术互补、轻量接口适配与应用验证。创新增量小不是自动否决理由。默认先用一个可信基线加两项机制；最多三项机制，来自两到三篇同领域论文。必要检查只服务于技术归属、可复现比较和诚实报告，不要求理论突破、十几个数据集或顶刊叙事。

本仓库的许可证只覆盖本仓库原创内容。下载数据、使用预训练权重或复用研究代码前，仍需分别核对它们的许可证、用途限制和引用要求；“论文可阅读”不等于“代码可任意复制”。无法核实许可证时可以记录待核实和独立实现方案，不伪造授权。

此表是时间点核对记录，不自动追踪 stars、许可证或分支变化。真实项目开始复用材料时应再次检查相应版本。
