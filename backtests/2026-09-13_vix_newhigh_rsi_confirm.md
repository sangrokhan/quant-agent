# Backtest Report: VIX New-High + RSI Stretch Confirmation (2026-09-13)

## Hypothesis
Per https://www.quantifiedstrategies.com/vix-trading-strategy/ (read via
browser_exec fallback this iteration; web_search's DDGS backend returned no
usable direct hit for the exact VIX-trend-following query, resolved via
Bing search instead), the source's disclosed rule: go long the underlying
equity index when ^VIX makes a new 20-day high AND VIX's own 5-period RSI
is >= 65 (a "stretched" confirmation), exit when close > yesterday's high.

Source URL: https://www.quantifiedstrategies.com/vix-trading-strategy/

## Strategy file
strategies/2026-09-13_vix_newhigh_rsi_confirm.py

## Step 6 grid summary (QQQ/SPY/BTC-USDT/ETH-USDT, vix_high_window=[15,20,30] x vix_rsi_threshold=[60,65,70], vol_regime_splits=3, 2018-2026)

- total_cells: 108, passed_cells: 17, pass_fraction: 0.157
- by_asset_class: equity 17/54 pass, crypto 0/54 (expected -- no VIX analog, all-flat falsification check as designed)
- by_vol_regime: low 17/36 (ALL passes), mid 0/36, high 0/36
- best_cell: SPY, vix_high_window=20/vix_rsi_threshold=70, low-vol, Sharpe 2.63
- worst_cell: ETH/USDT, vix_high_window=15/vix_rsi_threshold=60, high-vol, Sharpe -0.46

Interpretation: entirely a low-volatility-regime phenomenon; fails in mid
and high vol regimes on equity, and crypto correctly shows no signal (no
VIX proxy, all-flat by design).

## Step 7 single-config validators (best grid config: vix_high_window=20, vix_rsi_threshold=70, full sample 2018-2026)

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe | 0.684 FAIL | 0.680 FAIL | >= 1.0 |
| Max Drawdown | 16.0% PASS | 13.9% PASS | <= 25% |
| TC-survival (10bps/trade) | 0.577 PASS (83 trades) | 0.547 PASS (86 trades) | >= 0.5 |
| Walk-forward (4 equal slices) | 3/4 PASS | 3/4 PASS | >= 0.75 |
| Parameter sensitivity (rel. std) | 0.080 PASS (very stable) | 0.097 PASS (very stable) | <= 0.5 |

Full-sample Sharpe fails decisively on both QQQ and SPY. The grid's own
low-vol-only Sharpe of 2.63 does not survive being diluted by mid/high-vol
periods across the full 2018-2026 sample. Notably, param sensitivity is
excellent (very tight relative std) -- the strategy is consistent but
consistently below the 1.0 Sharpe bar, not overfit to one lucky parameter
combo.

## Decision: REJECTED

Primary validator (Sharpe >= 1.0) fails on both QQQ (0.684) and SPY
(0.680) at full-sample despite passing every other validator (MDD, TC,
walk-forward, parameter sensitivity). Consistent with this repo's frequent
finding that this VIX-family entry pattern (like several other VIX/vol-
regime strategies already tested) only has edge in low-vol regimes and
does not survive full-sample dilution.
