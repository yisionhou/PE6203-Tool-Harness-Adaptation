# 成员 3：评测与实验

目前已完成评测程序、先导数据独立复核、结果表、成本去重、重复实验方案和时钟服务实测。**尚未完成新的付费模型实验，也未完成扩充任务评测。** 不能把 27 条历史结果复制成三次重复。

## 已交付

- `analyze.py`：从原始运行和 judge 回执复算 TF、PE、Grounding、ECS；验证输入与协议哈希；缺失保留为空；多次重复输出均值及样本标准差。
- `experiment.py`：冻结知识包、任务、配置与源代码哈希；筛选官方扩充候选；检查本机条件；运行重复实验和评分，再自动汇总。
- `check_clock.py`：直接调用三个官方时钟快照，不使用模型，不改动快照。
- `evidence/pilot-v2/report.md`：目前应使用的 27 条先导结果复核表；JSON 保留逐条件数据与用量。
- `evidence/clock-check/clock-audit.json`：9 次真实服务调用。三个版本的结构化时间正常，locale 和 timestamp 接口均约偏快一小时。
- `evidence/tool-check/fairness_audit.json`：三策略 × 三版本 × 三任务的 27 次实际工具连接与知识加载全部通过，状态均为 `knowledge_ready`，无付费模型调用。
- `evidence/knowledge-equivalence.json`：独立确认九组对应条件的全量/选择性模型可见知识完全相同。
- `studies/replication-v2/study.json`：3 任务 × 3 策略 × 3 版本 × 3 次全新重复，共 81 次任务与 81 次评分的冻结计划。v1 是开发期方案，不用于执行。
- `studies/replication-v2/expansion-candidates.json`：201 个官方选定任务的服务覆盖筛查。只有 28、144、156 的全部服务已受当前运行器支持；其他候选必须先验证服务、快照、输入文件与工具知识。
- `tests/test_analysis.py`：13 项统计边界测试。

本次修复了本地归档布局：将原本位于重复目录下的 `member1` 复制到仓库根目录。保留原目录；原始历史证据没有改写。

## 模型 API 设置

仓库根目录 `.env` 已创建，且已被 `.gitignore` 排除。请在本机填入自己的 `ARK_API_KEY`。没有金钥时预检查返回未就绪，程序不执行付费请求。

官方操作说明：[获取 API Key](https://docs.volcengine.com/docs/ark/api-key?lang=zh&redirect=1)、[开通模型与首次调用](https://docs.volcengine.com/docs/ark/quick-start?lang=zh)。GitHub 访问权限与模型 API 额度是两回事。

任务模型与 judge 均沿用 `deepseek-v4-flash-ga-260731`。需要账户可访问该模型，并具有可用额度。若必须改模型，应重建统一配置与冻结方案，重新运行所有对比条件，不混合历史模型结果。

## 已安装的本机环境

本仓库 `.venv` 已按 `member1/requirements-lock.txt` 安装；Node 服务已按 `package-lock.json` 安装。`pip check` 通过。安装临时文件放在 `.tmp`，已忽略。

原有 85 项测试通过，新增 13 项测试通过，共 98 项；前者在允许本机异步通讯的执行环境中验证。受限环境中部分异步测试可能停滞。

## 先检查，后运行

在本仓库根目录执行：

```powershell
.venv\Scripts\python.exe -X utf8 member3/experiment.py preflight --study member3/studies/replication-v2
```

当前缺少 API Key，因此 `ready=false`；其他依赖检查通过。

确认模型可用与调用预算后运行新的重复批次（会产生模型费用）：

```powershell
.venv\Scripts\python.exe -X utf8 member3/experiment.py run --study member3/studies/replication-v2 --env-file .env --output-dir outputs/member3-replication-v2
```

输出目录必须全新。中断时保留原目录，不覆盖或重新解释已有证据；任务执行不是自动续跑。评分器保存请求回执，余额不足停止后续请求，已保存失败评分不会自动付费重试。

这个计划只扩充重复次数，**不等于扩充官方任务范围**。时钟服务已知错误需在报告中独立标记，不能归因于策略；若要修改服务修复错误，必须创建单独实验版本，重建证据与知识包，不能更改冻结的官方对比环境。

## 离线复算

```powershell
.venv\Scripts\python.exe -X utf8 member3/analyze.py --live member2/evidence/pre_handoff/live --scoring member2/evidence/pre_handoff/scoring_v2 --adaptation member2/evidence/adaptation --task-ids 28 144 156 --expected-repetitions 1 --label pilot-reanalysis --output-dir outputs/member3-pilot-reanalysis
```

新批次重复数据可多次传入成对的 `--live` 和 `--scoring`，再指定预定的 `--expected-repetitions 3`。重复的 run_id 会被拒绝；judge 或推理配置不同的批次不能合并。

ECS 按同一任务同一次重复的 Early/Middle/Late TF 均值减总体标准差，再等权平均。任一预定条件无有效评分时，对应总体指标为空。JSON 的 `observed_mean` 仅为部分样本描述，不代替总体结果。更新成本以 `update_id` 去重；推理与评分用量分开统计。

## 交给成员 5 的边界

先导实验中有效 TF 均为 10，存在任务完成评分天花板。全量重写与选择性修补的九组对应知识在模型可见内容上相同，不能由单次 PE 差异推出更新方法优劣。真实日志可支持重复调用和服务错误分析，尚不能提供更新不足、更新过度造成任务损伤的真实证据。

正式扩充任务应覆盖必需工具迁移与未变化能力对照；当前任务 156 的新增工具不必使用，不能宣称其验证了强制迁移。候选按所缺服务数量和任务 ID 排序，没有用分数或参考答案挑选。
