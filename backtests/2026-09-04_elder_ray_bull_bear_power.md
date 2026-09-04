# 2026-09-04 — Elder Ray Index (Bull Power / Bear Power) long-only trend strategy

**Hypothesis:** Elder Ray Index (Alexander Elder, 1989; source:
https://www.quantifiedstrategies.com/elder-ray-indicator/). 13-day EMA
defines trend; Bull Power = High - EMA, Bear Power = Low - EMA. Long entry
when EMA is rising AND Bear Power is negative but rising (bears losing
conviction while price still dips below EMA on the lows). Exit (go flat) on
the mirror short-entry condition (EMA falling AND Bull Power positive but
falling) rather than an actual short, since source found shorting
underperforms across assets. First Bull/Bear Power indicator family tested
in this repo.

**Source:** https://www.quantifiedstrategies.com/elder-ray-indicator/ (their
own AmiBroker backtest on SPY 2000-2020: CAGR 3.6% vs 6.25% buy-hold, 59%
time invested, win rate 39.5%, profit factor 1.5); also
https://www.google.com/search?q=%22Elder+Ray%22+bull+power+bear+power+trading+strategy+backtest+rules
(search fallback) and
https://www.bing.com/search?q=Elder+Ray+Index+bull+power+bear+power+trading+strategy+rules
(low-quality/irrelevant results, not used).

## Grid test summary (ema_window in {10,13,16,21}; QQQ, SPY, BTC/USDT, ETH/USDT; vol_regime_splits=3)

- total_cells: 48, passed_cells: 11, **pass_fraction: 0.229**
- by_asset_class: equity 11/24 passed, **crypto 0/24 passed**
- by_vol_regime: low 8/16, mid 3/16, **high 0/16**
- best_cell: ema_window=16, QQQ, low-vol regime, Sharpe=2.69
- worst_cell: ema_window=10, QQQ, high-vol regime, Sharpe=-0.67

Passes only in equity low/mid-vol regime slices; fails decisively in all
crypto cells and all high-vol cells regardless of asset class.

## Single-config validators (ema_window=16, QQQ, full sample 2019-01-01 to 2026-09-01)

| validator | passed | value | threshold |
|---|---|---|---|
| sharpe_ratio | **FAIL** | 0.754 | >= 1.0 |
| max_drawdown | **FAIL** | 0.388 | <= 0.25 |
| transaction_cost_survival (10bps/trade, 122 trades) | pass | net Sharpe 0.612 | >= 0.5 |
| walk_forward | skipped | -- | validators.py `check_walk_forward` hits a vectorbt API mismatch (`vectorbt.utils` has no attribute `splitting`) — pre-existing bug in the repo's validator, not specific to this strategy; flagging for a future iteration to fix |
| parameter_sensitivity (ema_window in {10,13,16,21}, full-sample QQQ Sharpe) | pass | relative_std 0.292 | <= 0.5 |

## Decision: **REJECT**

Full-sample Sharpe and max-drawdown both fail on the best grid config
(ema_window=16, QQQ). The grid confirms this isn't a fluke: the strategy
only clears the Sharpe/MDD bar inside low-vol regime slices (which the
full-sample validator run, correctly, does not selectively cherry-pick), and
it fails outright on crypto and in high-vol regimes. This matches the
source article's own skeptical conclusion ("not likely to be very
successful on stocks... indicator is not very useful").
