# 阶段四：三策略接口联调与交付

2026-10-30。成员 1 的运行器、三策略批次入口、评分输入桥接、证据归档与交接说明已完成。成员 2 尚未交付正式 `full_rewrite` / `selective_patch` 方法，本次使用明确标记的接口测试样例。正式算法对比与成员 2、3 本人确认仍待完成。

## 1. 现在的工作目录

已按用户要求迁移至 `D:\6203-final`。主仓库位于：

```text
D:\6203-final\outputs\PE6203-Tool-Harness-Adaptation
```

在 PowerShell 中进入环境：

```powershell
. D:\6203-final\start-work.ps1
```

该入口设置工作目录、临时目录、Git 路径和本机服务的代理例外，不加载或打印 API 密钥。已有本地配置位于 `D:\6203-final\work\stage4.env`，通过 `--env-file` 显式传入。新运行均写入仓库的 `outputs/`。原 C 盘目录保留为迁移时备份，后续开发只在 D 盘继续。

迁移复制 37,755 个文件，共 636,497,730 字节；逐文件 SHA-256 比对无差异。两个虚拟环境的 Windows 控制台启动器已重新生成。迁移后 Early、Middle、Late 的任务 156 工具发现检查均为 `tools_ready`。历史轨迹中的旧绝对路径保留原样，结果读取器通过归档内的相对位置读取。

## 2. 验收结果与结论范围

| 项目 | 实际结果 |
| --- | --- |
| Git 基线 | `222764661527f7be108d05b986d0576d66cc1e59`；本次 Stage 4 为基线之后的本地修改 |
| 基准来源 | Octobrist/MCPEvol-Bench，commit `888c779a0fe735f612ca62bdd1fdd7c9e6bf8701` |
| 三策略 × 三版本 | 原始任务 156，9 次真实模型任务运行，9 次正常结束 |
| 条件与隔离检查 | 9/9 通过；知识、参数、任务、初始文件状态、服务快照与进程清理有记录 |
| 真实评分 | 已请求 9 次；8 次返回有效评分，1 次没有返回正文 |
| 自动测试 | 56 项通过，包含已有阶段的回归测试 |
| 环境检查 | `pip check` 通过；迁移后 3 个版本的工具发现检查通过 |
| 成员 2 真实更新方法 | 未交付；本次不能用于论证算法效果 |

三份策略标签分别对应：`no_update` 固定 Early 目录；`full_rewrite` 样例直接导入保存的目标版本目录；`selective_patch` 样例替换发生变化的目录项，保留相同项。后两者只是用于检查运行器的输入和输出能否接通，不包含组员设计的知识更新算法。样例包均有 `test_fixture: true`，批次 `purpose` 为 `interface_smoke`；正式 `strategy_comparison` 模式拒绝这些样例。

| 环境 | 策略标签 | 任务状态 | TF | Grounding | PE |
| --- | --- | --- | --- | --- | --- |
| Early | no_update | completed | 10 | 10 | 10 |
| Early | full_rewrite（样例） | completed | 10 | 10 | 10 |
| Early | selective_patch（样例） | completed | 10 | 10 | 10 |
| Middle | no_update | completed | 10 | 10 | 10 |
| Middle | full_rewrite（样例） | completed | 10 | 10 | 10 |
| Middle | selective_patch（样例） | completed | 10 | 10 | 10 |
| Late | no_update | completed | 10 | 10 | 10 |
| Late | full_rewrite（样例） | completed | 缺失 | 缺失 | 缺失 |
| Late | selective_patch（样例） | completed | 10 | 10 | 10 |

缺失项的服务端用量记录为 8,192 个完成 token，全部标为 reasoning token，`raw_response` 为空；保存为 `judge_error`，未补零或自动重试。本次原始接口响应没有另存 `finish_reason`，因此原因判断以空正文与用量记录为依据；新代码已补充保存该字段和响应 ID。9 次任务及 9 次评分请求的授权已用完，没有追加付费评分。

任务 156 的跨版本 TF 计算 `mean(TF) - population_stddev(TF)`：no_update 与 selective_patch 样例均为 10；full_rewrite 样例因 Late 缺失而为 `null`。这只是单任务接口验证，不能作为完整基准 ECS 或选择性修补优于其他方法的证据。

用量由原始响应汇总：任务运行输入 34,077、输出 3,370，总计 37,447 token；评分输入 27,098、输出 17,749，总计 44,847 token。合计 82,294 token，包含失败评分的用量。没有将 token 数换算为未核实的金额；知识更新成本为未知 `null`，不能记成零。

## 3. 环境恢复与三个版本

本机实际验证环境：Windows、Python 3.12.14、Node.js 24.21.0、npm 11.19.0、`@1mcp/agent` 0.39.6。Python 和 Node 依赖分别由 `member1/requirements-lock.txt`、`package-lock.json` 锁定。Python 基础解释器、Node 和 Git 使用本机已安装运行时，项目依赖位于主仓库 `.venv` 与 `node_modules`。

其他电脑首次安装（在解压或克隆后的主仓库执行）：

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r member1/requirements-lock.txt
npm.cmd ci --registry=https://registry.npmjs.org --cache=.npm-cache --no-audit --no-fund
.venv\Scripts\python.exe -m pip check
```

当前机器已恢复依赖，无需再安装。其他电脑可复制 `.env.example` 为自己的 `.env` 并填写本地凭据；不要覆盖已有配置。本机提供的密钥不包含在源码交付包中。源码包可以没有 `.git`，运行器此时记录 `project_commit: null`，同时保留执行代码、Agent、任务来源与快照的哈希；若需要 Git 提交标识，请克隆仓库后覆盖交付文件。

| 版本 | 官方服务快照 | 本地端口 |
| --- | --- | --- |
| Early | original | 3051 |
| Middle | iter3 | 3053 |
| Late | iter5 | 3055 |

固定任务为 28、144、156。运行器核对原始快照哈希，为每次运行准备独立工作目录和空任务登记，按版本启动 1mcp，退出时停止自身创建的进程树。端口被占用时明确失败，避免误用外部正在运行的服务。

无需模型费用的工具发现检查：

```powershell
.venv\Scripts\python.exe -X utf8 member1/run_versions.py --version all --task-id 156 --check-tools
```

下面是真实模型运行命令，会产生 API 费用；本次没有重复执行：

```powershell
# 单个版本：将 Early 换成 Middle 或 Late。
.venv\Scripts\python.exe -X utf8 member1/run_versions.py --version Early --task-id 156 --env-file D:\6203-final\work\stage4.env
# 三个版本、全部固定任务，沿用冻结的 Early 知识。
.venv\Scripts\python.exe -X utf8 member1/run_versions.py --version all --knowledge-dir member1/knowledge_examples/no_update --env-file D:\6203-final\work\stage4.env
```

## 4. 成员 2 交接输入

知识包字段及加载协议沿用 [阶段三说明](stage3-knowledge-and-results-handoff.md)。每个策略、目标环境、任务提供一个 `<task-id>.json`。需要完整的 `tools`、对应 `instructions`、`strategy`、`source_version`；实际更新成本由成员 2 提供，缺失时保留 `null`。

新的批次计划样例是 `member1/knowledge_examples/stage4_demo/comparison.json`，核心字段为：

- `task_ids`、`versions`：本次共同任务与环境。
- `run_config`：唯一的模型与推理配置，不包含凭据。
- `knowledge_dirs`：三个策略各自在三个环境下的知识目录，路径相对于计划文件。
- `purpose`：本次样例为 `interface_smoke`；成员 2 交付真实方法产物后，新建正式计划使用 `strategy_comparison`。

`no_update` 对同一任务跨版本必须使用完全相同的文件字节；其 `source_version` 保持 Early，不因目标环境变化而改写。不能通过删除样例标记将样例改称真实算法结果。扩展为 28、144、156 三个任务前，须补齐每个目录中的三个知识包，运行器会在发起任何请求前检查全部输入。

三策略真实批次入口（会产生模型费用）：

```powershell
.venv\Scripts\python.exe -X utf8 member1/run_comparison.py --plan member1/knowledge_examples/stage4_demo/comparison.json --env-file D:\6203-final\work\stage4.env
```

入口先冻结全部知识文件和模型配置，再开始任务。它不会从实时工具目录刷新传入的工具名称、参数或说明；传入规则会加入 Agent 系统提示。各策略共用以下配置：

```json
{
  "model": "deepseek-v4-flash-ga-260731",
  "base_url": "https://ark.cn-beijing.volces.com/api/v3",
  "temperature": 0.2,
  "max_completion_tokens": 4096,
  "max_round": 10,
  "request_timeout": 60,
  "stop_policy": "final_text_after_tool_result"
}
```

每个批次有独立目录，每个案例有独立工作状态。指定已有输出目录会拒绝覆盖。`fairness_audit.json` 检查任务、参数、知识哈希、模型实际工具输入、规则、初始文件状态、服务入口和清理状态是否一致；它验证运行条件，不保证每次回答正确，也不能让顺序运行的真实时钟返回相同时间。

## 5. 成员 3 读取、评分与 ECS

从交付归档离线核查，无需启动 MCP 或访问模型：

```powershell
.venv\Scripts\python.exe -X utf8 member1/run_comparison.py --audit member1/evidence/stage4/interface_validation
.venv\Scripts\python.exe -X utf8 member1/read_results.py member1/evidence/stage4/interface_validation --output outputs/stage4-replay.jsonl
.venv\Scripts\python.exe -X utf8 member1/scoring_bridge.py align member1/evidence/stage4/scoring
```

结果读取器支持单案例、阶段二/三 suite、三策略 comparison。失败案例保留，损坏轨迹单独记录 `read_errors`，不静默删除。导出文件若已存在请换一个新名字。

准备新评分输入是离线步骤：

```powershell
.venv\Scripts\python.exe -X utf8 member1/scoring_bridge.py prepare member1/evidence/stage4/interface_validation --output-dir outputs/stage4-score-replay --judge-config member1/judge_config.example.json
```

评分桥接复用未经修改的上游 `build_mcp_bench_judge_prompt`，绕过原评分入口导入时连接本机 MCP 及依赖缺失 `real.json` 的问题。它用保存的实际环境工具目录及相应说明层、原问题、完整轨迹和最终答案构造评分输入；不把参考答案或策略系统提示发给 judge。模型的工具观察仍沿用上游截断行为，但 judge 统一通过调用 ID 恢复日志中的完整工具返回；这是明确记录的评分输入选择。

评分协议包含 rubric 哈希、固定 judge 参数、轨迹政策及提示词哈希。同一任务同一次评分的三个维度顺序对全部策略/环境一致。默认 judge 与执行模型相同，temperature 0、最大完成 token 8192、每例 1 次，适用于本次接口验证；正式研究需事先固定评委模型与重复次数并说明潜在偏差。

付费评分入口（对新目录执行前需有该批次的费用授权）：

```powershell
.venv\Scripts\python.exe -X utf8 member1/scoring_bridge.py judge outputs/stage4-score-replay --env-file D:\6203-final\work\stage4.env
```

每条评分保存原文、用量、时间、解析结果或错误；新代码也保存响应 ID 与结束原因。SDK 不自动重试。再次运行相同目录只读取已保存的尝试，不重新收费，包括失败尝试；提示词或配置被修改会报错。不要删掉失败文件来伪装首次评分。需要额外评分时，应另建经批准的批次并保留前次证据。

同一策略与任务必须恰有 Early/Middle/Late 各一条完整评分才能计算该任务 ECS。缺少版本、重复案例或评分失败都返回 `null` 与原因，不能填零或丢弃；多个任务的正式总体 ECS 仍由成员 3 根据预定任务集合汇总，不能用当前单任务的 10 代替全基准结论。

## 6. 交付文件与验收

| 文件 | 内容 |
| --- | --- |
| `member1/run_comparison.py` | 批次输入冻结、三策略运行和条件审计 |
| `member1/protocol.py` | 无凭据的固定推理参数校验 |
| `member1/scoring_bridge.py` | 离线评分准备、真实 judge 与跨版本对齐 |
| `member1/evidence/stage4/interface_validation/` | 9 次真实任务轨迹与审计 |
| `member1/evidence/stage4/scoring/` | 9 条评分原始记录、其中 1 条失败；固定协议和输入 |
| `member1/evidence/stage4/results.jsonl` | 统一结果读取器导出 |
| `member1/evidence/stage4/verification.json` | 验收与实际用量汇总 |
| `docs/member1-report-section.md` | 成员 6 可整合的报告素材 |
| `docs/member1-development-plan.md` | 完成项和跨成员待办 |

归档不包含 API 密钥、1mcp 管理凭据、虚拟环境或运行时会话。运行时目录仍在本机完整保留。最终代码检查：

```powershell
.venv\Scripts\python.exe -X utf8 -m pytest -q
.venv\Scripts\python.exe -m pip check
git diff --check
```

测试覆盖：冻结全部输入后才启动、禁止样例冒充正式结果、参数和状态串用检测、输出迁移读取、完整工具证据拼接、失败案例保留、评分边界、禁止重复收费、缺失/重复版本不计算 ECS，以及前阶段已有功能。

## 7. 待办与已知问题

1. 成员 2 提供真实 full_rewrite / selective_patch 产物后替换计划中的目录，并完成正式方法联调；目前不能声称组员方法已经验收。
2. 成员 3 按本文实际运行、确认评测参数并签收；已有代码自动验证不等于成员 3 本人确认。
3. Late/full_rewrite 的本次评分缺失。补评需额外费用授权；当前已准确保留缺失状态。
4. 任务 156 的新增工具不是完成问题的必需工具，不能据此证明工具迁移能力；28、144 的历史记录在阶段二/三归档，本阶段没有再次对它们进行三策略付费实验。正式实验须预先确定足够覆盖变化与能力保留的任务集合。
5. 时间服务曾观察到 ISO 时区偏移现象；当前验证主要依赖 `get_time_info` 的时、分、秒，正式时区相关实验需复核服务输出。时钟任务的每次“现在”也会变化。
6. 当前 8 条有效评分全部为 10，并不证明策略等效或适应有效；没有据此编造“更新不足/过度”的失败案例。失败分析与正式多任务统计仍属成员 2、3、5 的后续工作。
