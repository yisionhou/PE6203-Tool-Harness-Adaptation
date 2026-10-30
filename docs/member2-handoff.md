# 成员 2 → 成员 3 交付说明

更新日期：2026-10-30。

## 1. 当前状态

代码、知识包和 27 次任务运行可以交接；本轮有 25/27 条有效评分，不能交付完整的策略效果结论。缺失项保留为空，不补零、不使用旧轮分数替代。

成员 2 的第一版代码已完成，交付内容包括三种策略、知识包、更新日志和这轮真实验证记录。成员 3 接下来主要负责扩大实验范围、固定正式评测方案和统计分析。

| 部分 | 状态 |
| --- | --- |
| 不更新、全量重写、选择性修补 | 已实现 |
| 变化检测、规则依赖、知识保留检查 | 已实现 |
| 自动测试 | 85 项通过 |
| 真实任务 | 27/27 正常结束 |
| 本轮有效评分 | 25/27 |
| 正式多任务、多次重复结论 | 尚未完成 |

具体分数和限制见 [验证报告](member2-validation-report.md)。

## 2. 方法怎么理解

先比较新旧工具有哪些变化，再找到依赖这些工具的说明、参数规则和示例。

- **不更新**：继续使用原来的 Early 知识，文件内容不变。
- **全量重写**：重新生成当前任务需要的全部工具知识和规则。
- **选择性修补**：只重新生成变化工具及受影响规则，并核对其他知识保持不变。

第一版通过固定规则和模板生成，不调用模型改写知识。受影响的自由文本规则若没有生成配方，会要求审核。它不能识别工具目录中未声明的隐藏行为变化。

## 3. 优先看哪些文件

| 位置 | 用途 |
| --- | --- |
| `member2/README.md` | 方法、接口与运行说明 |
| `docs/member2-development-plan.md` | 详细计划与完成记录 |
| `member2/evidence/adaptation/comparison.json` | 27 个条件的运行计划 |
| `member2/evidence/adaptation/knowledge/` | 实际知识包 |
| `member2/evidence/adaptation/updates/` | 更新范围、保留哈希和成本 |
| `member2/evidence/pre_handoff/summary.json` | 本轮汇总数据 |
| `member2/evidence/pre_handoff/live/` | 原始结果与工作文件 |
| `member2/evidence/pre_handoff/scoring_v2/` | 本轮采用的评分输入和响应 |

旧 Stage 4 样例和 v1 评分保留作追踪，不加入本轮结果表。

## 4. 接手后先做三件事

**先读现有结果，不急着重新运行。** 使用统一读取器导出 27 条记录：

```powershell
.venv\Scripts\python.exe -X utf8 member1/read_results.py member2/evidence/pre_handoff/live --output outputs/member3-readback.jsonl
```

**再检查条件与证据。** 以下命令不调用模型：

```powershell
.venv\Scripts\python.exe -X utf8 member1/run_comparison.py --audit member2/evidence/pre_handoff/live
.venv\Scripts\python.exe -X utf8 member1/scoring_bridge.py align member2/evidence/pre_handoff/scoring_v2
.venv\Scripts\python.exe -X utf8 -m pytest -q
```

每次导出使用新文件名，避免覆盖证据。`completed` 只表示执行正常结束，任务质量要结合分数、轨迹和实际文件判断。

**然后确定正式实验范围。** 当前三个任务适合作为起点，但变化强度有限。应预先增加有明确迁移要求的官方任务，以及没有变化的保留能力对照任务。三种策略使用同一任务集合，不修改参考标签。

## 5. 复现步骤

当前电脑进入环境：

```powershell
. D:\6203-final\start-work.ps1
```

其他电脑按成员 1 说明安装锁定依赖，并设置自己的本地 `.env`。仓库为私有，成员 3 需要访问权限。

重新生成知识不调用模型：

```powershell
.venv\Scripts\python.exe -X utf8 member2/build.py --output-dir outputs/member3-new-knowledge
```

工具发现与知识加载检查也不调用模型：

```powershell
.venv\Scripts\python.exe -X utf8 member1/run_comparison.py --plan outputs/member3-new-knowledge/comparison.json --check-tools --output-dir outputs/member3-tool-check
```

正式任务运行会产生新的费用：

```powershell
.venv\Scripts\python.exe -X utf8 member1/run_comparison.py --plan outputs/member3-new-knowledge/comparison.json --env-file .env --output-dir outputs/member3-model-run
```

准备评分输入是离线操作。使用本轮固定配置与修正后的可见轨迹协议：

```powershell
.venv\Scripts\python.exe -X utf8 member1/scoring_bridge.py prepare outputs/member3-model-run --output-dir outputs/member3-scoring --judge-config member2/evidence/pre_handoff/judge-config-v2.json
```

确定正式实验预算后执行评分：

```powershell
.venv\Scripts\python.exe -X utf8 member1/scoring_bridge.py judge outputs/member3-scoring --env-file .env
```

评委只看到模型当时看到的工具返回，完整原文另存事件日志。遇到账户余额不足，评分器停止后续请求，已有记录保留。

## 6. 统计时保持这些规则

1. 固定模型、推理设置、任务集合和 judge 协议，重复实验也使用相同条件。
2. 不更新包跨版本字节一致，不临时从当前环境刷新它。
3. 更新、任务运行和评分成本分开记录。通过 `adaptation.update_id` 关联更新日志，同一个包重复使用不重复累计更新成本。
4. 超时、余额不足、格式异常与任务失败分开，不填零分、不删除记录。
5. 三个版本的 TF 齐全才计算任务 ECS，总体指标使用预先固定的任务集合。
6. 失败分析需要实际轨迹，不能把构造测试写成真实任务损伤。

## 7. 后续工作清单

- [ ] 在成员 3 的环境中读取这轮 27 条结果，核对原始记录。
- [ ] 固定正式任务集合、重复次数、评分协议和预算。
- [ ] 复核时间服务各接口的一致性，避免将服务问题误判为策略问题。
- [ ] 增加强制工具迁移案例与能力保留对照任务。
- [ ] 尽可能完成三次重复，报告均值与波动。
- [ ] 基于真实轨迹分析恢复、保留、更新不足和更新过度。

成员 2 当前可以交付代码与本轮验证材料。后续发现更新逻辑问题时，应根据具体失败轨迹修复，并保留修改前后的实验版本。
