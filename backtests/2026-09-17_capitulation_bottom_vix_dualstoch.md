# Backtest Report: Katsanos Capitulation-Bottom (VIX Spike + Dual-Stochastic Stack)

**Strategy file:** `strategies/2026-09-17_capitulation_bottom_vix_dualstoch.py`
**Source:** Traders.com Jul 2021 Traders' Tips (Markos Katsanos, "Buy &
Hold, Or Buy & Sell?", TASC Jul 2021), TradeStation EasyLanguage code, read
via `browser_exec` this iteration --
`https://traders.com/Documentation/FEEDbk_docs/2021/07/TradersTips.html`.

## Hypothesis

The source's weekly SPY+VIX strategy times capitulation bottoms via a
composite condition: a sharp recent bounce, VIX crashing down from its own
15-period high (fear peaking and subsiding), a deep pullback from the
100-day high, and BOTH a fast (14-period) and slow (40-period) stochastic
%K simultaneously oversold with the fast one crossing above the slow one
(bullish stack). Adapted here to daily bars (rescaled windows) as a
long-only entry, with a simple SMA trend-loss exit substituting for the
source's symmetric euphoria-top sell signal (out of scope for this
long-only adaptation).

## Grid test (Step 6)

`vix_dn_min` in [-15,-20] x `cch_threshold` in [-10,-15] x `up_threshold`
in [3,6], symbols QQQ/SPY (equity) + BTC/USDT, ETH/USDT (crypto, VIX-gate
still computed via ^VIX for consistency even though conceptually odd for
crypto), vol_regime_splits=3, 2019-01-01..2026-09-01. 96 cells (smaller
grid given decent trade counts required for the low-frequency
capitulation signal).

- **pass_fraction: 0.031** (3/96) -- decisively weak grid result
- by_asset_class: equity 3/48 (0.0625), crypto 0/48 (0.0) -- crypto never
  passed a single cell (unsurprising: VIX-based fear-gauge gating doesn't
  transfer conceptually to crypto).
- by_vol_regime: low 1/32, mid 2/32, high 0/32

## Single-config validation (Step 7) -- rejected at Sharpe screen

Full-sample Sharpe was checked directly for all 16 param combinations x 2
symbols (32 configs) rather than proceeding to the full validator suite,
since EVERY combination was decisively NEGATIVE:

| Symbol | Best config found | Sharpe | Trades |
|---|---|---|---|
| QQQ | vix_dn_min=-20/cch=-10/up=3 | -0.180 | 16 |
| SPY | vix_dn_min=-20/cch=-10/up=3 | -0.231 | 11 |

All 32 full-sample (symbol, param-combo) pairs tested had negative Sharpe,
ranging from -0.18 to -0.84. The strategy loses money in every
configuration tried.

**Diagnosis:** the substituted SMA(20) trend-loss exit is likely too tight
for a capitulation-bottom entry -- buying right after a sharp selloff often
means price is still below its 20-day SMA at entry (the SMA hasn't caught
up yet), causing an immediate/near-immediate stop-out before the intended
mean-reversion bounce can play out. The original source's weekly timeframe
and symmetric sell-signal condition (rather than a naive SMA stop) were
likely load-bearing design choices that this daily-bar, simplified-exit
adaptation lost.

## Overall decision

**REJECTED across all asset classes and all parameter combinations tested.**
Every full-sample (symbol, config) combination produced negative Sharpe.
The core capitulation-bottom entry idea (VIX spike-and-crash + deep
pullback + dual-stochastic bullish stack) may still have merit, but this
adaptation's exit logic (SMA(20) trend-loss stop) appears fundamentally
mismatched to the entry's premise -- a future revisit should use a
volatility-contraction-based exit or a fixed-bar hold instead of an SMA
stop, or properly implement the weekly timeframe the source specifies.
