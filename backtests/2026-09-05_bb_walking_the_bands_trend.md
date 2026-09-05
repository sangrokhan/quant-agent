# Bollinger Bands "Walking the Bands" Trend-Continuation — Backtest Report

**Hypothesis:** Per John Bollinger's own "Walking the Bands" concept: price
repeatedly touching/staying close to the upper Bollinger Band over several
consecutive bars confirms a strong, sustained UPTREND (not a reversal
signal) -- stay long while the price continues walking the upper band, and
exit only when price breaks away back below the basis (middle) band.

**Source:** https://tavifinance.com/2024/09/17/bollinger-bands-walking-the-bands/
(chapter summary of Bollinger's own writing): "Walking the bands is
indicative of a strong trend... this is not a signal for reversal but
rather a confirmation of trend strength. Traders should stay in the trade
as long as the price continues to walk the bands, exiting only when there
are clear reversal signals."

**Strategy file:** `strategies/2026-09-05_bb_walking_the_bands_trend.py`

**Distinct from:** every other Bollinger Band strategy in this repo, which
all treat a band touch/breach as a MEAN-REVERSION or one-off BREAKOUT
trigger (2026-09-03-001 lower-band mean reversion, 2026-09-04-091/126
squeeze breakout). This is a genuine TREND-CONTINUATION interpretation:
sustained proximity to the upper band across multiple bars is itself the
entry signal, and exit is defined by "breaking away" (dropping below the
basis line), not a single-bar band-crossing event.

## Step 6 — Grid test summary (param_grid: proximity_pct in [0.95,0.98] x
walk_bars in [3,5]; symbols: equity QQQ/SPY, crypto BTC/USDT, ETH/USDT;
vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 48, passed_cells: 10, **pass_fraction: 0.208**
- by_asset_class: equity 10/24 (42%); crypto 0/24 (0%, decisive fail)
- by_vol_regime: low 8/16 (50%), mid 1/16 (6%), high 1/16 (6% -- one of a
  small number of strategies this trigger to pass any high-vol cell)
- best_cell: proximity_pct=0.95, walk_bars=5, QQQ, low-vol, Sharpe=2.553
- worst_cell: proximity_pct=0.98, walk_bars=5, QQQ, high-vol, Sharpe=-0.814

## Step 7 — Single-config validators (config: proximity_pct=0.95,
walk_bars=5, full unconditional 2019-2026 sample)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | **PASS** 1.112 | **PASS** 1.002 (razor-thin pass) |
| Max Drawdown (<= 0.25) | PASS 0.188 | PASS 0.098 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade) | PASS 0.909 (126 trades) | PASS 0.666 (165 trades) |
| Parameter sensitivity (relative_std <= 0.5, 4-cell proximity/walk_bars sweep) | PASS 0.337 | PASS 0.243 |

Walk-forward not run: `check_walk_forward` hits the pre-existing
`vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt
version (same known issue as other recent entries).

## Outcome: **ACCEPTED (QQQ AND SPY, proximity_pct=0.95/walk_bars=5)**;
crypto rejected decisively

Both equity indices clear all four validators at the shared config,
though SPY's Sharpe (1.002) is a razor-thin pass right at the threshold --
worth flagging for a future loop to re-verify with a slightly different
data window or extra out-of-sample check before treating SPY as robustly
confirmed. QQQ is more comfortably above threshold (1.112). Trade counts
are notably higher than most strategies in this repo (126 QQQ / 165 SPY
trades over 7.7 years) since the walk-the-bands condition re-triggers
whenever price re-enters and re-exits proximity to the upper band, rather
than firing once per major trend -- transaction-cost survival still holds
comfortably (0.909 / 0.666) despite the higher turnover. Crypto failed all
24 grid cells, consistent with the broader pattern in this repo of
trend/band-proximity constructions not generalizing to BTC/ETH.
