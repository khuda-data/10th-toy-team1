"""공통 모델 학습과 하이퍼파라미터 탐색."""

from .train import train_model
from .tune import tune_model

__all__ = [
    "FirstStageModelResult",
    "first_stage_summary",
    "run_first_stage_modeling",
    "run_global_cv_modeling",
    "save_first_stage_oof_predictions",
    "save_first_stage_artifacts",
    "save_modeling_artifacts",
    "load_first_stage_best_params",
    "load_stage_fold_f1",
    "RefinementSearchResult",
    "RefinedModelResult",
    "boundary_flags",
    "count_grid_combinations",
    "refinement_config",
    "run_lr_refinement",
    "run_xgb_refinement_stage_a",
    "run_xgb_refinement_stage_b",
    "run_xgb_refinement_stage_c",
    "save_final_tuning_artifacts",
    "stage3_parameter_comparison",
    "train_model",
    "tune_model",
]


def __getattr__(name: str):
    """Stage 1 exports are lazy-loaded to avoid the model/evaluation import cycle."""
    if name in {
        "FirstStageModelResult",
        "first_stage_summary",
        "run_first_stage_modeling",
        "run_global_cv_modeling",
        "save_first_stage_oof_predictions",
        "save_first_stage_artifacts",
        "save_modeling_artifacts",
        "load_first_stage_best_params",
        "load_stage_fold_f1",
    }:
        from .first_stage import (
            FirstStageModelResult,
            first_stage_summary,
            run_first_stage_modeling,
            run_global_cv_modeling,
            save_first_stage_oof_predictions,
            save_first_stage_artifacts,
            save_modeling_artifacts,
            load_first_stage_best_params,
            load_stage_fold_f1,
        )

        return {
            "FirstStageModelResult": FirstStageModelResult,
            "first_stage_summary": first_stage_summary,
            "run_first_stage_modeling": run_first_stage_modeling,
            "run_global_cv_modeling": run_global_cv_modeling,
            "save_first_stage_oof_predictions": save_first_stage_oof_predictions,
            "save_first_stage_artifacts": save_first_stage_artifacts,
            "save_modeling_artifacts": save_modeling_artifacts,
            "load_first_stage_best_params": load_first_stage_best_params,
            "load_stage_fold_f1": load_stage_fold_f1,
        }[name]
    if name in {
        "RefinementSearchResult", "RefinedModelResult", "boundary_flags", "count_grid_combinations",
        "refinement_config", "run_lr_refinement", "run_xgb_refinement_stage_a",
        "run_xgb_refinement_stage_b", "run_xgb_refinement_stage_c", "save_final_tuning_artifacts",
        "stage3_parameter_comparison",
    }:
        from .final_tuning import (
            RefinementSearchResult,
            RefinedModelResult,
            boundary_flags,
            count_grid_combinations,
            refinement_config,
            run_lr_refinement,
            run_xgb_refinement_stage_a,
            run_xgb_refinement_stage_b,
            run_xgb_refinement_stage_c,
            save_final_tuning_artifacts,
            stage3_parameter_comparison,
        )

        return {
            "RefinementSearchResult": RefinementSearchResult,
            "RefinedModelResult": RefinedModelResult,
            "boundary_flags": boundary_flags,
            "count_grid_combinations": count_grid_combinations,
            "refinement_config": refinement_config,
            "run_lr_refinement": run_lr_refinement,
            "run_xgb_refinement_stage_a": run_xgb_refinement_stage_a,
            "run_xgb_refinement_stage_b": run_xgb_refinement_stage_b,
            "run_xgb_refinement_stage_c": run_xgb_refinement_stage_c,
            "save_final_tuning_artifacts": save_final_tuning_artifacts,
            "stage3_parameter_comparison": stage3_parameter_comparison,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
