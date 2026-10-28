# PaperSprint 工作规则

这是面向普通一区／二区期刊的组合型研究工作区。默认模式为 `journal-practical`：允许已知技术互补、轻量适配和应用验证。目标是找到一个可解释、可验证、成本可承受的组合，不以顶刊级范式创新作为立项条件，也不承诺录用。

## 开始工作

先读 [program.md](program.md)，再读当前项目的 brief、机制卡、候选、实验计划与现有结果。已有记录优先于猜测；只加载当前阶段需要的技能。

| 当前任务 | 仓库内技能 |
| --- | --- |
| 读同领域论文，拆出机制和适用条件 | [.agents/skills/paper-card/SKILL.md](.agents/skills/paper-card/SKILL.md) |
| 从 2～3 篇论文形成少量候选并收敛 | [.agents/skills/compose-method/SKILL.md](.agents/skills/compose-method/SKILL.md) |
| 制定预算、冻结协议、跑消融并登记结果 | [.agents/skills/run-evidence/SKILL.md](.agents/skills/run-evidence/SKILL.md) |
| 整理论断、实验支持和论文草稿 | [.agents/skills/write-evidence/SKILL.md](.agents/skills/write-evidence/SKILL.md) |

技能直接在本仓库内读取。没有全局安装、外部发布、推送远程或访问 GPU 服务器的默认授权。

## 研究约束

- 优先一个强基线加两项机制，最多三项新增机制；机制主要来自 2～3 篇可追溯的同领域论文。不要把多个已有模块改名后描述为原创组件。
- 组合理由须指向具体问题、数据流和可证伪假设。增量小可继续；来源不明、接口不通、近邻重复却隐瞒、验证不可负担时应修订。
- 目标期刊的分区体系、年份和来源由 brief 指定。JCR 与中科院分区分别记录；硬件预算可修改，A100 40GB 只是示例配置。
- 文献搜索和全文阅读由人或具备检索工具的 agent 完成。本仓库 CLI 不提供自动论文检索、模型训练或投稿功能。
- 开发集用于候选与超参数选择。冻结协议后再运行正式实验；最终测试须在选择固定后解锁，不按测试结果重新挑选方法。
- 真实结果必须保留配置、seed、split、代码版本、原始日志及完整成本；失败、负结果和实际超预算也要入账。
- `synthetic` 数据仅用于演示程序。没有真实实验只能写计划或带缺口的待填稿；不得补造数据、显著性、来源或新颖性。

## 修改本工具

保持 Python 标准库实现和可读 JSON 优先。协议或登记行为改变后，运行 `python -m unittest discover -s tests -v` 及一次新的 `demo`。不要通过删掉失败记录、降低证据条件或把 synthetic 改成真实标签来让检查通过。未知字段含义时先检查实际 CLI 和数据格式，不发明命令。
