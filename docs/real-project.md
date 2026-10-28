# 从演示切换到真实研究

真实项目从新的 `init` 目录开始。不要删除演示中的 synthetic 标记后继续使用示例数值。以下步骤不要求访问任何特定 GPU 服务器；本地、实验室或获授权的执行器都可产生登记材料。

## 1. 填 brief 与论文机制

编辑 `brief.json`，写一个具体的研究问题和有边界的预期贡献。`target.ranking_system` 填采用的体系，`ranking_year` 填对应年份，并在阅读记录附来源；如同时使用 JCR 与中科院分区，分别记录，不把 Q1 直接翻译成中科院一区。`hardware` 可改为实际硬件；默认 A100 40GB 是演示性配置。

`budget.max_gpu_hours` 是总 GPU 小时，`max_runs` 是总运行数。冻结前的 pilot／历史探索保留独立台账，其实际总成本填写到可选的 `prior_gpu_hours` 与 `prior_runs`（默认为 0），计入项目总预算。不补造旧运行的协议 hash，也不把它们自动当作冻结后的正式证据。CPU 实验可以记 0 GPU 小时，但应在实际日志补充墙钟时间、硬件和资源开销。MVP 不自动计费或调度训练。

为训练、开发、测试各生成一个 JSON 字符串 ID 列表，例如 `["train-0001", "train-0002"]`。三个清单必须非空、内部唯一、相互不重叠；保存在项目内，填入 `data.splits` 的 `manifest_path` 与真实 SHA256。ID 应对应实际样本或被试／场景划分单位，避免同一对象的近重复样本泄漏到多个集合。数据版本、许可和划分依据也要记录。

阅读全文后填 `papers.json` 的标题、引用、链接、机制、输入输出、假设、限制和原文证据位置。`code` 记录是否复用来源代码、许可核查和署名要求；即使独立实现，也应核查并说明来源。论文、代码、权重和数据可能适用不同许可证。

## 2. 收敛组合并预定实验

`candidates.json` 中最多保留三个初始候选，指定一个 `selected_id`。每个候选都有强基线理由、两项或三项模块、机制接口和互补假设。填写 `search_log`，记录检索式、日期和来源；`nearest_neighbors` 记录最接近工作的标题／链接与差异。CLI 检查记录存在，近邻检索质量仍需要阅读判断。

`plan.json` 中固定 seed、估计单次 GPU 小时、预处理、backbone、训练预算、评价流程和调参预算。`baseline_check` 的参考指标、容差和上下文须可比；不能用不同数据划分的文献分数当作无条件复现标准。若只做了本地 pilot，可记录其运行条件作为参考。主指标的方向在 brief 中固定。

使用 `stop_rules` 记录失败上限、最小有意义提升、简化条件与负结果政策。简化可以去掉成本高且无独立收益的模块、减少候选或更换可复现基线；改变被冻结协议时应建立新的项目／协议，保留旧记录。

```bash
python -m paper_composer validate my-study --ready
python -m paper_composer ablations my-study
python -m paper_composer freeze my-study
```

在冻结后改动 brief、机制来源、候选或计划，会改变协议身份并阻止继续按旧协议登记。不要覆盖旧协议或旧结果来消除错误。

## 3. 接入自己的训练脚本

执行器应接收 arm、seed、split 和固定配置，根据 arm 启用相应机制，先训练／评价基线，再执行消融。CLI 不会替你写数据加载器、调用深度学习框架或计算模型指标。

每次运行将原始日志和实际配置保存到项目内。推荐日志同时包含起止时间、命令、硬件、数据清单 hash、代码 commit、训练参数、指标计算方式和失败信息。原始日志不可只保留漂亮的最终一行；失败运行的异常与实际成本同样保留。

### 结果登记格式

登记文件是一个 JSON 对象，字段如下。值必须来自实际运行和实际文件，不能将表中的说明直接当成数据：

| 字段 | 值与约束 |
| --- | --- |
| `run_id` | 唯一运行 ID；重试使用新 ID，保留失败的旧 ID |
| `arm` | 矩阵中的 arm，例如 `baseline` 或 `m1+m2` |
| `seed` | 协议中允许的整数 seed |
| `split` | `dev` 或 `test` |
| `status` | `completed` 或 `failed` |
| `metric` | 成功时为有限数值，失败时为 `null`；部分完成但不足以形成有效结果的数值留在原始日志 |
| `gpu_hours` | 实际非负 GPU 小时；多卡应按卡数累计 |
| `synthetic` | 真实项目为 `false`，与 brief 保持一致 |
| `protocol_hash` | 从本项目 `protocol.json` 读取的冻结 hash |
| `code_version` | 实际代码版本，建议 commit 与 dirty 状态或快照 hash |
| `config_path` / `config_sha256` | 项目内配置相对路径及其实际 SHA256 |
| `artifact_path` / `artifact_sha256` | 项目内原始日志相对路径及其实际 SHA256 |
| `outcome` | `positive`、`negative`、`neutral` 或 `failure`；按实际表现记录 |
| `notes` | 运行上下文、负结果、失败原因或成本异常说明 |

Python 标准库可以用 `hashlib.sha256(path.read_bytes()).hexdigest()` 计算文件 hash。哈希对应的是文件原始字节，重新格式化 JSON 也会改变它。提交登记后保持配置和日志不变。

```bash
python -m paper_composer record my-study --file result.json
python -m paper_composer report my-study
```

`outcome` 是运行者的解释标签，不是自动证明机制有效；应在可比基线结果齐备后解释改善或退化。完整台账需要包括所有尝试，CLI 无法知道你遗漏了某次外部运行。它检查保存的配置／日志 hash，不解析日志核对指标，也不核实 `code_version` 是否对应真实 commit；训练适配器和人工复核负责这些事实。

## 4. 固定选择，最后使用测试集

完整开发集矩阵和 seed 结果齐备、基线复现检查通过后，用预先约定的开发选择规则选择方案。可以因成本选择更简单的方案，并写清理由。将理由绑定开发证据，不引用未解锁的测试分数。

```bash
python -m paper_composer select my-study --arm m1+m2 --reason "开发集均值与预定成本约束支持该方案"
```

选择保存后，测试仅接受基线和选定 arm 的预定 seed。测试结果不佳仍需登记；不可反复改选择再看同一测试集。若必须重新设计，把旧测试集已被接触这一事实纳入新计划，并寻找新的独立保留集。

## 5. 填论断并生成报告

MVP 的 `claims.json` 用于最终实验主张：为每条主张关联 `source_paper_ids`、完成的最终测试 `supporting_run_ids`、适用范围和边界；没有支持的部分保持 planned。更完整的文献事实、方法设计、组合假设和开发集消融观察写入 [叙事工作表](../templates/narrative-evidence.md)。开发消融可以用于正文机制讨论，前提是明确标注 split，并承认它参与了方法选择；不能将其伪装为独立最终测试。

```bash
python -m paper_composer report my-study --output my-study-report.json
```

报告指出缺失证据、预算状态和阶段。`--output` 只允许新路径，重复输出请改用新文件名。缺多少写多少，不填造。即使报告显示材料就绪，仍需人工复核原始日志、统计方法、论文论断、期刊格式和引用；MVP 不自动生成可投稿全文，也不自动投稿。
