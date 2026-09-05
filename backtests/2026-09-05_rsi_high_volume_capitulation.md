# RSI Oversold + High-Volume Capitulation Confirmation — Backtest Report

**Hypothesis:** RSI(14) crossing below an oversold threshold (30) confirmed
by ABOVE-average volume (heavy panic-selling capitulation, ratio >= 1.5x
20-day average) signals a stronger reversal setup than RSI oversold alone;
enter long on the subsequent RSI recovery back above 30; exit on RSI
crossing 60 or a max_hold_days time-stop. Non-pyramiding simplification of
TradingView's "RSI Volume Ladder" strategy, targeted at crypto majors per
the source.

**Source:** TradingView "RSI Volume Ladder" by wielkieef (via Google
search snippet): "A long-only pyramiding strategy that scales into
corrections using RSI oversold conditions confirmed by above-average
volume... developed on crypto majors (BTC, ETH)."

**Strategy file:** `strategies/2026-09-05_rsi_high_volume_capitulation.py`

**Distinct from:** 2026-09-05-042 (Connors RSI + volume-EXHAUSTION, i.e.
LOW volume as the confirming "quiet capitulation" signal -- opposite
volume-direction logic).

## Step 6 — Grid test summary (param_grid: vol_confirm_ratio in
[1.3,1.5,2.0] x max_hold_days in [10,15]; symbols: equity QQQ/SPY, crypto
BTC/USDT, ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 72, passed_cells: 4, **pass_fraction: 0.056**
- by_asset_class: equity 4/36 (11%); crypto 0/36 (0%, decisive fail --
  notably the strategy's OWN target asset class per the source failed
  completely)
- by_vol_regime: low 0/24, mid 4/24 (17%), high 0/24
- best_cell: vol_confirm_ratio=1.3, max_hold_days=15, QQQ, mid-vol,
  Sharpe=1.844
- worst_cell: vol_confirm_ratio=1.3, max_hold_days=10, SPY, mid-vol,
  Sharpe=-1.044

## Step 7 — Single-config validators (direct full-sample Sharpe check
across all 6 param combos x 4 symbols, given the sparse/scattered grid
pattern)

| Symbol | Best full-sample Sharpe (any config) |
|---|---|
| QQQ | -0.036 |
| SPY | -0.369 |
| BTC/USDT | 0.052 |
| ETH/USDT | 0.010 |

Every symbol/config combination fails decisively on the full 2019-2026
sample -- even the strategy's own target asset class (BTC/ETH crypto
majors) never exceeds Sharpe 0.052. The scattered mid-vol-only equity
passes in the grid do not reflect any genuine full-sample edge.

## Outcome: **REJECTED**

Decisive full-sample failure across all 4 symbols and 6 parameter combos
(-0.517 to 0.052 Sharpe range, nowhere near the 1.0 threshold). Unlike the
already-accepted opposite-direction variant (low-volume "quiet
capitulation" gates have shown some signal elsewhere in this repo),
requiring HIGH volume at an RSI oversold dip does not carry a robust edge
in either equities or crypto in this dataset -- heavy-volume selloffs may
just as often continue (capitulation cascades) as reverse, diluting any
mean-reversion signal.
