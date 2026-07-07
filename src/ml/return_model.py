"""Train return-prediction models and build model-driven factor scores."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.research.forward_returns import build_factor_forward_returns


FEATURE_COLUMNS = [
    "value_score",
    "quality_score",
    "growth_score",
    "momentum_score",
    "low_volatility_score",
    "composite_score",
    "return_6m",
    "return_12m_ex_1m",
    "volatility_1y",
    "max_drawdown_1y",
]
TARGET_COLUMN = "excess_forward_1m_return"


def run_ml_return_experiment(
    *,
    factor_scores_path: str | Path = "data/features/integrated_factor_scores_2007_2026.csv",
    price_path: str | Path = "data/raw/price/prices_2007_2026.csv",
    target_output_path: str | Path = "data/features/ml_forward_return_dataset.csv",
    prediction_output_path: str | Path = "outputs/ml/ml_return_predictions.csv",
    selected_factor_output_path: str | Path = "data/features/ml_predicted_factor_scores_2007_2026.csv",
    metrics_output_path: str | Path = "outputs/tables/ml_model_metrics.csv",
    split_summary_output_path: str | Path = "outputs/tables/ml_dataset_split_summary.csv",
    report_output_path: str | Path = "outputs/reports/ML_Return_Prediction_Experiment.md",
    split_scheme: str = "regime_period",
) -> dict[str, pd.DataFrame | str]:
    """Run a leakage-aware train/validation/test return prediction experiment."""
    targets = build_factor_forward_returns(
        factor_scores_path=factor_scores_path,
        price_path=price_path,
        output_path=target_output_path,
    )
    dataset = _prepare_dataset(targets, split_scheme=split_scheme)
    if dataset.empty:
        raise ValueError("No usable ML dataset rows after target/feature filtering.")

    metric_rows = []
    prediction_frames = []

    train = dataset[dataset["research_split"] == "train"].copy()
    if train.empty:
        raise ValueError("Training split is empty.")

    models = _model_specs(train)
    fitted_models = {}
    x_train = train[FEATURE_COLUMNS]
    y_train = train[TARGET_COLUMN]
    for model_name, model in models.items():
        model.fit(x_train, y_train)
        fitted_models[model_name] = model
        for split_name in ["train", "validation", "test"]:
            split = dataset[dataset["research_split"] == split_name].copy()
            if split.empty:
                continue
            split_predictions = model.predict(split[FEATURE_COLUMNS])
            metric_rows.append(_evaluate_predictions(split, split_predictions, model_name))

            prediction_frame = split[
                [
                    "ticker",
                    "name",
                    "signal_date",
                    "research_split",
                    "split_scheme",
                    TARGET_COLUMN,
                    *FEATURE_COLUMNS,
                ]
            ].copy()
            prediction_frame["model_name"] = model_name
            prediction_frame["predicted_excess_forward_1m_return"] = split_predictions
            prediction_frames.append(prediction_frame)

    metrics = pd.DataFrame(metric_rows).sort_values(["model_name", "research_split"])
    predictions = pd.concat(prediction_frames, ignore_index=True)
    selected_model_name = _select_model(metrics)
    selected_factors = _build_selected_factor_scores(
        predictions,
        selected_model_name=selected_model_name,
    )
    split_summary = _build_split_summary(dataset)

    _write_csv(targets, target_output_path)
    _write_csv(predictions, prediction_output_path)
    _write_csv(selected_factors, selected_factor_output_path)
    _write_csv(metrics, metrics_output_path)
    _write_csv(split_summary, split_summary_output_path)
    _write_report(
        report_output_path,
        metrics=metrics,
        split_summary=split_summary,
        selected_model_name=selected_model_name,
        selected_factors=selected_factors,
        split_scheme=split_scheme,
    )
    return {
        "targets": targets,
        "dataset": dataset,
        "metrics": metrics,
        "predictions": predictions,
        "selected_factors": selected_factors,
        "selected_model_name": selected_model_name,
        "split_summary": split_summary,
    }


def _prepare_dataset(targets: pd.DataFrame, *, split_scheme: str = "regime_period") -> pd.DataFrame:
    frame = targets.copy()
    frame["ticker"] = frame["ticker"].astype("string").str.zfill(6)
    frame["signal_date"] = pd.to_datetime(frame["signal_date"])
    frame = _assign_signal_split(frame, split_scheme=split_scheme)
    for column in FEATURE_COLUMNS + [TARGET_COLUMN]:
        if column not in frame.columns:
            frame[column] = np.nan
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["feature_count"] = frame[FEATURE_COLUMNS].notna().sum(axis=1)
    frame = frame.dropna(subset=[TARGET_COLUMN])
    frame = frame[frame["feature_count"] >= 3].copy()
    return frame.sort_values(["signal_date", "ticker"])


def _assign_signal_split(frame: pd.DataFrame, *, split_scheme: str = "regime_period") -> pd.DataFrame:
    output = frame.copy()
    dates = pd.to_datetime(output["signal_date"])
    if split_scheme in {"chronological_801010", "801010", "8:1:1"}:
        valid_dates = pd.Index(sorted(dates.dropna().unique()))
        if len(valid_dates) < 10:
            raise ValueError("Not enough signal dates for chronological 8:1:1 split.")
        train_end = pd.Timestamp(valid_dates[max(0, int(len(valid_dates) * 0.8) - 1)])
        validation_end = pd.Timestamp(
            valid_dates[max(int(len(valid_dates) * 0.8), int(len(valid_dates) * 0.9) - 1)]
        )
        output["research_split"] = "test"
        output.loc[dates <= train_end, "research_split"] = "train"
        output.loc[
            (dates > train_end) & (dates <= validation_end),
            "research_split",
        ] = "validation"
        output.loc[dates.isna(), "research_split"] = "unknown"
        output["split_scheme"] = "chronological_801010"
        return output

    output["research_split"] = "test"
    output.loc[dates <= pd.Timestamp("2016-12-31"), "research_split"] = "train"
    output.loc[
        (dates >= pd.Timestamp("2017-01-01"))
        & (dates <= pd.Timestamp("2021-12-31")),
        "research_split",
    ] = "validation"
    output.loc[dates.isna(), "research_split"] = "unknown"
    output["split_scheme"] = "regime_period"
    return output


def _model_specs(train: pd.DataFrame) -> dict[str, object]:
    return {
        "ridge_linear": RidgeReturnModel(alpha=10.0),
        "composite_baseline": CompositeBaselineModel(train),
    }


class RidgeReturnModel:
    """Small numpy-based ridge regression with train-only preprocessing."""

    def __init__(self, alpha: float = 10.0):
        self.alpha = alpha
        self.medians: pd.Series | None = None
        self.means: pd.Series | None = None
        self.stds: pd.Series | None = None
        self.coef_: np.ndarray | None = None

    def fit(self, x: pd.DataFrame, y: pd.Series) -> "RidgeReturnModel":
        self.medians = x.median(numeric_only=True).fillna(0.0)
        filled = x.fillna(self.medians)
        self.means = filled.mean()
        self.stds = filled.std(ddof=0).replace(0.0, 1.0).fillna(1.0)
        z = ((filled - self.means) / self.stds).to_numpy(dtype=float)
        design = np.column_stack([np.ones(len(z)), z])
        penalty = np.eye(design.shape[1]) * self.alpha
        penalty[0, 0] = 0.0
        self.coef_ = np.linalg.pinv(design.T @ design + penalty) @ design.T @ y.to_numpy()
        return self

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        if self.coef_ is None or self.medians is None or self.means is None or self.stds is None:
            raise ValueError("Model is not fitted.")
        filled = x.fillna(self.medians)
        z = ((filled - self.means) / self.stds).to_numpy(dtype=float)
        design = np.column_stack([np.ones(len(z)), z])
        return design @ self.coef_


class CompositeBaselineModel:
    """Scale the existing composite score to expected excess return units."""

    def __init__(self, train: pd.DataFrame):
        self.scale = 0.0
        self.intercept = 0.0
        self._fit_from_train(train)

    def _fit_from_train(self, train: pd.DataFrame) -> None:
        x = pd.to_numeric(train["composite_score"], errors="coerce").fillna(0.0).to_numpy()
        y = pd.to_numeric(train[TARGET_COLUMN], errors="coerce").fillna(0.0).to_numpy()
        variance = float(np.var(x))
        self.scale = float(np.cov(x, y, ddof=0)[0, 1] / variance) if variance > 0 else 0.0
        self.intercept = float(np.mean(y) - self.scale * np.mean(x))

    def fit(self, x: pd.DataFrame, y: pd.Series) -> "CompositeBaselineModel":
        return self

    def predict(self, x: pd.DataFrame) -> np.ndarray:
        composite = pd.to_numeric(x["composite_score"], errors="coerce").fillna(0.0).to_numpy()
        return self.intercept + self.scale * composite


def _evaluate_predictions(
    split: pd.DataFrame,
    predictions: np.ndarray,
    model_name: str,
) -> dict[str, object]:
    actual = split[TARGET_COLUMN].to_numpy()
    residual = actual - predictions
    monthly_rank_ic = (
        pd.DataFrame(
            {
                "signal_date": split["signal_date"].to_numpy(),
                "actual": actual,
                "prediction": predictions,
            }
        )
        .groupby("signal_date", group_keys=False)
        .apply(_rank_ic_for_month, include_groups=False)
    )
    return {
        "model_name": model_name,
        "research_split": split["research_split"].iloc[0],
        "rows": int(len(split)),
        "months": int(split["signal_date"].nunique()),
        "rmse": float(np.sqrt(np.mean((actual - predictions) ** 2))),
        "mae": float(np.mean(np.abs(actual - predictions))),
        "prediction_mean": float(np.mean(predictions)),
        "actual_mean": float(np.mean(actual)),
        "direction_hit_rate": float((np.sign(actual) == np.sign(predictions)).mean()),
        "mean_rank_ic": float(monthly_rank_ic.mean()),
        "median_rank_ic": float(monthly_rank_ic.median()),
        "positive_rank_ic_rate": float((monthly_rank_ic > 0).mean()),
        "residual_std": float(np.std(residual)),
    }


def _rank_ic_for_month(month: pd.DataFrame) -> float:
    if len(month) < 5:
        return np.nan
    return float(month["actual"].rank().corr(month["prediction"].rank()))


def _select_model(metrics: pd.DataFrame) -> str:
    validation = metrics[metrics["research_split"] == "validation"].copy()
    if validation.empty:
        return str(metrics.sort_values("mean_rank_ic", ascending=False)["model_name"].iloc[0])
    validation = validation.sort_values(
        ["mean_rank_ic", "direction_hit_rate", "rmse"],
        ascending=[False, False, True],
    )
    return str(validation["model_name"].iloc[0])


def _build_selected_factor_scores(
    predictions: pd.DataFrame,
    *,
    selected_model_name: str,
) -> pd.DataFrame:
    selected = predictions[predictions["model_name"] == selected_model_name].copy()
    selected["composite_score"] = selected["predicted_excess_forward_1m_return"]
    selected["ml_model_name"] = selected_model_name
    selected["factor_scope"] = "ml_predicted_1m_excess_return"
    columns = [
        "ticker",
        "name",
        "signal_date",
        "research_split",
        "split_scheme",
        "composite_score",
        "predicted_excess_forward_1m_return",
        TARGET_COLUMN,
        "value_score",
        "quality_score",
        "growth_score",
        "momentum_score",
        "low_volatility_score",
        "ml_model_name",
        "factor_scope",
    ]
    return selected[[column for column in columns if column in selected.columns]].sort_values(
        ["signal_date", "composite_score"],
        ascending=[True, False],
    )


def _build_split_summary(dataset: pd.DataFrame) -> pd.DataFrame:
    return (
        dataset.groupby("research_split", as_index=False)
        .agg(
            rows=("ticker", "size"),
            tickers=("ticker", "nunique"),
            months=("signal_date", "nunique"),
            min_signal_date=("signal_date", "min"),
            max_signal_date=("signal_date", "max"),
            mean_target_1m_excess=(TARGET_COLUMN, "mean"),
            mean_feature_count=("feature_count", "mean"),
        )
        .sort_values("min_signal_date")
    )


def _write_csv(frame: pd.DataFrame, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8-sig")


def _write_report(
    path: str | Path,
    *,
    metrics: pd.DataFrame,
    split_summary: pd.DataFrame,
    selected_model_name: str,
    selected_factors: pd.DataFrame,
    split_scheme: str,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    latest_date = selected_factors["signal_date"].max()
    latest = selected_factors[selected_factors["signal_date"] == latest_date].head(10)

    lines = [
        "# ML Return Prediction Experiment",
        "",
        "## 1. Objective",
        "",
        "Predict next-month excess return using only signal-date factor information, "
        "then convert the prediction into a top-N model portfolio score.",
        "",
        "## 2. Split Design",
        "",
        f"- Split scheme: `{split_scheme}`",
        "- Random split is not used because financial time-series experiments must preserve chronology.",
        "- `regime_period`: Train 2007~2016, Validation 2017~2021, Test 2022~2026",
        "- `chronological_801010`: monthly signal dates sorted by time, then split 80%/10%/10%",
        "",
        _markdown_table(split_summary),
        "",
        "## 3. Model Selection",
        "",
        f"Selected model: `{selected_model_name}`",
        "",
        _markdown_table(metrics),
        "",
        "## 4. Latest Model Candidates",
        "",
        _markdown_table(
            latest[
            [
                "ticker",
                "name",
                "signal_date",
                "composite_score",
                "predicted_excess_forward_1m_return",
                "research_split",
            ]
            ]
        ),
        "",
        "## 5. Interpretation",
        "",
        "The validation split chooses the model before test evaluation. "
        "The test split must therefore be read as the out-of-sample check of the selected model. "
        "The candidate list is a quantitative screening output, not investment advice.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    display = frame.copy()
    for column in display.columns:
        if pd.api.types.is_datetime64_any_dtype(display[column]):
            display[column] = display[column].dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(lambda value: f"{value:.4f}")
    headers = [str(column) for column in display.columns]
    rows = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in display.iterrows():
        values = [str(row[column]) for column in display.columns]
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)
