# Backtest Report: Quarters Theory Round-Number Level Bounce

**Strategy file:** `strategies/2026-09-09_quarters_theory_round_number_bounce.py`
**Date:** 2026-09-09
**Source:** Google AI-overview synthesis of FX Replay / Investopedia / TradingView
"Quarters Theory" pages (query: "quarters theory trading strategy specific rules")

## Hypothesis

Quarters Theory (a forex-education concept) holds that major round-number
price levels and the 25%/50%/75% quarter-points between them act as
psychological support/resistance where institutional orders cluster. Source
rules: plot horizontal levels at the big figure and quarter marks; trade a
mean-reversion bounce when price wicks through a level and closes back on
the near side, targeting the next quarter level, stop just past the level.
Adapted here to a scale-invariant percentage-based grid (`round_size_pct` of
a rolling reference price) so it applies to both equity and crypto price
scales, plus an RSI-oversold confirmation layer (source's own oscillator
add-on). First price-level/round-number-grid strategy in this repo.

## Grid test summary (Step 6)

Grid: `round_size_pct` in [0.03, 0.05, 0.08], `rsi_oversold` in [30, 40] x
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 72 cells,
2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.042** (3/72 cells passed)
- **By asset class:** equity 3/36 passed, **crypto 0/36 passed** (decisive)
- **By vol regime:** low 1/24, mid 0/24, high 2/24
- **Best cell:** QQQ, round_size_pct=0.08, rsi_oversold=40, high-vol regime, Sharpe=1.540
- **Worst cell:** QQQ, round_size_pct=0.08, rsi_oversold=40, mid-vol regime, Sharpe=-1.111

## Single-config validation (Step 7): round_size_pct=0.08, rsi_oversold=40, full sample 2018-2026

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.555 (FAIL) | 0.087 (FAIL) | >= 1.0 |
| Max drawdown | 0.160 (PASS) | 0.242 (PASS, narrow) | <= 0.25 |
| Net Sharpe after costs (10bps/trade) | 0.266 (FAIL) | -0.151 (FAIL) | >= 0.5 |
| Walk-forward pass fraction (4 slices) | 0.5 (FAIL) | 0.75 (PASS, marginal) | >= 0.75 |
| Parameter sensitivity relative std | 0.460 (PASS, marginal) | 0.826 (FAIL) | <= 0.5 |
| Num trades | 170 | 160 | -- |

## Decision

**Reject, decisively.** Full-sample Sharpe collapses far below threshold
for both symbols (0.555 QQQ, 0.087 SPY) despite an isolated promising
high-vol grid cell. High trade counts (160-170 over ~8.7yr) mean
transaction costs bite hard (net Sharpe turns negative for SPY, well below
threshold for QQQ). The core hypothesis -- that pure round-number price
levels (independent of any derived indicator) act as a tradeable
support/resistance grid on daily-bar QQQ/SPY/BTC/ETH -- is not supported by
this operationalization. Crypto decisively fails (0/36), consistent with
crypto's generally higher noise-to-signal ratio for daily-bar mean-reversion
constructions already observed across many other strategies in this
knowledge base.
