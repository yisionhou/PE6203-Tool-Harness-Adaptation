"""Create publication-ready cost figures and a report section from measured data."""
from pathlib import Path
import sys
import hashlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from member3.analyze import read,save


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    import numpy as np
    folder=ROOT/'member3/evidence/formal/cost-comparison'
    data=read(folder/'benchmark.json');formal=read(folder.parent/'results.json')
    strategies=['no_update','full_rewrite','selective_patch']
    labels=['不更新','全量重寫','選擇性修補']
    summaries=[data['summaries'][s] for s in strategies]
    font_manager.fontManager.addfont('C:/Windows/Fonts/msjh.ttc')
    plt.rcParams.update({'font.family':'Microsoft JhengHei','font.size':11,
        'axes.unicode_minus':False,'svg.fonttype':'path','axes.spines.top':False,
        'axes.spines.right':False,'axes.edgecolor':'#7c8795','axes.labelcolor':'#263446',
        'xtick.color':'#263446','ytick.color':'#263446'})
    fig,axes=plt.subplots(1,2,figsize=(13.4,6.5))
    fig.subplots_adjust(left=.07,right=.98,top=.78,bottom=.29,wspace=.32)
    fig.suptitle('工具知識維護成本比較',fontsize=21,fontweight='bold',y=.965)
    fig.text(.5,.885,'六個官方任務 × 三個版本；同一部電腦量測 30 次，時間顯示平均值與樣本標準差',ha='center',fontsize=11,color='#526173')
    mean=[s['processing_wall_mean_seconds'] for s in summaries]
    sd=[s['processing_wall_sample_sd_seconds'] for s in summaries]
    axes[0].bar(range(3),mean,yerr=sd,capsize=5,width=.6,
        color=['#a8b1be','#3568ae','#20846a'],error_kw={'elinewidth':1.3,'ecolor':'#344256'})
    axes[0].set_title('A  程式處理時間',loc='left',fontsize=14,pad=18)
    axes[0].set_ylabel('每套 18 個條件的處理時間（秒）')
    axes[0].set_xticks(range(3),[label+'\nTF '+f"{formal['aggregate']['strategies'][s]['metrics']['task_fulfillment']['mean']:.2f}" for label,s in zip(labels,strategies)])
    axes[0].set_ylim(0,max(m+s for m,s in zip(mean,sd))*1.27)
    axes[0].yaxis.grid(True,color='#e5eaf0');axes[0].set_axisbelow(True)
    for x,m,s in zip(range(3),mean,sd):axes[0].text(x,m+s+.035,f'{m:.3f} 秒',ha='center',fontweight='bold')
    x=np.arange(3);width=.34
    tools=[s['regenerated_tools'] for s in summaries];blocks=[s['regenerated_blocks'] for s in summaries]
    a=axes[1].bar(x-width/2,tools,width,label='重建工具記錄',color='#3568ae')
    b=axes[1].bar(x+width/2,blocks,width,label='重建規則區塊',color='#d68b38')
    axes[1].bar_label(a,padding=4);axes[1].bar_label(b,padding=4)
    axes[1].set_title('B  重建內容數量',loc='left',fontsize=14,pad=18)
    axes[1].set_ylabel('每套 18 個條件的重建數量')
    axes[1].set_xticks(x,labels);axes[1].set_ylim(0,max(blocks)*1.27)
    axes[1].yaxis.grid(True,color='#e5eaf0');axes[1].set_axisbelow(True)
    axes[1].legend(frameon=False,loc='upper left',fontsize=10)
    reduction=data['processing_time_reduction_percent']
    fig.text(.07,.19,f'選擇性修補：平均處理時間較全量重寫少 {reduction:.1f}%；工具記錄少 {data["tool_record_reduction_percent"]:.1f}%，規則區塊少 {data["rule_block_reduction_percent"]:.1f}%。',fontsize=11,color='#176b55')
    fig.text(.07,.12,'時間含驗證、偵測、複製及更新；不含初始建庫、載入、磁碟／匯出、任務推理與評分。',fontsize=9,color='#526173')
    fig.text(.07,.075,'三種策略的更新模型呼叫與 token 均為 0。TF 來自正式評測；程式時間未換算成人工工時或薪金。',fontsize=9,color='#526173')
    fig.savefig(folder/'update_cost_comparison.png',dpi=200,facecolor='white')
    fig.savefig(folder/'update_cost_comparison.svg',facecolor='white')
    plt.close(fig)
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
    (folder/'cost-report.md').write_text(section.replace('COST_IMAGE','update_cost_comparison.png'),encoding='utf-8')
    marker='## 更新成本對比圖與重複量測'
    for path,image in [(ROOT/'docs/member3-report-section.md','../member3/evidence/formal/cost-comparison/update_cost_comparison.png'),
                       (folder.parent/'summary.md','cost-comparison/update_cost_comparison.png')]:
        content=path.read_text(encoding='utf-8')
        if marker in content:
            start=content.index(marker);end=content.index('## 评分异常与使用范围',start)
            content=content[:start]+section.replace('COST_IMAGE',image)+'\n'+content[end:]
        else:
            content=content.replace('## 评分异常与使用范围',section.replace('COST_IMAGE',image)+'\n## 评分异常与使用范围')
        path.write_text(content,encoding='utf-8')
    save(folder/'figure-provenance.json',{'benchmark_sha256':hashlib.sha256((folder/'benchmark.json').read_bytes()).hexdigest(),
        'plot_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'software':{'matplotlib':matplotlib.__version__},'paid_model_requests':0,'conclusion':conclusion})
    print(conclusion)


if __name__=='__main__':main()
