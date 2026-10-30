# PE6203 Tool Harness Adaptation

PE6203 选题 4：研究工具环境发生变化后，如何更新 Agent 的工具知识，并比较不更新、全量重写和选择性修补三种策略。

本项目基于 [Octobrist/MCPEvol-Bench](https://github.com/Octobrist/MCPEvol-Bench)，保留基准代码和任务数据。上游基准说明见 [UPSTREAM_README.md](UPSTREAM_README.md)。

## 当前进度

- [x] 阶段一：搭建环境、接入方舟模型、运行一个原始任务并保存真实轨迹。
- [x] 阶段二：实现 Early、Middle、Late 三版本运行，固定任务 28、144、156，完成 9 次真实验证。
- [x] 阶段三：接入外部 JSON 工具知识、阻止自动刷新，提供统一原始结果读取接口。
- [x] 阶段四运行器侧：三策略接口、参数隔离、评分桥接、原始证据与交接文档。
- [ ] 正式实验：接入成员 2 的实际方法，并由成员 3 完成正式多任务评测。

阶段四已完成任务 156 的三策略接口样例 × 三版本共 9 次真实运行，条件审计通过；9 次评分中 8 次有效、1 次空正文失败，缺失项保持为空。56 项测试通过。成员 2 的正式算法尚未交付，这些结果仅用于接口验收。

当前工作区：`D:\6203-final`；主仓库在 `outputs/PE6203-Tool-Harness-Adaptation`。在 PowerShell 执行 `. D:\6203-final\start-work.ps1` 进入环境。

**下一步先读 [阶段四联调与交付说明](docs/stage4-integration-and-handoff.md)**；报告素材见 [运行环境与基准集成说明](docs/member1-report-section.md)。

## 开始运行

环境安装、模型配置和实际验证过的命令见 [成员 1 运行说明](member1/README.md)。

**阶段二的固定清单、版本映射、运行命令和验证结果见 [阶段二交付说明](docs/stage2-fixed-tasks-and-running.md)。** 阶段二入口可自动启动和清理服务：

```powershell
.venv\Scripts\python.exe -X utf8 member1/run_versions.py --version all
```

**阶段三的输入格式、成员 2/3 交接命令和防刷新验证见 [知识与结果交付说明](docs/stage3-knowledge-and-results-handoff.md)。** 使用冻结的 Early 知识运行三个版本：

```powershell
.venv\Scripts\python.exe -X utf8 member1/run_versions.py --version all --knowledge-dir member1/knowledge_examples/no_update
```

安装依赖并在本地配置 `.env` 后，在仓库根目录打开两个 PowerShell 窗口：

```powershell
# 窗口一：启动时间工具和计算器
& .\member1\start_mcp.ps1
```

```powershell
# 窗口二：运行任务 156
.venv\Scripts\python.exe -X utf8 member1/run_task.py
```

测试命令：

```powershell
.venv\Scripts\python.exe -X utf8 -m pytest -q
```

## 主要文件

| 路径 | 内容 |
| --- | --- |
| `member1/README.md` | 阶段一环境和运行说明 |
| `member1/run_task.py` | 复用基准 Agent 的单任务运行入口 |
| `member1/evidence/success/` | 真实成功运行的原始结果与轨迹 |
| `member1/evidence/provenance.json` | 运行命令、上游版本和代码哈希 |
| `member1/requirements-lock.txt`、`package-lock.json` | 本次运行依赖版本 |
| `docs/member1-development-plan.md` | 成员 1 开发计划与阶段完成记录 |
| `docs/stage2-fixed-tasks-and-running.md` | 阶段二交付、固定任务清单与三版本验证 |
| `member1/tasks_manifest.json`、`member1/run_versions.py` | 固定子集与版本运行入口 |
| `docs/stage3-knowledge-and-results-handoff.md` | JSON 知识包与原始结果读取协议 |
| `member1/knowledge.py`、`member1/read_results.py` | 知识包导出/校验与 JSONL 结果读取 |
| `member1/run_comparison.py`、`member1/protocol.py` | 三策略批次与固定推理参数 |
| `member1/scoring_bridge.py`、`member1/evidence/stage4/` | 评分桥接与真实验收证据 |
| `src/`、`servers/`、`anotation_path/` | 上游基准代码、服务配置和任务资源 |

`.env`、本机运行时凭证、虚拟环境、Node 依赖和临时输出均通过 `.gitignore` 排除。仓库提供不含密钥的 `.env.example`；每位组员在本地配置自己的凭证。

## 来源与实验约定

- 上游仓库：`https://github.com/Octobrist/MCPEvol-Bench`
- 使用的上游 commit：`888c779a0fe735f612ca62bdd1fdd7c9e6bf8701`
- 本组新增代码主要位于 `member1/`，Agent 兼容性调整及停止规则详见运行说明。
- 后续三种策略须使用相同模型、推理参数、任务集、停止规则与 judge 协议。
