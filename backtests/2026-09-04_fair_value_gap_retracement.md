# Backtest Report: Fair Value Gap (FVG) Retracement Entry, daily-bar adaptation

**Strategy file:** `strategies/2026-09-04_fair_value_gap_retracement.py`
**Date:** 2026-09-04
**Source:** Google AI-overview (ICT/smart-money-concepts consensus across
VladimirRibakov/AudaCity Capital/GeekOnDaily/Phidias/ForexTesterOnline
sources), retrieved via browser_exec after web_search DDGS/Yahoo TLS failure

## Hypothesis

3-candle bullish Fair Value Gap (low[i] > high[i-2]) formed in an uptrend
(close > SMA200), entered on retracement to the gap's 50% midpoint, with a
stop below the gap's outer extreme and a fixed reward-multiple (1.5-3x)
take-profit target.

## Grid test summary (reward_multiple x fvg_expiry_days x 4 symbols x 3 vol terciles = 72 cells)

- pass_fraction: **37.5%** (27/72) -- best of any strategy tested this cron
  trigger's 3 iterations so far
- by_asset_class: equity 18/36 (50%), crypto 9/36 (25%)
- by_vol_regime: low 12/24 (50%), mid 6/24 (25%), high 9/24 (38%)
- best_cell: SPY, reward_multiple=1.5/expiry=10, low-vol regime, Sharpe 2.20

## Full-sample single-config metrics (reward_multiple=1.5, fvg_expiry_days=10)

| Symbol   | Sharpe | Pass | MDD   | Pass | TC-adj Sharpe (10bps, entry+exit) | Pass |
|----------|--------|------|-------|------|-------------------------------------|------|
| SPY      | 0.655  | No   | 0.077 | Yes  | (not run, Sharpe already fails)     | -    |
| QQQ      | 1.157  | Yes  | 0.078 | Yes  | 0.071                               | No   |
| BTC/USDT | 0.430  | No   | 0.147 | Yes  | (not run, Sharpe already fails)     | -    |
| ETH/USDT | 0.627  | No   | 0.159 | Yes  | (not run, Sharpe already fails)     | -    |

Parameter sensitivity (QQQ Sharpe across reward_multiple 1.5/2.0/3.0/1.5,fvg_expiry=5,
relative std): 0.022 (very low, well under 0.5 threshold) -- PASS.

## Decision: REJECTED (all symbols)

- **QQQ** clears gross Sharpe (1.16) and MDD (7.8%) with very stable
  parameter sensitivity, but **decisively fails transaction-cost survival**
  (net Sharpe 0.07 vs 0.5 threshold) -- the strategy trades relatively
  infrequently (136 trades / 7.7yr) but each trade carries meaningful
  round-trip cost drag relative to its modest per-trade edge; net of even a
  modest 10bps/leg assumption the edge evaporates.
- **SPY, BTC/USDT, ETH/USDT** all fail gross Sharpe outright (0.66, 0.43,
  0.63 respectively, all < 1.0).
- MDD passes cleanly everywhere (7-16%), confirming the tight stop-loss
  risk-management mechanic works as intended, but that alone isn't
  sufficient without a real Sharpe edge net of costs.

Future idea: this is the highest grid pass_fraction (37.5%) of any strategy
tested this run -- worth revisiting with (a) a wider stop/less-frequent
signal to reduce the trade-cost drag relative to edge, or (b) partial-profit
scaling (1:1 then move to breakeven) as the source itself recommends rather
than a single fixed-R:R exit, which may reduce round-trip overhead per unit
of captured edge.
