# Plain CCI Zero-Line Crossover (SPY accepted; QQQ near-miss MDD)

**Strategy file:** `strategies/2026-09-09_cci_zeroline_crossover.py`
**Knowledge base id:** 2026-09-09-083

## Hypothesis + source

Per Pomegra's "CCI Zero Line Crossover" article and TITAN FX Research Hub
(surfaced via Google search snippet -- "When CCI crosses the zero line, it
signals a potential trend reversal and can serve as a reference point for
trade entries"), CCI crossing above zero signals a fresh uptrend. This is
the first PLAIN unconditional zero-line-cross CCI variant tested in this
repo -- all six prior CCI strategies used an extreme threshold (+/-100/90),
a bounce-without-cross (Zero-Line-Reject), a trend-line break, a
range-reentry, or a hook-from-extreme pattern.

## Grid test (Step 6)

`param_grid={"cci_window": [14,20,30], "max_hold_days": [20,40]}`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), `vol_regime_splits=3`,
2019-01-01 to 2026-09-01:

- **pass_fraction: 0.319** (23/72 cells) -- strong pass rate for this repo
- by_asset_class: equity 23/36, crypto 0/36 (decisive crypto rejection)
- by_vol_regime: low 12/24, mid 5/24, high 6/24 -- notably robust across
  ALL three vol regimes, unusual for a trend-following strategy in this repo
- best_cell: QQQ, low-vol, cci_window=14/max_hold_days=20, Sharpe 2.66

## Single-config validators (Step 7), config: cci_window=14, max_hold_days=20

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 1.074 PASS | **1.114 PASS** |
| Max drawdown (<=0.25) | 0.281 FAIL | **0.153 PASS** |
| Transaction-cost survival (net Sharpe >=0.5) | 0.918 PASS | **0.899 PASS** |
| Walk-forward (4 splits, >=75% positive) | 3/4 PASS | **4/4 PASS** |
| Parameter sensitivity (relative_std <=0.5) | 0.055 PASS | **0.058 PASS** |

SPY: all 5 validators pass cleanly, with very low parameter sensitivity
(0.058) -- the signal is robust across cci_window/max_hold_days combos.
QQQ: 4/5 pass, MDD (28.1%) is the only failure, a near-miss above the 25%
budget.

## Decision

**Accept for SPY.** QQQ logged as a near-miss (MDD fails, everything else
passes) worth revisiting with a tighter max_hold_days or an added
volatility-scaled position-sizing overlay in a future iteration. Crypto
rejected decisively (0/36 grid cells).
