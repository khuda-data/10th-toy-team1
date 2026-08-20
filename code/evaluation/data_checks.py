"""Global 모델링 전 Dataset·split 점검용 요약표."""

from __future__ import annotations

import pandas as pd

from code.contracts import DatasetBundle


def summarize_global_modeling_inputs(
    train_bundle: DatasetBundle,
    test_bundle: DatasetBundle,
    *,
    expected_features: list[str],
) -> dict[str, pd.DataFrame]:
    """Notebook이 표시할 표본·Target·baseline_year·Feature·결측 점검표를 만든다."""
    overlap = set(train_bundle.groups.astype("string")) & set(test_bundle.groups.astype("string"))
    feature_presence = pd.DataFrame(
        {
            "feature": expected_features,
            "in_train": [feature in train_bundle.X.columns for feature in expected_features],
            "in_test": [feature in test_bundle.X.columns for feature in expected_features],
        }
    )
    sample_rows = []
    target_rows = []
    baseline_frames = []
    missing_frames = []
    for split_name, bundle in (("train", train_bundle), ("test", test_bundle)):
        target_rate = float(bundle.y.mean())
        sample_rows.append(
            {
                "split": split_name,
                "n_person_periods": len(bundle.y),
                "n_sampids": bundle.groups.nunique(),
                "target_positive_rate": target_rate,
            }
        )
        target_rows.extend(
            [
                {"split": split_name, "target": 0, "count": int((bundle.y == 0).sum()), "rate": float((bundle.y == 0).mean())},
                {"split": split_name, "target": 1, "count": int((bundle.y == 1).sum()), "rate": float((bundle.y == 1).mean())},
            ]
        )
        baseline = pd.DataFrame({"baseline_year": bundle.metadata["baseline_year"], "target": bundle.y})
        baseline_summary = baseline.groupby("baseline_year", as_index=False).agg(
            n_person_periods=("target", "size"), employment_transition_rate=("target", "mean")
        )
        baseline_summary.insert(0, "split", split_name)
        baseline_frames.append(baseline_summary)
        missing = bundle.X.isna().mean().rename("missing_rate").rename_axis("feature").reset_index()
        missing.insert(0, "split", split_name)
        missing_frames.append(missing)

    return {
        "sample_summary": pd.DataFrame(sample_rows),
        "target_summary": pd.DataFrame(target_rows),
        "baseline_summary": pd.concat(baseline_frames, ignore_index=True),
        "feature_presence": feature_presence,
        "missingness": pd.concat(missing_frames, ignore_index=True),
        "split_checks": pd.DataFrame(
            [
                {"check": "train_test_sampid_overlap", "value": len(overlap)},
                {"check": "expected_feature_count", "value": len(expected_features)},
                {"check": "missing_expected_features", "value": int((~feature_presence["in_train"] | ~feature_presence["in_test"]).sum())},
            ]
        ),
    }
