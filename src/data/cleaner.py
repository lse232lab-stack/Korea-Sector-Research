"""Shared data cleaning utilities."""

from __future__ import annotations


def standardize_ticker(ticker: object) -> str:
    """Return a six-character Korean stock ticker."""
    return str(ticker).strip().zfill(6)
