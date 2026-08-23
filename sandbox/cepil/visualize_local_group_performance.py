"""로컬 직군 6개 모델 성능 비교 시각화.

실행:
    python sandbox/cepil/visualize_local_group_performance.py

출력:
    sandbox/cepil/figures/local_group_performance.png  ← 4개 차트 한 장
    sandbox/cepil/figures/local_group_feature_importance.png  ← 그룹별 feature importance

의존:
    pip install matplotlib  (seaborn 불필요)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Windows 터미널 한글 깨짐 방지
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd

# ── 경로 설정 ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
MODELING_DIR = ROOT / "data/result/baseline_42features/modeling"
OUT_DIR = Path(__file__).parent / "figures"
OUT_DIR.mkdir(exist_ok=True)

# ── 직군 정보 (cepil 제공 2026-08-23, group3→group3_2 수정 2026-08-23) ────
GROUPS = {
    "group1": "경영·사무·금융",
    "group2": "연구·공학·산업기술",
    "group3_2": "교육·법률·사회·공공",
    "group4": "보건·의료",
    "group5": "예술·디자인·방송·스포츠",
    "group6": "서비스·영업·판매·운송",
}
GROUP_KEYS = list(GROUPS.keys())
GROUP_LABELS = [f"G{i+1}\n{v}" for i, v in enumerate(GROUPS.values())]
GROUP_LABELS_SHORT = [f"G{i+1} {v}" for i, v in enumerate(GROUPS.values())]

# ── 한글 폰트 설정 ─────────────────────────────────────────────────────────
def _set_korean_font() -> None:
    """Windows/Mac/Linux에서 한글 폰트를 자동으로 찾아 설정한다."""
    candidates = ["Malgun Gothic", "AppleGothic", "NanumGothic", "NanumBarunGothic",
                  "Noto Sans CJK KR", "DejaVu Sans"]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False

_set_korean_font()

# ── 색상 팔레트 ────────────────────────────────────────────────────────────
# 성능 수준별: 낮음=주황, 보통=하늘, 양호=초록, 주의=회색
COLORS = ["#E07B39", "#5BA4CF", "#E07B39", "#4BAE8A", "#4BAE8A", "#9E9E9E"]

# ═══════════════════════════════════════════════════════════════════════════
# 1. 데이터 로드
# ═══════════════════════════════════════════════════════════════════════════
def load_summary() -> pd.DataFrame:
    """6개 그룹의 best candidate (최고 F1) 행만 모은다."""
    rows = []
    for gkey in GROUP_KEYS:
        path = MODELING_DIR / f"stage_4_local_{gkey}" / "final_test_summary.csv"
        df = pd.read_csv(path)
        best = df.loc[df["test_f1"].idxmax()].copy()
        best["group"] = gkey
        best["group_label"] = GROUPS[gkey]
        rows.append(best)
    return pd.DataFrame(rows).reset_index(drop=True)


def load_ci() -> pd.DataFrame:
    """6개 그룹 best candidate의 Bootstrap CI를 모은다."""
    rows = []
    for gkey in GROUP_KEYS:
        path = MODELING_DIR / f"stage_4_local_{gkey}" / "final_test_bootstrap_ci.csv"
        df = pd.read_csv(path)
        # summary의 best candidate과 동일한 candidate를 선택
        summary_path = MODELING_DIR / f"stage_4_local_{gkey}" / "final_test_summary.csv"
        summary = pd.read_csv(summary_path)
        best_candidate = summary.loc[summary["test_f1"].idxmax(), "candidate"]
        ci_row = df[df["candidate"] == best_candidate].iloc[0].copy()
        ci_row["group"] = gkey
        rows.append(ci_row)
    return pd.DataFrame(rows).reset_index(drop=True)


def load_confusion_matrices() -> dict[str, dict]:
    """6개 그룹 confusion matrix를 불러온다. [[TN,FP],[FN,TP]] 형식."""
    result = {}
    for gkey in GROUP_KEYS:
        path = MODELING_DIR / f"stage_4_local_{gkey}" / "final_test_confusion_matrices.json"
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        # best candidate 찾기
        summary_path = MODELING_DIR / f"stage_4_local_{gkey}" / "final_test_summary.csv"
        summary = pd.read_csv(summary_path)
        best_candidate = summary.loc[summary["test_f1"].idxmax(), "candidate"]
        result[gkey] = data[best_candidate]
    return result


def load_importance(model: str = "xgboost") -> dict[str, pd.DataFrame]:
    """6개 그룹 permutation importance를 불러온다."""
    prefix = "xgboost" if model == "xgboost" else "logistic_regression"
    result = {}
    for gkey in GROUP_KEYS:
        path = MODELING_DIR / f"stage_4_local_{gkey}" / f"{prefix}_final_permutation_importance.csv"
        result[gkey] = pd.read_csv(path)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# 2. 메인 차트 (4-in-1)
# ═══════════════════════════════════════════════════════════════════════════
def plot_main(summary: pd.DataFrame, ci: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("로컬 직군별 모델 성능 비교 (stage_4 baseline_42features)",
                 fontsize=15, fontweight="bold", y=0.98)

    x = np.arange(len(GROUP_KEYS))
    width = 0.55

    # ── (1,1) F1 + Bootstrap CI ────────────────────────────────────────────
    ax = axes[0, 0]
    f1_vals = summary["test_f1"].values
    ci_lower = ci["ci95_lower"].values
    ci_upper = ci["ci95_upper"].values
    err_lo = f1_vals - ci_lower
    err_hi = ci_upper - f1_vals

    bars = ax.bar(x, f1_vals, width=width, color=COLORS, alpha=0.85, zorder=3)
    ax.errorbar(x, f1_vals, yerr=[err_lo, err_hi],
                fmt="none", color="#333333", capsize=6, linewidth=1.5, zorder=4)

    # 수치 라벨
    for i, (bar, val) in enumerate(zip(bars, f1_vals)):
        ax.text(bar.get_x() + bar.get_width() / 2, val + err_hi[i] + 0.01,
                f"{val:.3f}", ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.axhline(0.5, color="gray", linestyle="--", linewidth=1, alpha=0.6, label="F1=0.5 기준선")
    ax.set_xticks(x)
    ax.set_xticklabels(GROUP_LABELS, fontsize=8)
    ax.set_ylim(0, 0.85)
    ax.set_ylabel("F1 Score")
    ax.set_title("① F1 Score + Bootstrap 95% CI", fontweight="bold")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3, zorder=0)
    ax.set_axisbelow(True)

    # ── (1,2) ROC-AUC & Average Precision ─────────────────────────────────
    ax = axes[0, 1]
    roc = summary["test_roc_auc"].values
    ap  = summary["test_average_precision"].values

    ax.bar(x - 0.2, roc, width=0.35, color=COLORS, alpha=0.85, label="ROC-AUC", zorder=3)
    ax.bar(x + 0.2, ap,  width=0.35, color=COLORS, alpha=0.45, label="Avg Precision", zorder=3,
           edgecolor=[c for c in COLORS], linewidth=1.2)

    for i in range(len(x)):
        ax.text(x[i] - 0.2, roc[i] + 0.01, f"{roc[i]:.3f}", ha="center", va="bottom", fontsize=8)
        ax.text(x[i] + 0.2, ap[i]  + 0.01, f"{ap[i]:.3f}",  ha="center", va="bottom", fontsize=8)

    ax.axhline(0.5, color="gray", linestyle="--", linewidth=1, alpha=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(GROUP_LABELS, fontsize=8)
    ax.set_ylim(0, 0.9)
    ax.set_ylabel("Score")
    ax.set_title("② ROC-AUC vs Average Precision", fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3, zorder=0)
    ax.set_axisbelow(True)

    # ── (2,1) Precision / Recall / Accuracy ───────────────────────────────
    ax = axes[1, 0]
    prec = summary["test_precision"].values
    rec  = summary["test_recall"].values
    acc  = summary["test_accuracy"].values

    ax.plot(x, prec, "o-", color="#E07B39", linewidth=2, markersize=7, label="Precision")
    ax.plot(x, rec,  "s-", color="#5BA4CF", linewidth=2, markersize=7, label="Recall")
    ax.plot(x, acc,  "^-", color="#4BAE8A", linewidth=2, markersize=7, label="Accuracy")

    for i in range(len(x)):
        ax.text(x[i], prec[i] - 0.025, f"{prec[i]:.2f}", ha="center", fontsize=7, color="#E07B39")
        ax.text(x[i], rec[i]  + 0.012, f"{rec[i]:.2f}",  ha="center", fontsize=7, color="#5BA4CF")

    ax.set_xticks(x)
    ax.set_xticklabels(GROUP_LABELS, fontsize=8)
    ax.set_ylim(0.2, 1.0)
    ax.set_ylabel("Score")
    ax.set_title("③ Precision / Recall / Accuracy 추이", fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    # ── (2,2) 표본 크기 & 양성률 ──────────────────────────────────────────
    ax = axes[1, 1]
    n_test   = summary["test_rows"].values
    pos_rate = summary["positive_rate"].values * 100

    ax2 = ax.twinx()
    bars2 = ax.bar(x, n_test, width=width, color=COLORS, alpha=0.6, zorder=3, label="n (test)")
    line2 = ax2.plot(x, pos_rate, "D--", color="#8B4513", linewidth=2,
                     markersize=8, label="양성률(%)", zorder=5)

    for i, (bar, n) in enumerate(zip(bars2, n_test)):
        ax.text(bar.get_x() + bar.get_width()/2, n + 3, str(n),
                ha="center", va="bottom", fontsize=9, fontweight="bold")
    for i, r in enumerate(pos_rate):
        ax2.text(x[i], r + 1.0, f"{r:.1f}%", ha="center", va="bottom",
                 fontsize=8, color="#8B4513")

    ax.set_xticks(x)
    ax.set_xticklabels(GROUP_LABELS, fontsize=8)
    ax.set_ylabel("Test 표본 수 (명)")
    ax2.set_ylabel("양성률 (%)")
    ax2.set_ylim(0, 80)
    ax.set_title("④ 표본 크기 & 양성률(취업률)", fontweight="bold")
    lines = [mpatches.Patch(color=COLORS[0], alpha=0.6, label="n (test)"), line2[0]]
    ax.legend(handles=lines, fontsize=9)
    ax.grid(axis="y", alpha=0.3, zorder=0)
    ax.set_axisbelow(True)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = OUT_DIR / "local_group_performance.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"저장: {out}")
    plt.close()


# ═══════════════════════════════════════════════════════════════════════════
# 3. Feature Importance 비교 (XGB, 상위 10개)
# ═══════════════════════════════════════════════════════════════════════════
def plot_importance(importance: dict[str, pd.DataFrame]) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("그룹별 XGBoost Feature Importance (Permutation, Top 10)",
                 fontsize=14, fontweight="bold", y=0.98)

    for idx, (gkey, label) in enumerate(GROUPS.items()):
        ax = axes[idx // 3][idx % 3]
        df = importance[gkey].copy()

        # 양수/음수 구분
        top10 = df.head(10).copy()
        bar_colors = ["#4BAE8A" if v >= 0 else "#E07B39" for v in top10["importance_mean"]]

        y_pos = np.arange(len(top10))
        ax.barh(y_pos, top10["importance_mean"], color=bar_colors, alpha=0.85)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(top10["feature"], fontsize=8)
        ax.invert_yaxis()
        ax.set_title(f"G{idx+1} {label}", fontweight="bold", fontsize=10)
        ax.set_xlabel("Importance (F1 drop)")
        ax.grid(axis="x", alpha=0.3)

        # 수치 표시
        for i, (val, err) in enumerate(zip(top10["importance_mean"], top10["importance_std"])):
            ha = "left" if val >= 0 else "right"
            offset = 0.001 if val >= 0 else -0.001
            ax.text(val + offset, i, f"{val:.3f}", va="center", ha=ha, fontsize=7)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    out = OUT_DIR / "local_group_feature_importance.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"저장: {out}")
    plt.close()


# ═══════════════════════════════════════════════════════════════════════════
# 4. Confusion Matrix 시각화
# ═══════════════════════════════════════════════════════════════════════════
def plot_confusion(cm_data: dict[str, list]) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(14, 9))
    fig.suptitle("그룹별 Confusion Matrix (최적 모델, threshold=0.5)",
                 fontsize=14, fontweight="bold", y=0.98)

    for idx, (gkey, label) in enumerate(GROUPS.items()):
        ax = axes[idx // 3][idx % 3]
        cm = np.array(cm_data[gkey])  # [[TN, FP], [FN, TP]]

        im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
        ax.set_title(f"G{idx+1} {label}", fontweight="bold", fontsize=9)
        ax.set_xlabel("예측")
        ax.set_ylabel("실제")
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["미취업(0)", "취업(1)"])
        ax.set_yticklabels(["미취업(0)", "취업(1)"])

        thresh = cm.max() / 2
        for i in range(2):
            for j in range(2):
                label_text = {(0,0): "TN", (0,1): "FP", (1,0): "FN", (1,1): "TP"}[(i,j)]
                color = "white" if cm[i, j] > thresh else "black"
                ax.text(j, i, f"{label_text}\n{cm[i, j]}",
                        ha="center", va="center", fontsize=11,
                        fontweight="bold", color=color)

        # Precision / Recall 표시
        tn, fp, fn, tp = cm[0,0], cm[0,1], cm[1,0], cm[1,1]
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec  = tp / (tp + fn) if (tp + fn) > 0 else 0
        ax.set_xlabel(f"예측   |  Precision={prec:.2f}  Recall={rec:.2f}")

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    out = OUT_DIR / "local_group_confusion_matrix.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"저장: {out}")
    plt.close()


# ═══════════════════════════════════════════════════════════════════════════
# 실행
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("데이터 로딩 중...")
    summary    = load_summary()
    ci         = load_ci()
    cm_data    = load_confusion_matrices()
    importance = load_importance(model="xgboost")

    print("차트 생성 중...")
    plot_main(summary, ci)
    plot_importance(importance)
    plot_confusion(cm_data)

    print("\n[완료] 저장 위치:")
    print(f"   {OUT_DIR / 'local_group_performance.png'}")
    print(f"   {OUT_DIR / 'local_group_feature_importance.png'}")
    print(f"   {OUT_DIR / 'local_group_confusion_matrix.png'}")
