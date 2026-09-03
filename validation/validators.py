"""Strategy validation stubs.

These functions are thin wrappers around ``vectorbt`` (backtest engine,
performance metrics, walk-forward splitting) — do NOT reimplement Sharpe
ratio, drawdown, or parameter-sweep logic here. Call into vectorbt and shape
its output into a simple ``(passed: bool, evidence: dict)`` contract so the
Research Agent can log a clear pass/fail reason to the knowledge base.

Every validator returns a tuple:
    (passed: bool, evidence: dict)

``evidence`` should always be JSON-serializable (used verbatim in the
knowledge_base log entry), and should include at minimum the metric value(s)
and the threshold that was applied.

Thresholds here are starting points — the Research Agent may need to tune
them per asset class/timeframe, but should record whatever threshold it
actually used in ``evidence``.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

import pandas as pd

Evidence = Dict[str, Any]


def check_sharpe_ratio(
    returns: pd.Series,
    min_sharpe: float = 1.0,
    periods_per_year: int = 252,
) -> Tuple[bool, Evidence]:
    """Annualized Sharpe ratio via vectorbt's returns accessor.

    Requires `vectorbt` to be installed (see requirements.txt). Uses
    ``returns.vbt.returns(freq=...)`` for the actual computation.
    """
    import vectorbt as vbt  # noqa: F401  (imported for its pandas accessor side effect)

    # vectorbt's Returns accessor needs an explicit annualization factor when
    # the index has no inferable freq (e.g. after .pct_change()/masking
    # breaks DatetimeIndex.freq) -- pass freq='D' explicitly rather than
    # relying on index.freq, which is unset in practice for our daily bars.
    sharpe = returns.vbt.returns(freq="D").sharpe_ratio()

    passed = bool(sharpe is not None and sharpe >= min_sharpe)
    return passed, {
        "metric": "sharpe_ratio",
        "value": float(sharpe) if sharpe is not None else None,
        "threshold": min_sharpe,
        "periods_per_year": periods_per_year,
    }


def check_max_drawdown(
    returns: pd.Series,
    max_allowed_mdd: float = 0.25,
) -> Tuple[bool, Evidence]:
    """Max drawdown must not exceed ``max_allowed_mdd`` (fraction, e.g. 0.25 = 25%)."""
    import vectorbt as vbt  # noqa: F401

    mdd = abs(returns.vbt.returns(freq="D").max_drawdown())
    passed = bool(mdd <= max_allowed_mdd)
    return passed, {
        "metric": "max_drawdown",
        "value": float(mdd),
        "threshold": max_allowed_mdd,
    }


def check_transaction_cost_survival(
    gross_returns: pd.Series,
    cost_bps_per_trade: float,
    num_trades: int,
    min_net_sharpe: float = 0.5,
) -> Tuple[bool, Evidence]:
    """Rough check that the strategy still looks good after transaction costs.

    Deducts an approximate flat cost per trade from gross returns before
    recomputing Sharpe. This is intentionally simple; for precise cost
    modeling use vectorbt Portfolio.from_signals(fees=..., slippage=...)
    directly in the backtest step instead of here.
    """
    import vectorbt as vbt  # noqa: F401

    total_cost_drag = (cost_bps_per_trade / 10_000.0) * num_trades
    net_returns = gross_returns.copy()
    if len(net_returns) > 0:
        net_returns.iloc[-1] -= total_cost_drag
    net_sharpe = net_returns.vbt.returns(freq="D").sharpe_ratio()
    passed = bool(net_sharpe is not None and net_sharpe >= min_net_sharpe)
    return passed, {
        "metric": "net_sharpe_after_costs",
        "value": float(net_sharpe) if net_sharpe is not None else None,
        "threshold": min_net_sharpe,
        "cost_bps_per_trade": cost_bps_per_trade,
        "num_trades": num_trades,
        "estimated_total_cost_drag": total_cost_drag,
    }


def check_walk_forward(
    price_data: pd.DataFrame,
    strategy_fn,
    n_splits: int = 4,
    min_pass_fraction: float = 0.75,
) -> Tuple[bool, Evidence]:
    """Walk-forward robustness check.

    ``strategy_fn(price_slice: pd.DataFrame) -> pd.Series returns`` is
    supplied by the Research Agent's strategy module. Splitting should use
    vectorbt's ``vbt.utils.split`` / ``Portfolio`` walk-forward helpers
    (see vectorbt docs: "Walk-forward" splitter) rather than hand-rolled
    date-slicing logic.
    """
    import vectorbt as vbt  # noqa: F401

    splits = vbt.utils.splitting.RangeSplitter(n=n_splits).split(price_data.index)
    results = []
    for split_range in splits:
        idx = split_range if not isinstance(split_range, tuple) else split_range[0]
        slice_df = price_data.loc[idx]
        if slice_df.empty:
            continue
        returns = strategy_fn(slice_df)
        sharpe = returns.vbt.returns.sharpe_ratio() if len(returns) else None
        results.append(sharpe is not None and sharpe > 0)

    pass_fraction = (sum(results) / len(results)) if results else 0.0
    passed = bool(pass_fraction >= min_pass_fraction)
    return passed, {
        "metric": "walk_forward_pass_fraction",
        "value": pass_fraction,
        "threshold": min_pass_fraction,
        "n_splits": n_splits,
        "per_split_passed": results,
    }


def check_parameter_sensitivity(
    param_grid_results: Dict[str, float],
    max_relative_std: float = 0.5,
) -> Tuple[bool, Evidence]:
    """Checks that performance doesn't collapse under small parameter perturbations.

    ``param_grid_results`` maps a stringified parameter combo to its Sharpe
    (or other headline metric) from a vectorbt parameter sweep
    (``Portfolio.from_signals`` with array-like params, a.k.a. vectorbt's
    built-in vectorized parameter grid). Compute the sweep with vectorbt;
    only the pass/fail judgement happens here.
    """
    if not param_grid_results:
        return False, {"metric": "parameter_sensitivity", "value": None, "reason": "empty grid"}

    values = list(param_grid_results.values())
    mean = sum(values) / len(values)
    if mean == 0:
        return False, {"metric": "parameter_sensitivity", "value": None, "reason": "mean is zero"}

    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = variance ** 0.5
    relative_std = std / abs(mean)

    passed = bool(relative_std <= max_relative_std)
    return passed, {
        "metric": "parameter_sensitivity_relative_std",
        "value": relative_std,
        "threshold": max_relative_std,
        "grid_size": len(values),
        "mean": mean,
        "std": std,
    }
