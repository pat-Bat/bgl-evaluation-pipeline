DEFAULT_PROGRESS = {"enabled": True, "leave": True, "mininterval": 1}
DEFAULT_LOG_LEVEL = "debug"

SEED = 42

GLUCOSE_FILTER = None
# GLUCOSE_FILTER = {"gte": 70, "lte": 240}

SPLIT_RATIO = {"test_ratio": 0, "val_ratio": 0.15}
RANDOM_SPLIT_RATIO = {"test_ratio": 0.20, "val_ratio": 0.10}

BASE_DL_PARAMS = {
    "seed": SEED,
    "epochs": 1000,
}

XGB_PARAMS = {
    "objective": "reg:squarederror",
    "tree_method": "hist",
    "eval_metric": "rmse",
    "seed": SEED,
}

XGB_MFCC_FULL_PARAMS = {
    "objective": "reg:squarederror",
    "tree_method": "hist",
    "eval_metric": "rmse",
    "seed": SEED,
    "max_depth": 4,
    "learning_rate": 0.119972,
    "colsample_bytree": 0.828334,
    "subsample": 0.937768,
    "min_child_weight": 19,
    "reg_lambda": 0.005877,
    "reg_alpha": 0.000199,
    "gamma": 1.322527,
}

DATASETS = {
        "vitaldb_50": {
            "type": "vitaldb_extractor",
            "config": {
                "max_cases": 0,
                "minute_window": 16,
                "target_fs": 50,
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
        "vitaldb_70": {
            "type": "vitaldb_extractor",
            "config": {
                "max_cases": 0,
                "minute_window": 16,
                "target_fs": 70,
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
        "vitaldb_100": {
            "type": "vitaldb_extractor",
            "config": {
                "max_cases": 0,
                "minute_window": 16,
                "target_fs": 100,
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
                "vitaldb_test": {
            "type": "vitaldb_extractor",
            "config": {
                "max_cases": 30,          # nur die ersten 30 OPs mit Glukose
                "minute_window": 16,
                "target_fs": 100,
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
        "must": {
            "type": "must_extractor",
            "config": {
                "input_dir": "../Data/must_v4/must_dataset/PPG_Dataset",
                "target_fs": 100,
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": True,
        },
        "berki": {
                    "type": "berki_extractor",
                    "config": {
                        "input_dir": "../Data/berki/wfdb_data",
                        "target_fs": 100,
                        "progress": DEFAULT_PROGRESS,
                        "log_level": DEFAULT_LOG_LEVEL,
                    },
                    "force_overwrite": True,
                },
        "mimic3": {
                            "type": "mimic3_extractor",
                            "config": {
                                "input_dir": "../Data/mimic3",
                                "target_fs": 100,
                                "progress": DEFAULT_PROGRESS,
                                "log_level": DEFAULT_LOG_LEVEL,
                                "max_nan_frac": 0.05,
                            },
                            "force_overwrite": True,
                        },
    }
PROCESSORS = {
        "zeynali_proc": {
            "type": "zeynali_processor",
            "config": {
                "quality_threshold": 1.0,
                "lowcut_hz": 0.5,
                "highcut_hz": 8.0,
                "filter_order": 3,
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
        "sen_gupta_proc": {
            "type": "sen_gupta_processor",
            "config": {
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
        "alghlayini_proc": {
            "type": "alghlayini_processor",
            "config": {
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
        "islam_proc": {
            "type": "islam_processor",
            "config": {
                "als_lam": 1e5,
                "als_p": 0.01,
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
        "prabha_proc": {
            "type": "prabha_processor",
            "config": {
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
        "global_mean_proc": {
            "type": "global_mean_processor",
            "config": {
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
    }
BUILDERS = {
        "sen_gupta_builder": {
            "type": "sen_gupta_builder",
            "config": {
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
        "islam_builder": {
            "type": "islam_builder",
            "config": {
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
        "islam_builder_must": {
            "type": "islam_builder",
            "config": {
                "window_sec": 10,
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
        "zeynali_builder": {
            "type": "zeynali_beat_segmentation",
            "config": {
                "window_sec": 1.0,
                "similarity_threshold": 0.85,
                "distance_threshold": 0.8,
                "height_threshold": 20,
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
        "zeynali_builder_must": {
            "type": "zeynali_beat_segmentation",
            "config": {
                "window_sec": 1.0,
                "similarity_threshold": 0.85,
                "distance_threshold": 0.8,
                "adaptive_height_threshold": True,
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
        "alghlayini_builder": {
            "type": "alghlayini_builder",
            "config": {
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
        "alghlayini_builder_must": {
            "type": "alghlayini_builder",
            "config": {
                "window_sec": 10.0,
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
        "prabha_builder": {
            "type": "prabha_tabular_features",
            "config": {
                "window_sec": 5.0,
                "n_frames": 8,
                "n_mels": 26,
                "n_mfcc": 13,
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
        "global_mean_builder": {
            "type": "global_mean_builder",
            "config": {
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
        "rf_builder": {
            "type": "rf_builder",
            "config": {
                "window_sec": 10,
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
            },
            "force_overwrite": False,
        },
    }
MODELS = {
        "xgb": {
            "type": "xgboost",
            "config": {
                "params": XGB_PARAMS,
                "target_range": GLUCOSE_FILTER,
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
                "show_fold_metrics": False,
            },
            "force_overwrite": False,
        },
        "xgb_notemp_nospo": {
            "type": "xgboost",
            "config": {
                "params": XGB_PARAMS,
                "target_range": GLUCOSE_FILTER,
                "exclude_features": ["temp_mean", "spo2_mean"],
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
                "show_fold_metrics": False,
            },
            "force_overwrite": False,
        },
        "xgb_std_feat": {
            "type": "xgboost",
            "config": {
                "params": XGB_PARAMS,
                "target_range": GLUCOSE_FILTER,
                # "use_tuner": False,
                "exclude_features": ["gender", "age", "temp_mean"],
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
                "show_fold_metrics": False,
            },
            "force_overwrite": False,
        },
        "xgb_std_feat_nospo": {
            "type": "xgboost",
            "config": {
                "params": XGB_PARAMS,
                "target_range": GLUCOSE_FILTER,
                "exclude_features": ["gender", "age", "temp_mean", "spo2_mean"],
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
                "show_fold_metrics": False,
            },
            "force_overwrite": False,
        },
        "pls": {
            "type": "pls",
            "config": {
                "target_range": GLUCOSE_FILTER,
                "params": {
                    "seed": SEED,
                    "n_components": 2,
                    "scale": True,
                },
            },
            "force_overwrite": False,
        },
        "mean_baseline": {
            "type": "mean",
            "config": {
                "target_range": GLUCOSE_FILTER,
                "params": {
                    "seed": SEED,
                },
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
                "show_fold_metrics": False,
            },
            "force_overwrite": False,
        },
        "rf": {
            "type": "random_forest",
            "config": {
                "target_range": GLUCOSE_FILTER,
                "params": {
                    "seed": SEED,
                    "n_estimators": 300,
                    "max_depth": None,
                    "min_samples_leaf": 1,
                },
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
                "show_fold_metrics": True,
            },
            "force_overwrite": False,
        },
        "tiny": {
            "type": "tiny_cnn",
            "config": {
                "params": BASE_DL_PARAMS,
                "target_range": GLUCOSE_FILTER,
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
                "show_fold_metrics": True,
                "fit_verbose": 1,
            },
            "force_overwrite": False,
        },
        "resnet": {
            "type": "resnet34",
            "config": {
                "params": BASE_DL_PARAMS,
                "target_range": GLUCOSE_FILTER,
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
                "show_fold_metrics": False,
                "fit_verbose": 1,
            },
            "force_overwrite": False,
        },
        "xgb_mfcc_paper": {
            "type": "xgboost",
            "config": {
                "params": XGB_PARAMS,
                "target_range": GLUCOSE_FILTER,
                "feature_selection_top_k": 5,
                "feature_selection_importance_type": "gain",
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
                "show_fold_metrics": False,
            },
            "force_overwrite": False,
        },
        "xgb_mfcc_full": {
            "type": "xgboost",
            "config": {
                "params": XGB_MFCC_FULL_PARAMS,
                "target_range": GLUCOSE_FILTER,
                "progress": DEFAULT_PROGRESS,
                "log_level": DEFAULT_LOG_LEVEL,
                "show_fold_metrics": False,
            },
            "force_overwrite": False,
        },
    }

ZEYNALI_PLAN = [
    {
        "datasets": ["vitaldb_100"],
        "processors": ["zeynali_proc"],
        "builders": ["zeynali_builder"],
        "models": ["resnet"],
        "mode": "train_cv",
        "force_train": False,
    },
    {
        "datasets": ["must"],
        "processors": ["zeynali_proc"],
        "builders": ["zeynali_builder_must"],
        "models": ["resnet"],
        "mode": "train_cv",
        "force_train": False,
    },

        {
        "datasets": ["vitaldb_100"],
        "processors": ["zeynali_proc"],
        "builders": ["zeynali_builder"],
        "models": ["resnet"],
        "mode": "train_cv_multi_session",
        "force_train": False,
    },

        {
        "datasets": ["must"],
        "processors": ["zeynali_proc"],
        "builders": ["zeynali_builder_must"],
        "models": ["resnet"],
        "mode": "train_cv_multi_session",
        "force_train": False,
    },

        {
        "datasets": ["vitaldb_100"],
        "processors": ["zeynali_proc"],
        "builders": ["zeynali_builder"],
        "models": ["resnet"],
        "mode": "train_cv_random",
        "force_train": False,
    },

        {
        "datasets": ["must"],
        "processors": ["zeynali_proc"],
        "builders": ["zeynali_builder_must"],
        "models": ["resnet"],
        "mode": "train_cv_random",
        "force_train": False,
    },
    
    {
        "datasets": ["must"],
        "processors": ["zeynali_proc"],
        "builders": ["zeynali_builder_must"],
        "mode": "eval",
        "eval_model_config": {
            "dataset": "vitaldb_100",
            "processor": "zeynali_proc",
            "builder": "zeynali_builder",
            "models": ["resnet"],
            "mode": "train_single",
            "split_ratio": SPLIT_RATIO,
        },
        "force_train": False,
    },

]

GUPTA_PLAN = [
    {
        "datasets": ["vitaldb_100"],
        "processors": ["sen_gupta_proc"],
        "builders": ["sen_gupta_builder"],
        "models": [
            "xgb_std_feat",
        ],
        "mode": "train_cv",
        "force_train": False,
    },
    {
        "datasets": ["must"],
        "processors": ["sen_gupta_proc"],
        "builders": ["sen_gupta_builder"],
        "models": [
            "xgb_std_feat_nospo",
        ],
        "mode": "train_cv",
        "force_train": False,
    },

    {
        "datasets": ["vitaldb_100"],
        "processors": ["sen_gupta_proc"],
        "builders": ["sen_gupta_builder"],
        "models": [
            "xgb_std_feat",
        ],
        "mode": "train_cv_multi_session",
        "force_train": False,
    },

    {
        "datasets": ["must"],
        "processors": ["sen_gupta_proc"],
        "builders": ["sen_gupta_builder"],
        "models": [
            "xgb_std_feat_nospo",
        ],
        "mode": "train_cv_multi_session",
        "force_train": False,
    },

    {
        "datasets": ["vitaldb_100"],
        "processors": ["sen_gupta_proc"],
        "builders": ["sen_gupta_builder"],
        "models": [
            "xgb_std_feat",
        ],
        "mode": "train_cv_random",
        "force_train": False,
    },
    {
        "datasets": ["must"],
        "processors": ["sen_gupta_proc"],
        "builders": ["sen_gupta_builder"],
        "models": [
            "xgb_std_feat_nospo",
        ],
        "mode": "train_cv_random",
        "force_train": False,
    },

    {
        "datasets": ["must"],
        "processors": ["sen_gupta_proc"],
        "builders": ["sen_gupta_builder"],
        "mode": "eval",
        "eval_model_config": {
            "dataset": "vitaldb_100",
            "processor": "sen_gupta_proc",
            "builder": "sen_gupta_builder",
            "models": ["xgb_std_feat_nospo"],
            "mode": "train_single",
            "split_ratio": SPLIT_RATIO,
        },
        "force_train": False,
    },

]

ISLAM_PLAN = [
    {
        "datasets": ["vitaldb_100"],
        "processors": ["islam_proc"],
        "builders": ["islam_builder"],
        "models": ["pls"],
        "mode": "train_cv",
        "force_train": False,
    },
    {
        "datasets": ["must"],
        "processors": ["islam_proc"],
        "builders": ["islam_builder_must"],
        "models": ["pls"],
        "mode": "train_cv",
        "force_train": False,
    },
    {
        "datasets": ["vitaldb_100"],
        "processors": ["islam_proc"],
        "builders": ["islam_builder"],
        "models": ["pls"],
        "mode": "train_cv_multi_session",
        "force_train": False,
    },
    {
        "datasets": ["must"],
        "processors": ["islam_proc"],
        "builders": ["islam_builder_must"],
        "models": ["pls"],
        "mode": "train_cv_multi_session",
        "force_train": False,
    },
    {
        "datasets": ["vitaldb_100"],
        "processors": ["islam_proc"],
        "builders": ["islam_builder"],
        "models": ["pls"],
        "mode": "train_cv_random",
        "force_train": False,
    },
    {
        "datasets": ["must"],
        "processors": ["islam_proc"],
        "builders": ["islam_builder_must"],
        "models": ["pls"],
        "mode": "train_cv_random",
        "force_train": False,
    },

    {
        "datasets": ["vitaldb_100"],
        "processors": ["islam_proc"],
        "builders": ["islam_builder"],
        "models": ["pls"],
        "mode": "train_single",
        "split_ratio": SPLIT_RATIO,
        "force_train": False,
    },

    {
        "datasets": ["must"],
        "processors": ["islam_proc"],
        "builders": ["islam_builder_must"],
        "mode": "eval",
        "eval_model_config": {
            "dataset": "vitaldb_100",
            "processor": "islam_proc",
            "builder": "islam_builder",
            "models": ["pls"],
            "mode": "train_single",
            "split_ratio": SPLIT_RATIO,
        },
        "force_train": False,
    },

]

ALGHLAYINI_PLAN = [
    {
        "datasets": ["vitaldb_100"],
        "processors": ["alghlayini_proc"],
        "builders": ["alghlayini_builder"],
        "models": ["tiny"],
        "mode": "train_cv",
        "force_train": False,
    },
    {
        "datasets": ["must"],
        "processors": ["alghlayini_proc"],
        "builders": ["alghlayini_builder_must"],
        "models": ["tiny"],
        "mode": "train_cv",
        "force_train": False,
    },
    {
        "datasets": ["vitaldb_100"],
        "processors": ["alghlayini_proc"],
        "builders": ["alghlayini_builder"],
        "models": ["tiny"],
        "mode": "train_cv_multi_session",
        "force_train": False,
    },
    {
        "datasets": ["must"],
        "processors": ["alghlayini_proc"],
        "builders": ["alghlayini_builder_must"],
        "models": ["tiny"],
        "mode": "train_cv_multi_session",
        "force_train": False,
    },

    {
        "datasets": ["vitaldb_100"],
        "processors": ["alghlayini_proc"],
        "builders": ["alghlayini_builder"],
        "models": ["tiny"],
        "mode": "train_cv_random",
        "force_train": False,
    },
    {
        "datasets": ["must"],
        "processors": ["alghlayini_proc"],
        "builders": ["alghlayini_builder_must"],
        "models": ["tiny"],
        "mode": "train_cv_random",
        "force_train": False,
    },

        {
        "datasets": ["vitaldb_100"],
        "processors": ["alghlayini_proc"],
        "builders": ["alghlayini_builder_must"],
        "models": ["tiny"],
        "mode": "train_single",
        "split_ratio": SPLIT_RATIO,
        "force_train": False,
    },

    {
        "datasets": ["must"],
        "processors": ["alghlayini_proc"],
        "builders": ["alghlayini_builder_must"],
        "mode": "eval",
        "eval_model_config": {
            "dataset": "vitaldb_100",
            "processor": "alghlayini_proc",
            "builder": "alghlayini_builder_must",
            "models": ["tiny"],
            "mode": "train_single",
            "split_ratio": SPLIT_RATIO,
        },
        "force_train": False,
    },
]

PRABHA_PLAN = [
    {
        "datasets": ["vitaldb_100"],
        "processors": ["prabha_proc"],
        "builders": ["prabha_builder"],
        "models": ["xgb_mfcc_paper"],
        "mode": "train_cv",
        "force_train": False,
    },
    {
        "datasets": ["must"],
        "processors": ["prabha_proc"],
        "builders": ["prabha_builder"],
        "models": ["xgb_mfcc_paper"],
        "mode": "train_cv",
        "force_train": False,
    },
    {
        "datasets": ["vitaldb_100"],
        "processors": ["prabha_proc"],
        "builders": ["prabha_builder"],
        "models": ["xgb_mfcc_paper"],
        "mode": "train_cv_multi_session",
        "force_train": False,
    },
    {
        "datasets": ["must"],
        "processors": ["prabha_proc"],
        "builders": ["prabha_builder"],
        "models": ["xgb_mfcc_paper"],
        "mode": "train_cv_multi_session",
        "force_train": False,
    },
    {
        "datasets": ["vitaldb_100"],
        "processors": ["prabha_proc"],
        "builders": ["prabha_builder"],
        "models": [
            "xgb_mfcc_paper",
        ],
        "mode": "train_cv_random",
        "force_train": False,
    },
    {
        "datasets": ["must"],
        "processors": ["prabha_proc"],
        "builders": ["prabha_builder"],
        "models": [
            "xgb_mfcc_paper",
        ],
        "mode": "train_cv_random",
        "force_train": False,
    },
    {
        "datasets": ["vitaldb_100"],
        "processors": ["prabha_proc"],
        "builders": ["prabha_builder"],
        "models": ["xgb_mfcc_paper"],
        "mode": "train_single",
        "split_ratio": SPLIT_RATIO,
        "force_train": False,
    },
    {
        "datasets": ["must"],
        "processors": ["prabha_proc"],
        "builders": ["prabha_builder"],
        "mode": "eval",
        "eval_model_config": {
            "dataset": "vitaldb_100",
            "processor": "prabha_proc",
            "builder": "prabha_builder",
            "models": ["xgb_mfcc_paper"],
            "mode": "train_single",
            "split_ratio": SPLIT_RATIO,
        },
        "force_train": False,
    }
]

GLOBAL_MEAN_PLAN = [
    {
        "datasets": ["vitaldb_100", "must"],
        "processors": ["global_mean_proc"],
        "builders": ["global_mean_builder"],
        "models": ["mean_baseline"],
        "mode": "train_cv",
        "force_train": False,
    },
    {
        "datasets": ["vitaldb_100", "must"],
        "processors": ["global_mean_proc"],
        "builders": ["global_mean_builder"],
        "models": ["mean_baseline"],
        "mode": "train_cv_multi_session",
        "force_train": False,
    },
    {
        "datasets": ["vitaldb_100", "must"],
        "processors": ["global_mean_proc"],
        "builders": ["global_mean_builder"],
        "models": ["mean_baseline"],
        "mode": "train_cv_random",
        "force_train": False,
    },

       {
        "datasets": ["vitaldb_100"],
        "processors": ["global_mean_proc"],
        "builders": ["global_mean_builder"],
        "models": ["mean_baseline"],
        "mode": "train_single",
        "split_ratio": SPLIT_RATIO,
        "force_train": False,
    },
    
    {
        "datasets": ["must"],
        "processors": ["global_mean_proc"],
        "builders": ["global_mean_builder"],
        "mode": "eval",
        "eval_model_config": {
            "dataset": "vitaldb_100",
            "processor": "global_mean_proc",
            "builder": "global_mean_builder",
            "models": ["mean_baseline"],
            "mode": "train_single",
            "split_ratio": SPLIT_RATIO,
        },
        "force_train": False,
    }
]


ALL_PLANS = (
    ISLAM_PLAN
    + GUPTA_PLAN
    + ALGHLAYINI_PLAN
    + PRABHA_PLAN
    + ZEYNALI_PLAN
    + GLOBAL_MEAN_PLAN
)
TEST_PLAN = [
    {
        "datasets": ["berki"],
        "processors": ["global_mean_proc"],
        "builders": ["global_mean_builder"],
        "models": ["mean_baseline"],
        "mode": "train_cv",
        "force_train": False,
    },
    {
        "datasets": ["berki"],
        "processors": ["sen_gupta_proc"],
        "builders": ["sen_gupta_builder"],
        "models": ["xgb_std_feat_nospo"],
        "mode": "train_cv",
        "force_train": False,
    },
]
PIPELINE = {
    "name": "bench",
    "artifacts_root": "artifacts/bench",
    "datasets": DATASETS,
    "processors": PROCESSORS,
    "builders": BUILDERS,
    "models": MODELS,
    "plan": TEST_PLAN,
}

