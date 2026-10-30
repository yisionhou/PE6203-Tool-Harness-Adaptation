# 成员 2：工具知识更新

第一版实现 `dependency-aware-v1`，使用确定性模板与显式依赖图，提供真正执行不同更新路径的 `no_update`、`full_rewrite` 和 `selective_patch`。它不调用模型生成知识，更新 token 成本为 0，耗时由程序实际测量。

验收：82 项自动测试通过；27 个条件均完成工具发现与知识加载，审计通过；本轮没有模型或评分 API 请求。

详细计划见 [成员 2 开发计划](../docs/member2-development-plan.md)，报告素材见 [方法说明](../docs/member2-report-section.md)。本目录产物独立于成员 1 Stage 4 的 `test_fixture` 示例；历史示例仍保留原标记。

## 1. 已实现什么

| 文件 | 用途 |
| --- | --- |
| `catalog.py` | 工具观察校验、稳定身份、字段路径差异 |
| `knowledge_base.py` | 工具卡片、规则与示例、依赖检查、提示编译 |
| `adapt.py` | 三种策略、依赖传播、保留校验与更新成本 |
| `build.py` | 冻结九份目录观察，生成三策略知识包与成员 1 运行计划 |
| `tests/test_adaptation.py` | 改名、删除、参数与描述变化、保留、失败和导出测试 |
| `evidence/adaptation/` | 本次实际生成的输入快照、知识包、更新记录和批次计划 |
| `evidence/tool_integration/` | 27 个条件的工具发现和知识加载记录 |
| `evidence/verification.json` | 实际验收摘要与范围说明 |

现有 Python/Node 环境直接复用，不新增依赖，不读取本地 API 配置来生成知识。主仓库位于 `D:\6203-final\outputs\PE6203-Tool-Harness-Adaptation`。

## 2. 快速复现

进入当前工作环境：

```powershell
. D:\6203-final\start-work.ps1
```

离线重新生成一个新批次（输出目录必须不存在）：

```powershell
.venv\Scripts\python.exe -X utf8 member2/build.py --output-dir outputs/member2-new-build
```

默认只读取成员 1 历史记录中的九个 `result/tools.json`，覆盖任务 28、144、156 及 Early/Middle/Late。脚本不会打开这些目录里的答案、轨迹或参考信息。更换观察来源时可以设置 `--catalog-root`，仍需提供 `<Version>-task-<ID>/result/tools.json` 的结构。

无需模型费用的接入检查：

```powershell
.venv\Scripts\python.exe -X utf8 member1/run_comparison.py --plan member2/evidence/adaptation/comparison.json --check-tools --output-dir outputs/member2-new-tool-check
```

这会启动真实 MCP 环境，发现工具、加载知识并保存记录，属于 `tools_only` 模式。`knowledge_ready` 证明配置和知识接口接通，不证明所有调用参数已经被服务执行，也不产生 TF/PE 分数。

离线审计已有接入记录：

```powershell
.venv\Scripts\python.exe -X utf8 member1/run_comparison.py --audit member2/evidence/tool_integration
```

全部自动测试：

```powershell
.venv\Scripts\python.exe -X utf8 -m pytest -q
```

## 3. 三种策略怎么工作

初始知识从 Early 工具目录生成，工具身份是 `(source_server, source_name)`。同名工具属于不同服务器时保持独立。每个工具有一张知识卡片，包括定义说明、参数约束、可选输出约束和 Schema 形状示例；工具清单规则依赖全部卡片。

**不更新：** 不检查目标目录，复用初始知识包完整字节。同一任务跨版本包哈希相同。知识版本仍是 Early，目标运行环境由成员 1 的计划决定。

**全量重写：** 读取同样的目标目录，重新生成任务范围内的所有工具定义、卡片、规则和示例。即使没有发生变化，也执行完整生成流程。这里的“完整”指该任务送入模型的完整工具知识集合，不是基准全部 123 个服务。

**选择性修补：** 比较目录中的新增、删除、路由、输入参数、描述和可选输出 Schema；将变化工具作为依赖图起点，找到受影响卡片和后续规则，只重新生成这些块。未影响的工具记录和规则对象以规范 JSON 哈希校验保留，规则文字逐字保留。整个知识包会添加新的版本、更新 ID 和成本，不能因此声称整个更新包字节不变。

两个不同的工具名称不做语义相同推断。重命名处理为移除旧身份并增加新身份，随后更新工具清单与调用形状示例。真实目录没有声明的内部行为变化、输出语义变化，不能由本方法凭空发现。

依赖图支持传递依赖。额外人工规则可以是：

```json
{
  "id": "rule:expert-policy",
  "recipe": null,
  "depends_on": ["tool:calculator::calculate"],
  "text": "A calculator-specific usage policy."
}
```

当依赖工具未变化时，这段文字原样保留；一旦受到影响且没有已实现的生成配方，程序抛出 `ReviewRequired`，列出需要审核的规则，不导出假装已经修好的结果。全量重写遇到这种无法重新生成的规则也要求审核。自定义工具相关内容必须放进带依赖的规则块，不能放进没有跟踪的顶层字段或全局提示。调用者仍须正确声明依赖；程序不理解任意自由文本里的隐藏引用。

输入知识结构为 `initial/<task>.json`。代码方式执行单次修补：

```python
import json
from pathlib import Path
from member2.adapt import adapt, packet
from member2.catalog import read_catalog

base = json.loads(Path("member2/evidence/adaptation/initial/156.json").read_text(encoding="utf-8"))
target, _, _ = read_catalog("member2/evidence/adaptation/observations/Late/156.json")
updated, log = adapt(base, target, "selective_patch", "Late")
knowledge_package = packet(updated, "selective_patch", log)
```

API 支持把上一次内部知识状态作为下一次更新的基线；当前交付批次固定为独立 Early→目标版本，不能把两种实验协议混合统计。

## 4. 示例与一致性检查

示例只是符合 JSON Schema 的调用形状，不是正确任务答案或已经执行过的工具调用。参数值可能是占位符，模型仍须根据用户任务替换。对于无法生成满足约束的示例，记录 `example: null` 与明确原因；不把无效参数标成合法示例。

校验包括：唯一工具身份和模型名称、Schema 格式、只使用本地 Schema 引用、依赖无悬空/循环、卡片和路由一致、示例参数满足对应 Schema、局部更新范围不越过依赖闭包。结构检查不能证明自然语言语义正确或实际工具执行成功。

## 5. 输出如何交接

```text
evidence/adaptation/
├─ observations/<Version>/<task>.json       原始目录字节
├─ initial/<task>.json                      初始内部知识状态
├─ initial_packets/<task>.json              初始成员 1 格式知识包
├─ knowledge/no_update/<task>.json          与初始包相同
├─ knowledge/full_rewrite/<Version>/<task>.json
├─ knowledge/selective_patch/<Version>/<task>.json
├─ updates/<strategy>/<Version>/<task>.json 差异、影响范围、保留哈希与成本
├─ comparison.json                         成员 1 的 27 条件计划
└─ build_report.json                       观察来源、生成代码哈希和索引
```

共导出 21 个不同路径的知识包：不更新 3 份共享包，全量与局部各 9 份；组合成 27 个运行条件。每包都经成员 1 `load_knowledge` 校验，并由 `prepare` 检查计划中的全部条件。没有设置 `test_fixture`；它们来自真实程序式更新，但当前还未进行实际模型任务表现评估。

新增元数据 `knowledge_blocks`、`knowledge_global_instructions`、`adaptation` 不改变成员 1 既有输入协议。模型使用的是 `tools` 和编译后的 `instructions`，附加元数据用于追踪。每条任务的原始 `knowledge.json` 中有 `adaptation.update_id`，可与 `build_report.json` 和更新日志关联。

成本按实际更新 ID 去重。同一知识包用于三次重复任务运行，不代表更新执行了三次。全量与局部记录包括差异检测、规则生成和知识验证的 本机墙钟耗时，不包含文件读写、兼容包序列化、共享初始建库、任务推理和评分。建库耗时单列。无更新的逻辑更新成本为零，验证与复制开销另记 `harness_overhead_seconds`。本版无更新模型调用，tokens=0；没有估算美元费用。

## 6. 本次观察到的更新范围

| 版本 / 任务 | 全量重建工具 | 局部重建工具 | 全量重建规则 | 局部重建规则 |
| --- | ---: | ---: | ---: | ---: |
| Early / 28 | 3 | 0 | 4 | 0 |
| Early / 144 | 4 | 0 | 5 | 0 |
| Early / 156 | 3 | 0 | 4 | 0 |
| Middle / 28 | 3 | 0 | 4 | 0 |
| Middle / 144 | 4 | 1 | 5 | 2 |
| Middle / 156 | 3 | 1 | 4 | 2 |
| Late / 28 | 3 | 2 | 4 | 3 |
| Late / 144 | 4 | 2 | 5 | 3 |
| Late / 156 | 4 | 2 | 5 | 3 |
| 合计 | 31 | 8 | 40 | 13 |

本次单次构建记录中，全量累计更新时间约 0.155 秒，局部约 0.110 秒。这是小范围、单次、本机测量，不能解释为稳定的普遍加速比例；原值与计时边界见 `build_report.json`。任务 28/Middle 完全未变化，选择性修补没有重新生成任何卡片。

九组对应环境/任务的 full_rewrite 和 selective_patch 最终模型可见 `tools` 与 `instructions` 均完全一致。这与确定性生成器的设计相符，说明本例局部更新能恢复同一知识状态。它不能证明选择性修补的 TF/PE 更高。若正式执行中两者分数不同，应先考虑模型采样噪声和实际环境时间差，不能直接归因于方法内容差异。

## 7. 已知边界与下一步

- 本版是 Schema/描述驱动的程序式方法，没有实现任意自然语言知识的 LLM 重写，也不声称具备自主读取报错后推断隐藏变化的能力。
- 当前观察是成员 1 按相关工具与官方描述层生成的保存目录，不是完全黑盒探测。更新器没有读取演化标签或参考答案；观察生成方式须在报告中说明。
- 当前输入没有可比较的输出 Schema，因此输出变化处理仅由合成测试验证。
- 改名、删除、复杂参数和损坏依赖有自动测试；真实固定子集主要包含可选参数和描述变化，任务 156 的新增工具也不是完成该问题的必需工具。
- `test_affected_opaque_rule_requires_review_instead_of_silent_under_update` 展示遗漏更新风险被阻止；`test_full_rewrite_regenerates_every_card_and_rule_even_if_tools_are_unchanged` 展示额外人工措辞在全量再生成中可能丢失。它们是机制测试，不是课程要求的真实模型失败轨迹，不能写成实际任务损伤结论。
- 接下来由成员 3 固定正式任务集合与 judge 协议，判断是否扩充具有强制迁移的官方任务，再进行付费任务运行与评分。此前 Stage 4 的调用授权不用于这一新批次。

正式任务命令如下，会产生模型费用，尚未执行：

```powershell
.venv\Scripts\python.exe -X utf8 member1/run_comparison.py --plan member2/evidence/adaptation/comparison.json --env-file D:\6203-final\work\stage4.env --output-dir outputs/member2-model-comparison
```

完成真实运行后，再按成员 1 评分桥接说明准备 judge 输入；评委参数、重复次数和总费用必须在正式实验前固定。
