"""노트북의 모든 차트를 한 번에 실행해서 PNG로 저장하는 스크립트."""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # 화면 없이 파일로만 저장
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd

ROOT         = Path(__file__).resolve().parents[2]
MODELING_DIR = ROOT / 'data/result/baseline_42features/modeling'
OUT_DIR      = Path(__file__).parent / 'figures'
OUT_DIR.mkdir(exist_ok=True)

GROUPS = {
    'group1': '경영·사무·금융',
    'group2': '연구·공학·산업기술',
    'group3_2': '교육·법률·사회·공공',
    'group4': '보건·의료',
    'group5': '예술·디자인·방송·스포츠',
    'group6': '서비스·영업·판매·운송',
}
GROUP_KEYS  = list(GROUPS.keys())
SHORT       = [f'G{i+1}' for i in range(6)]
LABELS_2L   = [f'G{i+1}\n{v}' for i, v in enumerate(GROUPS.values())]

C = {
    'primary'   : '#0066cc',
    'primary_d' : '#0071e3',
    'ink'       : '#1d1d1f',
    'ink_m80'   : '#333333',
    'ink_m48'   : '#7a7a7a',
    'canvas'    : '#ffffff',
    'parchment' : '#f5f5f7',
    'hairline'  : '#e0e0e0',
    'tile_dark' : '#272729',
    'on_dark'   : '#ffffff',
    'sky_blue'  : '#2997ff',
}
BAR_COLORS = ['#E07B39', C['sky_blue'], '#E07B39',
              C['primary'], C['primary_d'], C['ink_m48']]

FEAT_KO = {
    'age'                          : 'age (나이)',
    'student_status'               : 'student_status (재학상태)',
    'graduation_prep_experience'   : 'graduation_prep_exp',
    'major_group'                  : 'major_group (전공계열)',
    'months_since_graduation'      : 'months_since_graduation',
    'gender'                       : 'gender (성별)',
    'region_5'                     : 'region_5 (거주지역)',
    'currently_preparing_exam'     : 'currently_preparing_exam',
    'baseline_year'                : 'baseline_year (조사연도)',
    'recent_job_search'            : 'recent_job_search',
    'education_level'              : 'education_level (학력)',
    'has_employment_certificate'   : 'has_employment_cert',
    'has_major_related_certificate': 'has_major_related_cert',
    'prep_effort_08'               : 'prep_effort_08',
    'prep_effort_04'               : 'prep_effort_04',
    'prep_effort_03'               : 'prep_effort_03',
    'nonemployment_type'           : 'nonemployment_type',
    'recent_employment_prep'       : 'recent_employment_prep',
    'student_type'                 : 'student_type',
    'university_type'              : 'university_type',
    'has_certificate'              : 'has_certificate',
}

# ── 한글 폰트 ──────────────────────────────────────────────────────────────
candidates = ['Malgun Gothic', 'AppleGothic', 'NanumGothic', 'NanumBarunGothic']
available  = {f.name for f in fm.fontManager.ttflist}
for name in candidates:
    if name in available:
        plt.rcParams['font.family'] = name
        break
plt.rcParams['axes.unicode_minus'] = False

plt.rcParams.update({
    'axes.facecolor'    : C['canvas'],
    'figure.facecolor'  : C['parchment'],
    'axes.edgecolor'    : C['hairline'],
    'axes.spines.top'   : False,
    'axes.spines.right' : False,
    'axes.spines.left'  : False,
    'axes.spines.bottom': True,
    'axes.grid'         : True,
    'axes.grid.axis'    : 'y',
    'grid.color'        : C['hairline'],
    'grid.linewidth'    : 0.7,
    'grid.alpha'        : 0.8,
    'xtick.color'       : C['ink_m48'],
    'ytick.color'       : C['ink_m48'],
    'xtick.bottom'      : False,
    'ytick.left'        : False,
    'text.color'        : C['ink'],
})

# ── 데이터 로드 ────────────────────────────────────────────────────────────
def load_summary():
    rows = []
    for gkey in GROUP_KEYS:
        df   = pd.read_csv(MODELING_DIR / f'stage_4_local_{gkey}/final_test_summary.csv')
        best = df.loc[df['test_f1'].idxmax()].copy()
        best['group'] = gkey
        rows.append(best)
    return pd.DataFrame(rows).reset_index(drop=True)

def load_ci(summary):
    rows = []
    for gkey in GROUP_KEYS:
        df   = pd.read_csv(MODELING_DIR / f'stage_4_local_{gkey}/final_test_bootstrap_ci.csv')
        cand = summary.loc[summary['group'] == gkey, 'candidate'].values[0]
        row  = df[df['candidate'] == cand].iloc[0].copy()
        row['group'] = gkey
        rows.append(row)
    return pd.DataFrame(rows).reset_index(drop=True)

def load_confusion(summary):
    result = {}
    for gkey in GROUP_KEYS:
        with open(MODELING_DIR / f'stage_4_local_{gkey}/final_test_confusion_matrices.json', encoding='utf-8') as f:
            data = json.load(f)
        cand = summary.loc[summary['group'] == gkey, 'candidate'].values[0]
        result[gkey] = np.array(data[cand])
    return result

def load_importance(model='xgboost'):
    prefix = 'xgboost' if model == 'xgboost' else 'logistic_regression'
    return {gkey: pd.read_csv(MODELING_DIR / f'stage_4_local_{gkey}/{prefix}_final_permutation_importance.csv')
            for gkey in GROUP_KEYS}

summary    = load_summary()
ci         = load_ci(summary)
cm_data    = load_confusion(summary)
importance = load_importance('xgboost')

x     = np.arange(6)
f1    = summary['test_f1'].values
roc   = summary['test_roc_auc'].values
ap    = summary['test_average_precision'].values
prec  = summary['test_precision'].values
rec   = summary['test_recall'].values
ci_lo = f1 - ci['ci95_lower'].values
ci_hi = ci['ci95_upper'].values - f1

# ═══════════════════════════════════════════════════════════════════════════
# Chart 1 — F1 + CI
# ═══════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(13, 6.5), facecolor=C['parchment'])
ax.set_facecolor(C['canvas'])
bars = ax.bar(x, f1, width=0.52, color=BAR_COLORS, alpha=0.88, zorder=3)
ax.errorbar(x, f1, yerr=[ci_lo, ci_hi],
            fmt='none', color=C['ink_m80'], capsize=7, capthick=1.8, linewidth=1.8, zorder=5)
for i, (v, hi) in enumerate(zip(f1, ci_hi)):
    ax.text(x[i], v+hi+0.018, f'{v:.3f}', ha='center',
            fontsize=11.5, fontweight='600', color=C['ink'])
for i, (v, lo) in enumerate(zip(f1, ci_lo)):
    ax.text(x[i], v-lo-0.022, f'CI {ci["ci95_lower"].values[i]:.3f}',
            ha='center', va='top', fontsize=8, color=C['ink_m48'])
ax.axhline(0.5, color=C['ink_m48'], linestyle='--', linewidth=1.2, alpha=0.7)
ax.text(5.55, 0.502, 'F1=0.5', fontsize=9, color=C['ink_m48'])
badges = ['낮음', '보통', '낮음', '양호', '양호', 'n 과소']
badge_c = ['#E07B39', C['sky_blue'], '#E07B39', C['primary'], C['primary_d'], C['ink_m48']]
for i, (b, bc) in enumerate(zip(badges, badge_c)):
    ax.text(x[i], 0.055, b, ha='center', fontsize=9, color=bc, fontweight='600')
ax.set_xticks(x)
ax.set_xticklabels(LABELS_2L, fontsize=10)
ax.set_ylim(0, 0.88)
ax.set_ylabel('F1 Score', fontsize=11, color=C['ink_m80'])
ax.set_title('직군별 F1 Score + Bootstrap 95% CI',
             fontsize=15, fontweight='600', color=C['ink'], pad=18, loc='left')
legend_items = [
    mpatches.Patch(color='#E07B39', alpha=0.88, label='낮음 (F1 < 0.5)'),
    mpatches.Patch(color=C['sky_blue'], alpha=0.88, label='보통'),
    mpatches.Patch(color=C['primary'], alpha=0.88, label='양호 (F1 >= 0.65)'),
    mpatches.Patch(color=C['ink_m48'], alpha=0.88, label='표본 과소'),
]
ax.legend(handles=legend_items, loc='upper right', framealpha=0.9,
          edgecolor=C['hairline'], fontsize=9)
fig.tight_layout(pad=2)
fig.savefig(OUT_DIR/'chart1_f1_ci.png', dpi=180, bbox_inches='tight', facecolor=C['parchment'])
plt.close()
print('Chart 1 저장완료')

# ═══════════════════════════════════════════════════════════════════════════
# Chart 2 — ROC-AUC & Avg Precision
# ═══════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(13, 6), facecolor=C['parchment'])
ax.set_facecolor(C['canvas'])
w = 0.34
ax.bar(x - w/2 - 0.02, roc, width=w, color=BAR_COLORS, alpha=0.90, zorder=3, label='ROC-AUC')
ax.bar(x + w/2 + 0.02, ap,  width=w, color=BAR_COLORS, alpha=0.42, zorder=3, label='Avg Precision',
       edgecolor=BAR_COLORS, linewidth=1.1)
for i in range(6):
    ax.text(x[i]-w/2-0.02, roc[i]+0.012, f'{roc[i]:.3f}', ha='center',
            fontsize=10, fontweight='600', color=C['ink'])
    ax.text(x[i]+w/2+0.02, ap[i]+0.012,  f'{ap[i]:.3f}', ha='center',
            fontsize=9.5, color=C['ink_m80'])
ax.axhline(0.5, color=C['ink_m48'], linestyle='--', linewidth=1.2, alpha=0.7)
ax.text(5.6, 0.502, 'Random\n= 0.5', fontsize=8, color=C['ink_m48'])
ax.set_xticks(x); ax.set_xticklabels(LABELS_2L, fontsize=10)
ax.set_ylim(0, 0.86); ax.set_ylabel('Score', fontsize=11, color=C['ink_m80'])
ax.set_title('ROC-AUC vs Average Precision', fontsize=15, fontweight='600',
             color=C['ink'], pad=18, loc='left')
ax.legend(loc='upper right', framealpha=0.9, edgecolor=C['hairline'], fontsize=10)
fig.tight_layout(pad=2)
fig.savefig(OUT_DIR/'chart2_roc_ap.png', dpi=180, bbox_inches='tight', facecolor=C['parchment'])
plt.close()
print('Chart 2 저장완료')

# ═══════════════════════════════════════════════════════════════════════════
# Chart 3 — Precision / Recall 선형
# ═══════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(13, 6), facecolor=C['parchment'])
ax.set_facecolor(C['canvas'])
ax.fill_between(x, prec, rec, alpha=0.07, color=C['primary'])
ax.plot(x, rec,  'o-', color=C['sky_blue'], lw=2.5, markersize=9,
        markeredgecolor=C['canvas'], markeredgewidth=1.5, zorder=4, label='Recall')
ax.plot(x, prec, 's-', color='#E07B39', lw=2.5, markersize=9,
        markeredgecolor=C['canvas'], markeredgewidth=1.5, zorder=4, label='Precision')
ax.plot(x, summary['test_accuracy'].values, '^--', color=C['ink_m48'],
        lw=1.5, markersize=7, alpha=0.7, zorder=3, label='Accuracy')
for i in range(6):
    ax.text(x[i]+0.08, rec[i]+0.015,  f'{rec[i]:.2f}', fontsize=10,
            color=C['sky_blue'], fontweight='600')
    ax.text(x[i]+0.08, prec[i]-0.03,  f'{prec[i]:.2f}', fontsize=10, color='#E07B39')
ax.annotate('G4 Recall 82%\n(보건·의료)', xy=(3, rec[3]),
            xytext=(3.4, rec[3]-0.14),
            arrowprops=dict(arrowstyle='->', color=C['primary'], lw=1.5,
                            connectionstyle='arc3,rad=-0.2'),
            fontsize=9, color=C['primary'], fontweight='600')
ax.set_xticks(x); ax.set_xticklabels(LABELS_2L, fontsize=10)
ax.set_ylim(0.2, 1.0); ax.set_ylabel('Score', fontsize=11, color=C['ink_m80'])
ax.set_title('Precision / Recall / Accuracy', fontsize=15, fontweight='600',
             color=C['ink'], pad=18, loc='left')
ax.legend(loc='upper left', framealpha=0.9, edgecolor=C['hairline'], fontsize=10)
fig.tight_layout(pad=2)
fig.savefig(OUT_DIR/'chart3_prec_rec.png', dpi=180, bbox_inches='tight', facecolor=C['parchment'])
plt.close()
print('Chart 3 저장완료')

# ═══════════════════════════════════════════════════════════════════════════
# Chart 4 — Confusion Matrix
# ═══════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 3, figsize=(17, 10), facecolor=C['parchment'])
fig.suptitle('Confusion Matrix  —  최적 모델 (threshold = 0.5)',
             fontsize=16, fontweight='600', color=C['ink'], y=0.97, x=0.05, ha='left')
for idx, (gkey, label) in enumerate(GROUPS.items()):
    ax  = axes[idx//3][idx%3]
    cm  = cm_data[gkey]
    col = BAR_COLORS[idx]
    for i in range(2):
        for j in range(2):
            bg = col if i==j else '#EBEBED'
            rect = FancyBboxPatch(
                (j+0.04, 1-i+0.04), 0.92, 0.92,
                boxstyle='round,pad=0.02',
                facecolor=bg, alpha=0.88 if i==j else 0.9,
                edgecolor=C['hairline'], linewidth=1,
                transform=ax.transData, zorder=2)
            ax.add_patch(rect)
            lmap = {(0,0):'TN', (0,1):'FP', (1,0):'FN', (1,1):'TP'}
            tc   = C['on_dark'] if i==j else C['ink_m80']
            ax.text(j+0.5, 1-i+0.64, lmap[(i,j)],
                    ha='center', va='center', fontsize=11, color=tc, alpha=0.75 if i!=j else 1.0)
            ax.text(j+0.5, 1-i+0.38, str(cm[i,j]),
                    ha='center', va='center', fontsize=22, fontweight='600', color=tc)
    tn,fp,fn,tp = cm[0,0],cm[0,1],cm[1,0],cm[1,1]
    pv = tp/(tp+fp) if tp+fp>0 else 0
    rv = tp/(tp+fn) if tp+fn>0 else 0
    ax.set_facecolor(C['canvas'])
    ax.set_xlim(0,2); ax.set_ylim(0,2)
    ax.set_xticks([0.5,1.5]); ax.set_yticks([0.5,1.5])
    ax.set_xticklabels(['미취업 예측','취업 예측'], fontsize=9.5)
    ax.set_yticklabels(['취업','미취업'], fontsize=9.5)
    ax.tick_params(left=False, bottom=False)
    ax.set_xlabel(f'Precision = {pv:.2f}   |   Recall = {rv:.2f}',
                  fontsize=10, color=C['ink_m80'], labelpad=8)
    ax.set_title(f'G{idx+1}  {label}', fontsize=12, fontweight='600',
                 color=C['ink'], pad=10, loc='left')
    ax.spines[:].set_visible(False); ax.grid(False)
    ax.axhline(1, color=C['canvas'], linewidth=3, zorder=3)
    ax.axvline(1, color=C['canvas'], linewidth=3, zorder=3)
    ax.text(-0.1, 1.5, '실제\n미취업', ha='right', va='center',
            fontsize=9, color=C['ink_m48'])
    ax.text(-0.1, 0.5, '실제\n취업',  ha='right', va='center',
            fontsize=9, color=C['ink_m48'])
fig.tight_layout(pad=2.5)
fig.savefig(OUT_DIR/'chart4_confusion.png', dpi=180, bbox_inches='tight', facecolor=C['parchment'])
plt.close()
print('Chart 4 저장완료')

# ═══════════════════════════════════════════════════════════════════════════
# Chart 5 — Feature Importance
# ═══════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 3, figsize=(20, 12), facecolor=C['parchment'])
fig.suptitle('XGBoost Feature Importance (Permutation, Top 10)',
             fontsize=16, fontweight='600', color=C['ink'], y=0.98, x=0.03, ha='left')
for idx, (gkey, glabel) in enumerate(GROUPS.items()):
    ax  = axes[idx//3][idx%3]
    df  = importance[gkey].head(10).copy()
    col = BAR_COLORS[idx]
    vals   = df['importance_mean'].values
    errs   = df['importance_std'].values
    feat   = [FEAT_KO.get(f, f) for f in df['feature']]
    yp     = np.arange(len(df))
    bc     = [col if v>=0 else '#CCCCCC' for v in vals]
    ax.set_facecolor(C['canvas'])
    ax.barh(yp, vals, color=bc, alpha=0.88,
            xerr=errs, error_kw={'ecolor':C['ink_m48'],'capsize':3,'linewidth':0.8}, zorder=3)
    ax.axvline(0, color=C['ink_m48'], linewidth=0.8, zorder=4)
    ax.set_yticks(yp); ax.set_yticklabels(feat, fontsize=8.2)
    ax.invert_yaxis()
    ax.set_title(f'G{idx+1}  {glabel}', fontsize=11.5, fontweight='600',
                 color=C['ink'], loc='left', pad=8)
    ax.set_xlabel('F1 drop (양수=유용, 음수=노이즈)', fontsize=8.5, color=C['ink_m48'])
    ax.tick_params(left=False)
    ax.spines['bottom'].set_color(C['hairline'])
    ax.grid(axis='x', alpha=0.4, color=C['hairline'])
    ax.grid(axis='y', visible=False)
    for i, v in enumerate(vals):
        ha  = 'left' if v>=0 else 'right'
        off = 0.0008 if v>=0 else -0.0008
        ax.text(v+off, i, f'{v:.3f}', va='center', ha=ha, fontsize=7.5,
                color=C['ink'] if v>=0 else C['ink_m48'])
fig.tight_layout(pad=2.5, h_pad=3.5)
fig.savefig(OUT_DIR/'chart5_importance.png', dpi=180, bbox_inches='tight', facecolor=C['parchment'])
plt.close()
print('Chart 5 저장완료')

# ═══════════════════════════════════════════════════════════════════════════
# Chart 6 — Dashboard PPT 1장 (16:9)
# ═══════════════════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(20, 11.25), facecolor=C['parchment'])
gs  = gridspec.GridSpec(2, 3, figure=fig,
                        left=0.06, right=0.97,
                        top=0.87, bottom=0.10,
                        hspace=0.58, wspace=0.30)
fig.text(0.06, 0.93,
         '로컬 직군별 모델 성능  —  종합 Dashboard',
         fontsize=18, fontweight='600', color=C['ink'])
fig.text(0.06, 0.905,
         'baseline_42features · stage_4 최종 평가  |  직군 분류: KECO 대분류 (cepil, 2026-08-23)',
         fontsize=10, color=C['ink_m48'])

# (0,0) F1
ax1 = fig.add_subplot(gs[0, 0]); ax1.set_facecolor(C['canvas'])
ax1.bar(x, f1, width=0.55, color=BAR_COLORS, alpha=0.88, zorder=3)
ax1.errorbar(x, f1, yerr=[ci_lo, ci_hi],
             fmt='none', color=C['ink_m80'], capsize=5, linewidth=1.5, zorder=5)
for i, (v, hi) in enumerate(zip(f1, ci_hi)):
    ax1.text(x[i], v+hi+0.02, f'{v:.3f}', ha='center',
             fontsize=9, fontweight='600', color=C['ink'])
ax1.axhline(0.5, color=C['ink_m48'], linestyle='--', lw=1, alpha=0.6)
ax1.set_xticks(x); ax1.set_xticklabels(SHORT, fontsize=9)
ax1.set_ylim(0, 0.85); ax1.set_title('F1 + 95% CI', fontsize=12,
                                       fontweight='600', color=C['ink'], loc='left')
ax1.spines['left'].set_visible(False); ax1.spines['bottom'].set_color(C['hairline'])

# (0,1) ROC-AUC
ax2 = fig.add_subplot(gs[0, 1]); ax2.set_facecolor(C['canvas'])
ax2.bar(x-0.18, roc, width=0.33, color=BAR_COLORS, alpha=0.90, zorder=3, label='ROC-AUC')
ax2.bar(x+0.18, ap,  width=0.33, color=BAR_COLORS, alpha=0.40, zorder=3, label='Avg Prec.',
        edgecolor=BAR_COLORS, linewidth=0.8)
for i in range(6):
    ax2.text(x[i]-0.18, roc[i]+0.012, f'{roc[i]:.3f}', ha='center',
             fontsize=8.5, fontweight='600', color=C['ink'])
ax2.axhline(0.5, color=C['ink_m48'], linestyle='--', lw=1, alpha=0.6)
ax2.set_xticks(x); ax2.set_xticklabels(SHORT, fontsize=9)
ax2.set_ylim(0, 0.85); ax2.set_title('ROC-AUC vs Avg Precision', fontsize=12,
                                       fontweight='600', color=C['ink'], loc='left')
ax2.legend(fontsize=8, framealpha=0.8)
ax2.spines['left'].set_visible(False); ax2.spines['bottom'].set_color(C['hairline'])

# (0,2) Prec/Rec
ax3 = fig.add_subplot(gs[0, 2]); ax3.set_facecolor(C['canvas'])
ax3.fill_between(x, prec, rec, alpha=0.06, color=C['primary'])
ax3.plot(x, rec,  'o-', color=C['sky_blue'], lw=2.2, markersize=7,
         markeredgecolor=C['canvas'], markeredgewidth=1.2, label='Recall')
ax3.plot(x, prec, 's-', color='#E07B39', lw=2.2, markersize=7,
         markeredgecolor=C['canvas'], markeredgewidth=1.2, label='Precision')
for i in range(6):
    ax3.text(x[i]+0.08, rec[i]+0.015,  f'{rec[i]:.2f}', fontsize=8,
             color=C['sky_blue'], fontweight='600')
    ax3.text(x[i]+0.08, prec[i]-0.03,  f'{prec[i]:.2f}', fontsize=8, color='#E07B39')
ax3.set_xticks(x); ax3.set_xticklabels(SHORT, fontsize=9)
ax3.set_ylim(0.2, 1.0); ax3.set_title('Precision / Recall', fontsize=12,
                                        fontweight='600', color=C['ink'], loc='left')
ax3.legend(fontsize=8, framealpha=0.8)
ax3.spines['left'].set_visible(False); ax3.spines['bottom'].set_color(C['hairline'])

# (1,0~2) Feature Importance 하이라이트 3개 (G3 vs G4 vs G5)
highlight = ['group3_2', 'group4', 'group5']
hi_titles = {
    'group3_2': 'G3  교육·법률·사회·공공  [낮음]',
    'group4': 'G4  보건·의료  [양호]',
    'group5': 'G5  예술·디자인·방송·스포츠  [양호]',
}
for ci_idx, gkey in enumerate(highlight):
    ax = fig.add_subplot(gs[1, ci_idx]); ax.set_facecolor(C['canvas'])
    df   = importance[gkey].head(10)
    vals = df['importance_mean'].values
    feat = [FEAT_KO.get(f, f) for f in df['feature']]
    yp   = np.arange(len(df))
    col  = BAR_COLORS[GROUP_KEYS.index(gkey)]
    bc   = [col if v>=0 else '#CCCCCC' for v in vals]
    ax.barh(yp, vals, color=bc, alpha=0.88, zorder=3)
    ax.axvline(0, color=C['ink_m48'], lw=0.8)
    ax.set_yticks(yp); ax.set_yticklabels(feat, fontsize=7.8)
    ax.invert_yaxis()
    ax.set_title(hi_titles[gkey], fontsize=10.5, fontweight='600',
                 color=C['ink'], loc='left')
    ax.set_xlabel('F1 drop', fontsize=8, color=C['ink_m48'])
    ax.tick_params(left=False)
    ax.spines['bottom'].set_color(C['hairline']); ax.spines['left'].set_visible(False)
    ax.grid(axis='x', alpha=0.3); ax.grid(axis='y', visible=False)
    for i, v in enumerate(vals):
        ha  = 'left' if v>=0 else 'right'
        off = 0.001 if v>=0 else -0.001
        ax.text(v+off, i, f'{v:.3f}', va='center', ha=ha,
                fontsize=7, color=C['ink_m48'])

fig.text(0.06, 0.035,
         '색상: 주황=낮음  하늘=보통  파랑=양호  회색=표본과소  |  '
         '하단 차트: G3(낮음) vs G4·G5(양호) 대조  |  '
         'Feature importance: 양수=예측에 유용, 음수=노이즈',
         fontsize=8.5, color=C['ink_m48'])

fig.savefig(OUT_DIR/'chart6_dashboard_ppt.png', dpi=180,
            bbox_inches='tight', facecolor=C['parchment'])
plt.close()
print('Chart 6 (PPT Dashboard) 저장완료')

print('\n--- 전체 완료 ---')
for f in sorted(OUT_DIR.glob('chart*.png')):
    print(f'  {f.name}  ({f.stat().st_size//1024} KB)')
