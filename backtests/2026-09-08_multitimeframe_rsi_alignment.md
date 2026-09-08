# Multi-Timeframe RSI Alignment — Backtest Report (REJECTED)

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_multitimeframe_rsi_alignment.py`
**Knowledge base id:** 2026-09-08-136

## Hypothesis

Per https://medium.com/@FMZQuant/multi-timeframe-rsi-trading-strategy-169
cc2771848's disclosed rule (originally 15m/1h/4h intraday, adapted here to
daily/weekly/monthly resampled RSI): long when RSI_daily > RSI_weekly >
RSI_monthly (strict alignment) AND RSI_monthly > a floor (avoid a
structurally oversold slow trend); exit when RSI_daily crosses back below
RSI_weekly. Distinct from Elder's Triple Screen (2026-09-04-044, rejected)
which uses a weekly MACD-Histogram slope filter gating a daily Stochastic
%K trigger — here all three timeframes use the SAME indicator (RSI) in a
strict three-way ordering/alignment condition.

## Parameter sweep (before grid test)

Manual sweep of `rsi_period` in {7,10,14,21} × `monthly_oversold_floor` in
{20,30,40,50} on both QQQ and SPY, full-sample Sharpe (only configs with
>=10 trades shown):

Best result across the ENTIRE sweep: QQQ at rsi_period=14,
monthly_oversold_floor=50, Sharpe 0.918 — but only 13 trades over the
full 2019-2026 sample (too sparse to trust; likely overfit to a handful of
lucky trades). Every other combination on both symbols stayed well below
0.7, most in the 0.1-0.5 range.

## Decision: REJECTED

No parameter combination across a systematic 16-combo sweep on either
symbol produces a robust, adequately-traded (>=20 trades) config clearing
even Sharpe 0.7, let alone the 1.0 threshold. The daily/weekly/monthly
resampling adaptation of an intraday 15m/1h/4h construction appears to
lose most of its edge at this much slower timeframe cadence — the "fast"
timeframe (daily) updates far less frequently relative to the "slow"
timeframe (monthly) than the source's own 15m-vs-4h ratio, producing a
much less responsive/more lagging signal. Given the sweep's uniformly weak
results, the full grid-test/validator pipeline was skipped per Step 7's
minimum-subset guidance for a clearly non-viable construction.
