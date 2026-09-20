# Backtest Report: Donchian Channel Breakout with ATR Volatility-Expansion Filter

**Strategy file:** `strategies/2026-09-21_donchian_atr_volexpansion_breakout.py`
**Date:** 2026-09-21
**Hypothesis source:** N. Poluri, SSRN 2026, "Evaluating the Performance of
a Donchian Channel [breakout strategy] enhanced with the ATR-based
volatility regime filter and ATR based [stop-loss]" — full text
inaccessible (SSRN login wall), rule reconstructed from Google's
AI-overview synthesis of the paper's disclosed numeric parameters
(Donchian 20-period entry, ATR(14), 200-day SMA trend filter, ATR(14) >
ATR(50) volatility-expansion gate, 3.0x ATR stop-loss, 10-period opposite
Donchian extreme exit).

## Hypothesis

A Donchian Channel breakout is filtered to only fire when price is in a
long-term uptrend (close > 200-day SMA) AND volatility is EXPANDING
(current ATR(14) above its own 50-period moving average) — the theory
being breakouts are more reliable continuation signals during a genuine
volatility regime shift rather than a quiet/contracting market. Exit uses
a shorter opposite Donchian channel extreme as a trailing stop, backed by
a hard ATR-multiple stop-loss. Distinct from the already-accepted GAPO
strategy (which requires volatility to be LOW/compressed before the
breakout — the opposite regime condition).

## Grid test (Step 6)

`param_grid={"donchian_entry": [20, 40], "donchian_exit": [10, 20],
"stop_atr_mult": [2.0, 3.0]}`, `symbols={"equity": ["QQQ","SPY"], "crypto":
["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`, period 2018-01-01 to
2026-09-01.

- Overall pass_fraction: 25/96 = 0.260
- By asset class: equity 13/48, crypto 12/48 (roughly even split, unusual
  for this repo where crypto usually fails decisively)
- By vol regime: low 18/32, mid 7/32, high 0/32
- Best cell: BTC/USDT, donchian_entry=20/donchian_exit=20/stop_atr_mult=2.0,
  high-vol regime, Sharpe 1.51

## Full-sample single-config sweep (all 8 param combos x 4 symbols = 32 points)

QQQ: Sharpe range 0.345-0.545, all FAIL (< 1.0)
SPY: Sharpe range 0.221-0.460, all FAIL
BTC/USDT: Sharpe range 0.707-0.868, all FAIL
ETH/USDT: Sharpe range 0.617-0.928 (best near-miss), all FAIL

**No parameter combination passes the Sharpe >= 1.0 threshold on the full
sample for ANY symbol.** Max-drawdown is comfortably under 0.25 for most
equity configs but that's moot given the Sharpe fail.

## Decision: REJECTED

The volatility-expansion gate combined with the 200-day trend filter makes
this strategy trade far too conservatively/rarely to generate a full-sample
Sharpe above 1.0 on any symbol — the grid's vol-regime-sliced pass_fraction
(0.26) is entirely a narrow-slice artifact (high-vol crypto cells looked
good in isolation but the full-sample equity curve dilutes any edge).
Crypto ETH/USDT came closest (Sharpe 0.928) but still falls short. Decisive
rejection across the board; this exact "volatility-expansion gate on a
Donchian breakout" mechanism does not clear this repo's bar, in contrast to
the accepted GAPO strategy's opposite "volatility-compression-then-
breakout" framing, or the accepted fractional-ATR-breakout-with-trend-
filter (2026-09-21-189) which used a much higher-frequency entry signal
(daily ATR-distance from prior close) rather than a slower channel
breakout.
