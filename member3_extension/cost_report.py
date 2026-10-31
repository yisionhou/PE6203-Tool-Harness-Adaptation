"""Shared offline cost-section renderer for reports and plots."""
from pathlib import Path
import hashlib
import json

COST_HEADING = '## 更新成本對比圖與重複量測'
NEXT_HEADING = '## 评分异常与使用范围'


def load_cost_data(root):
    folder = Path(root) / 'member3/evidence/formal/cost-comparison'
    required = ('benchmark.json', 'figure-provenance.json',
                'update_cost_comparison.png', 'update_cost_comparison.svg')
    missing = [name for name in required if not (folder / name).is_file()]
    if missing:
        raise ValueError('Required cost evidence is missing: ' + ', '.join(missing) +
                         '; generate the offline cost figures before delivering the report')
    raw = (folder / 'benchmark.json').read_bytes()
    provenance = json.loads((folder / 'figure-provenance.json').read_text(encoding='utf-8'))
    if provenance.get('benchmark_sha256') != hashlib.sha256(raw).hexdigest():
        raise ValueError('Cost figures are stale: benchmark fingerprint mismatch')
    for name, digest in provenance.get('figure_sha256', {}).items():
        if name not in ('update_cost_comparison.png', 'update_cost_comparison.svg'):
            raise ValueError('Unknown cost figure in provenance')
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Cost figure fingerprint mismatch: ' + name)
    return json.loads(raw.decode('utf-8')), folder


def render_cost_section(data, formal, image_ref):
    strategies = ['no_update', 'full_rewrite', 'selective_patch']
    labels = ['不更新', '全量重寫', '選擇性修補']
    summaries = [data['summaries'][s] for s in strategies]
    mean = [s['processing_wall_mean_seconds'] for s in summaries]
    reduction = data['processing_time_reduction_percent']
    table=['| 策略 | 程式處理時間（秒，平均 ± SD） | 更新 token | 重建工具記錄 | 重建規則區塊 | TF |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for label,strategy,s in zip(labels,strategies,summaries):
        table.append(f"| {label} | {s['processing_wall_mean_seconds']:.4f} ± {s['processing_wall_sample_sd_seconds']:.4f} | 0 | {s['regenerated_tools']} | {s['regenerated_blocks']} | {formal['aggregate']['strategies'][strategy]['metrics']['task_fulfillment']['mean']:.2f} |")
    conclusion=f'在相同電腦、相同六任務知識與相同處理範圍下重複量測 30 次，選擇性修補的平均處理時間為 {mean[2]:.4f} 秒，全量重寫為 {mean[1]:.4f} 秒，前者平均少 {reduction:.1f}%。兩者正式任務完成度皆為 10 分。這支持本機此實作的處理時間優勢與較小重建範圍；未量測人工工時或薪金。'
    section='''## 更新成本對比圖與重複量測

本節可用於作業 4.3 Update Cost。提供的報告範本允許以 token、時間或 API 費用作成本指標，並要求標明單位與統計範圍。

![更新成本比較](COST_IMAGE)

'''+ '\n'.join(table)+f'''

**口徑：** 每次處理六任務 × 三版本共 18 個知識條件；30 次離線重複、一次暖機，策略與條件順序按固定種子交錯。時間包含整個 `adapt()` 呼叫的校驗、偵測、複製、生成、保留檢查及最終完整性檢查，不含載入、共同初始化、磁碟讀寫、匯出、模型任務執行與評分。不更新的數值是校驗／複製等共同處理開銷，其改寫成本仍為 0。誤差線為 30 次的樣本標準差。TF 為原正式實驗的三次重複結果，不是新增模型任務。

**成本與效果：** {conclusion}

工具記錄從 68 減至 23，減少 {data['tool_record_reduction_percent']:.1f}%；規則區塊從 86 減至 34，減少 {data['rule_block_reduction_percent']:.1f}%。數量衡量重建工作範圍，不能直接換算成員工工時。三種策略的更新階段都沒有模型 API 呼叫，更新 token 與更新 API 費用皆為 0，因此此實驗沒有觀察到更新 API 費用差額。

**資料定位：** `benchmark.json` 保存 90 條策略／重複彙總、來源與程式雜湊、測量範圍；每條彙總包含 18 次相同輸入處理。所有生成結果均核對為與凍結知識相同。這是正式任務評測以外的離線成本微基準，沒有改寫原始 162 條評分或原有單次時間紀錄。
'''
    return section.replace('COST_IMAGE', image_ref), conclusion


def integrate_cost_section(content, section):
    if NEXT_HEADING not in content:
        raise ValueError('Report is missing the cost-section insertion boundary')
    if COST_HEADING in content:
        start = content.index(COST_HEADING)
        end = content.index(NEXT_HEADING, start)
        return content[:start] + section + '\n' + content[end:]
    return content.replace(NEXT_HEADING, section + '\n' + NEXT_HEADING, 1)
