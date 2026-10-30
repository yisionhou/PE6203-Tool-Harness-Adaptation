"""Create publication-ready cost figures and a report section from measured data."""
from pathlib import Path
import sys
import hashlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from member3.analyze import read,save
from member3_extension.cost_report import render_cost_section,integrate_cost_section


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
    section, conclusion = render_cost_section(data, formal, 'COST_IMAGE')
    (folder/'cost-report.md').write_text(section.replace('COST_IMAGE','update_cost_comparison.png'),encoding='utf-8')
    for path,image in [(ROOT/'docs/member3-report-section.md','../member3/evidence/formal/cost-comparison/update_cost_comparison.png'),
                       (folder.parent/'summary.md','cost-comparison/update_cost_comparison.png')]:
        if not path.exists():
            continue  # Figures can be generated before the first full report.
        content = integrate_cost_section(path.read_text(encoding='utf-8'), section.replace('COST_IMAGE', image))
        path.write_text(content,encoding='utf-8')
    save(folder/'figure-provenance.json',{'benchmark_sha256':hashlib.sha256((folder/'benchmark.json').read_bytes()).hexdigest(),
        'figure_sha256':{name:hashlib.sha256((folder/name).read_bytes()).hexdigest()
            for name in ('update_cost_comparison.png','update_cost_comparison.svg')},
        'plot_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'cost_report_sha256':hashlib.sha256((ROOT/'member3_extension/cost_report.py').read_bytes()).hexdigest(),
        'software':{'matplotlib':matplotlib.__version__},'paid_model_requests':0,'conclusion':conclusion})
    print(conclusion)


if __name__=='__main__':main()
