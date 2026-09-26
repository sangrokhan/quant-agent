# Backtest Report: IBS Extreme-Threshold Trend-Reversal (Previous-Day Input)

**Strategy file:** `strategies/2026-09-26_ibs_extreme_threshold_reversal.py`
**KB id:** 2026-09-26-071
**Outcome:** ACCEPTED (equity QQQ + SPY); REJECTED (crypto, out of scope)

## Hypothesis

Source: https://medium.com/@redsword_23261/internal-bar-strength-trend-reversal-trading-system-c5f8c7e5362e
("Internal Bar Strength Trend Reversal Trading System"). Distinct from
this repo's 38+ prior IBS entries in two ways: (1) IBS is computed from
the **previous** completed bar (IBS[t]=(Close[t-1]-Low[t-1])/(High[t-1]-Low[t-1]))
rather than same-day close; (2) uses the source's own **extreme asymmetric**
thresholds (entry 0.09, exit 0.985) rather than this repo's typical
0.2/0.8 range, combined with a long EMA(220) trend filter and a 14-day
time-stop.

Entry: IBS[t-1] < entry_threshold (0.09) AND close > EMA(220). Exit:
IBS[t-1] >= exit_threshold (0.985), or a 14-day time-stop.

## Grid summary (Step 6)

`param_grid={entry_threshold:[0.09,0.15,0.20], exit_threshold:[0.9,0.985]}`,
symbols equity (QQQ, SPY) + crypto (BTC/USDT, ETH/USDT), `vol_regime_splits=3`,
72 total cells, 2016-01-01 to 2026-09-01.

| Metric | Value |
|---|---|
| pass_fraction | 0.403 (29/72) |
| by_asset_class | **equity 29/36 (0.806)**, crypto 0/36 (0.0) |
| by_vol_regime | low 12/24, mid 12/24, high 5/24 |
| best_cell | QQQ, entry_threshold=0.09, exit_threshold=0.9, low-vol tercile, Sharpe 2.381 |
| worst_cell | BTC/USDT, entry_threshold=0.2, exit_threshold=0.9, low-vol tercile, Sharpe -0.520 |

Strong, broad equity edge (holds across all 3 vol regimes, though weaker
in high-vol); crypto decisively rejected across the entire grid — scope
this strategy to equity only.

## Single-config validation (Step 7) — source's own default config, full sample

Config: entry_threshold=0.09, exit_threshold=0.985, trend_window=220 (EMA),
max_hold_days=14.

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | **PASS** 1.269 | **PASS** 1.325 | ≥ 1.0 |
| Max drawdown | **PASS** 0.182 | **PASS** 0.107 | ≤ 0.25 |
| Transaction cost survival | **PASS** net Sharpe 0.998 (182 trades, 10bps/trade) | **PASS** net Sharpe 0.893 (183 trades) | ≥ 0.5 |
| Walk-forward (4 manual contiguous splits — `vbt.utils.splitting` still broken, established repo workaround) | **PASS** 4/4 splits positive (1.0) | **PASS** 4/4 splits positive (1.0) | ≥ 0.75 |
| Parameter sensitivity (entry_threshold sweep {0.05,0.09,0.12,0.15}) | **PASS** rel-std 0.057 | **PASS** rel-std 0.056 | ≤ 0.5 |

All 5 validators pass cleanly on both QQQ and SPY, with a very stable
walk-forward (4/4 positive splits) and low parameter sensitivity —
strong, robust signal.

## Decision

**Accept (equity only: QQQ, SPY).** All 5 validators pass for both
tickers at the source's own default config, with a broad grid
pass_fraction (0.806 within equity, across all 3 vol regimes). **Reject
crypto (BTC/USDT, ETH/USDT)** — decisive 0/36 grid failure, out of scope.
Strategy file kept live in `strategies/`, scoped explicitly to equity.
