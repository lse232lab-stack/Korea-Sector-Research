"""Chart generation for the research report."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def save_price_chart(
    price_path: str | Path = "data/raw/price/prices.csv",
    *,
    output_path: str | Path = "outputs/charts/price_index_2025.svg",
) -> Path:
    """Save a normalized price index chart for fetched tickers."""
    prices = pd.read_csv(price_path, dtype={"ticker": "string"}, parse_dates=["date"])
    if prices.empty:
        raise ValueError("Price data is empty.")

    prices = prices.sort_values(["ticker", "date"])
    prices["price_index"] = prices.groupby("ticker")["adj_close"].transform(
        lambda series: series / series.iloc[0] * 100
    )
    pivot = prices.pivot(index="date", columns="ticker", values="price_index")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_build_svg_line_chart(pivot), encoding="utf-8")
    return output_path


def save_charts():
    """Save currently available report charts."""
    return {"price_index": save_price_chart()}


def _build_svg_line_chart(pivot: pd.DataFrame) -> str:
    width = 960
    height = 520
    margin_left = 70
    margin_right = 30
    margin_top = 55
    margin_bottom = 55
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    min_value = float(pivot.min().min())
    max_value = float(pivot.max().max())
    value_pad = (max_value - min_value) * 0.08 or 1
    y_min = min_value - value_pad
    y_max = max_value + value_pad

    dates = list(pivot.index)
    colors = ["#2563eb", "#dc2626", "#059669", "#7c3aed", "#ea580c"]

    def x_pos(index: int) -> float:
        if len(dates) == 1:
            return margin_left
        return margin_left + index / (len(dates) - 1) * plot_width

    def y_pos(value: float) -> float:
        return margin_top + (y_max - value) / (y_max - y_min) * plot_height

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="30" text-anchor="middle" font-family="Arial" font-size="20" font-weight="700">Normalized Price Index</text>',
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{height - margin_bottom}" stroke="#111827" stroke-width="1"/>',
        f'<line x1="{margin_left}" y1="{height - margin_bottom}" x2="{width - margin_right}" y2="{height - margin_bottom}" stroke="#111827" stroke-width="1"/>',
    ]

    for i in range(5):
        value = y_min + i / 4 * (y_max - y_min)
        y = y_pos(value)
        elements.append(
            f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>'
        )
        elements.append(
            f'<text x="{margin_left - 10}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial" font-size="12" fill="#374151">{value:.0f}</text>'
        )

    for idx in [0, len(dates) // 2, len(dates) - 1]:
        date = dates[idx]
        x = x_pos(idx)
        label = date.strftime("%Y-%m-%d")
        elements.append(
            f'<text x="{x:.1f}" y="{height - 20}" text-anchor="middle" font-family="Arial" font-size="12" fill="#374151">{label}</text>'
        )

    for color_index, ticker in enumerate(pivot.columns):
        series = pivot[ticker].dropna()
        points = []
        for date, value in series.items():
            idx = dates.index(date)
            points.append(f"{x_pos(idx):.1f},{y_pos(float(value)):.1f}")
        color = colors[color_index % len(colors)]
        elements.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="2.2" points="{" ".join(points)}"/>'
        )
        legend_x = margin_left + color_index * 115
        legend_y = height - 38
        elements.append(
            f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x + 22}" y2="{legend_y}" stroke="{color}" stroke-width="3"/>'
        )
        elements.append(
            f'<text x="{legend_x + 28}" y="{legend_y + 4}" font-family="Arial" font-size="13" fill="#111827">{ticker}</text>'
        )

    elements.append("</svg>")
    return "\n".join(elements)
