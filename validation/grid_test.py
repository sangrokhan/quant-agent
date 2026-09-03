"""Grid-testing helper: validate one strategy across parameters, volatility
regimes, and asset classes systematically.

Not a new backtest engine -- this orchestrates repeated calls into
validation/validators.py (which is itself a thin vectorbt wrapper) across a
cartesian grid, and aggregates the pass/fail results into one summary a
Research Agent loop iteration can log in a single knowledge_base entry.

Usage pattern (see RESEARCH_LOOP.md Step G):

    from grid_test import run_strategy_grid, GridSpec

    spec = GridSpec(
        param_grid={"bb_window": [15, 20, 25], "bb_std": [1.5, 2.0, 2.5]},
        symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]},
        vol_regime_splits=3,  # low/mid/high realized-vol terciles
    )
    result = run_strategy_grid(
        generate_returns_fn=strat.generate_returns,
        loader_fn_by_asset_class={"equity": load_equity, "crypto": load_crypto},
        spec=spec,
        start=datetime(2019, 1, 1), end=datetime(2026, 9, 1),
    )
    # result.summary() -> dict suitable for the knowledge_base "validators"/
    # "notes" fields: overall pass fraction, best/worst cell, per-asset-class
    # and per-vol-regime breakdowns.

This intentionally does NOT try to be exhaustive/fast (e.g. no parallelism,
no smart pruning) -- keep grids modest in Step G scoping (a handful of
parameter values x 2 asset classes x 3 vol terciles = dozens of cells, not
thousands) so one loop iteration finishes in reasonable time/token budget.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validation"))
from validators import check_max_drawdown, check_sharpe_ratio  # noqa: E402


@dataclass
class GridSpec:
    param_grid: Dict[str, List[Any]]
    symbols: Dict[str, List[str]]  # asset_class -> list of symbols
    vol_regime_splits: int = 3  # split the sample into N realized-vol terciles/quantiles
    min_sharpe: float = 1.0
    max_allowed_mdd: float = 0.25


@dataclass
class GridCellResult:
    params: Dict[str, Any]
    asset_class: str
    symbol: str
    vol_regime_label: str  # e.g. "low", "mid", "high"
    sharpe: Optional[float]
    sharpe_passed: bool
    mdd: Optional[float]
    mdd_passed: bool
    error: Optional[str] = None

    @property
    def passed(self) -> bool:
        return self.error is None and self.sharpe_passed and self.mdd_passed


@dataclass
class GridResult:
    cells: List[GridCellResult] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        total = len(self.cells)
        passed = sum(1 for c in self.cells if c.passed)
        by_asset_class: Dict[str, Dict[str, int]] = {}
        by_vol_regime: Dict[str, Dict[str, int]] = {}
        for c in self.cells:
            ac = by_asset_class.setdefault(c.asset_class, {"passed": 0, "total": 0})
            ac["total"] += 1
            ac["passed"] += int(c.passed)
            vr = by_vol_regime.setdefault(c.vol_regime_label, {"passed": 0, "total": 0})
            vr["total"] += 1
            vr["passed"] += int(c.passed)

        best = max(self.cells, key=lambda c: (c.sharpe if c.sharpe is not None else -999)) if self.cells else None
        worst = min(self.cells, key=lambda c: (c.sharpe if c.sharpe is not None else 999)) if self.cells else None

        return {
            "metric": "grid_test",
            "total_cells": total,
            "passed_cells": passed,
            "pass_fraction": (passed / total) if total else 0.0,
            "by_asset_class": by_asset_class,
            "by_vol_regime": by_vol_regime,
            "best_cell": None if best is None else {
                "params": best.params, "asset_class": best.asset_class,
                "symbol": best.symbol, "vol_regime": best.vol_regime_label,
                "sharpe": best.sharpe,
            },
            "worst_cell": None if worst is None else {
                "params": worst.params, "asset_class": worst.asset_class,
                "symbol": worst.symbol, "vol_regime": worst.vol_regime_label,
                "sharpe": worst.sharpe,
            },
        }


def _vol_regime_masks(price_df: pd.DataFrame, n_splits: int) -> Dict[str, pd.Series]:
    """Split the sample period into N realized-volatility regime labels
    (e.g. n_splits=3 -> "low"/"mid"/"high"), based on rolling 20-period
    realized vol of the UNDERLYING price series (not the strategy's own
    returns, which are mostly zero when flat and would make quantile
    splitting degenerate/fail for low-frequency strategies).
    """
    import math

    close = price_df.set_index("timestamp")["close"] if "timestamp" in price_df.columns else price_df["close"]
    daily_log_ret = (close / close.shift(1)).apply(
        lambda r: math.log(r) if r and r > 0 else None
    ).astype(float)
    realized_vol = daily_log_ret.rolling(20).std()

    labels = ["low", "mid", "high"] if n_splits == 3 else [f"q{i+1}" for i in range(n_splits)]
    try:
        quantile_bins = pd.qcut(realized_vol.dropna(), q=n_splits, labels=labels, duplicates="drop")
        quantile_bins = quantile_bins.reindex(realized_vol.index)
    except ValueError:
        # Not enough distinct values to split -- fall back to a single "all" bucket.
        return {"all": pd.Series(True, index=close.index)}

    masks = {}
    categories = quantile_bins.cat.categories if hasattr(quantile_bins, "cat") else labels
    for label in categories:
        masks[str(label)] = (quantile_bins == label).fillna(False)
    return masks


def run_strategy_grid(
    generate_returns_fn: Callable[..., pd.Series],
    loader_fn_by_asset_class: Dict[str, Callable[..., pd.DataFrame]],
    spec: GridSpec,
    start: datetime,
    end: datetime,
) -> GridResult:
    """Run generate_returns_fn across the full param x symbol x vol-regime grid.

    ``generate_returns_fn`` must accept a price DataFrame as its first
    positional arg and the grid's param names as keyword args (matching the
    strategy module's own ``generate_returns(price_df, **kwargs)`` contract
    -- see strategies/*.py for examples), and return a pd.Series of daily
    strategy returns.
    """
    result = GridResult()

    param_names = list(spec.param_grid.keys())
    param_combos = list(itertools.product(*[spec.param_grid[p] for p in param_names])) or [()]

    # Cache raw price data per (asset_class, symbol) -- fetched once, reused
    # across every param combo and vol-regime slice (data/loaders.py is
    # already cache-first, but this avoids repeat function-call overhead too).
    price_cache: Dict[Tuple[str, str], pd.DataFrame] = {}

    for asset_class, symbols in spec.symbols.items():
        loader = loader_fn_by_asset_class.get(asset_class)
        if loader is None:
            continue
        for symbol in symbols:
            key = (asset_class, symbol)
            if key not in price_cache:
                try:
                    price_cache[key] = loader(symbol, start, end)
                except Exception as exc:  # noqa: BLE001 - record and continue the grid
                    for combo in param_combos:
                        params = dict(zip(param_names, combo))
                        result.cells.append(GridCellResult(
                            params=params, asset_class=asset_class, symbol=symbol,
                            vol_regime_label="n/a", sharpe=None, sharpe_passed=False,
                            mdd=None, mdd_passed=False, error=f"data load failed: {exc}",
                        ))
                    continue

            price_df = price_cache[key]

            for combo in param_combos:
                params = dict(zip(param_names, combo))
                try:
                    full_returns = generate_returns_fn(price_df, **params)
                except Exception as exc:  # noqa: BLE001
                    result.cells.append(GridCellResult(
                        params=params, asset_class=asset_class, symbol=symbol,
                        vol_regime_label="n/a", sharpe=None, sharpe_passed=False,
                        mdd=None, mdd_passed=False, error=f"generate_returns failed: {exc}",
                    ))
                    continue

                regime_masks = _vol_regime_masks(price_df, spec.vol_regime_splits)
                for regime_label, mask in regime_masks.items():
                    mask = mask.reindex(full_returns.index).fillna(False)
                    sliced = full_returns[mask]
                    if sliced.empty or sliced.abs().sum() == 0:
                        result.cells.append(GridCellResult(
                            params=params, asset_class=asset_class, symbol=symbol,
                            vol_regime_label=regime_label, sharpe=None, sharpe_passed=False,
                            mdd=None, mdd_passed=False, error="empty/no-trade slice",
                        ))
                        continue
                    try:
                        sharpe_passed, sharpe_ev = check_sharpe_ratio(sliced, min_sharpe=spec.min_sharpe)
                        mdd_passed, mdd_ev = check_max_drawdown(sliced, max_allowed_mdd=spec.max_allowed_mdd)
                        result.cells.append(GridCellResult(
                            params=params, asset_class=asset_class, symbol=symbol,
                            vol_regime_label=regime_label,
                            sharpe=sharpe_ev.get("value"), sharpe_passed=sharpe_passed,
                            mdd=mdd_ev.get("value"), mdd_passed=mdd_passed,
                        ))
                    except Exception as exc:  # noqa: BLE001
                        result.cells.append(GridCellResult(
                            params=params, asset_class=asset_class, symbol=symbol,
                            vol_regime_label=regime_label, sharpe=None, sharpe_passed=False,
                            mdd=None, mdd_passed=False, error=f"validator failed: {exc}",
                        ))

    return result
