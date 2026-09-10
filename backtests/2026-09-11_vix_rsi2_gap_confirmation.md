# Connors/Alvarez VIX RSI + VIX Gap-Up Confirmation — ACCEPTED (QQQ only)

**Iteration ID:** 2026-09-11-018
**Date:** 2026-09-11

## Hypothesis

Direct fix attempt for this repo's near-miss `2026-09-05-052` (Connors/
Alvarez VIX RSI, full-period Sharpe below threshold on both QQQ (0.654)
and SPY (0.829) despite every other validator passing cleanly; low trade
count 39-41 over 7.5y suggested a real but too-infrequent/low-magnitude
edge).

Per https://www.turingtrader.com/portfolios/connors-vix-rsi/ (visited this
iteration), TuringTrader's restatement of Connors & Alvarez's exact
published rule (from "Short Term Trading Strategies That Work", 2009)
includes a fourth condition this repo's original implementation omitted:
**"today's VIX open is greater than yesterday's close"** -- the VIX must
gap up intraday on the signal day, tightening selectivity toward genuine
fresh fear spikes rather than any elevated-RSI(2) day.

Full rule: (1) tradable-asset close > 200-day SMA, (2) tradable-asset
RSI(2) < `price_rsi_entry`, (3) VIX's own RSI(2) > `vix_rsi_entry`, (4)
today's VIX open > yesterday's VIX close (NEW). Exit: tradable-asset RSI(2)
> `price_rsi_exit`, or `max_hold_days` time-stop.

## Fine-tune result

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe) | Trades | Manual walk-forward (4 splits) |
|---|---|---|---|---|---|---|
| QQQ | trend_window=200, price_rsi_entry=30, vix_rsi_entry=90, price_rsi_exit=75, max_hold_days=15 | **1.055** (PASS) | 0.107 (PASS, thr 0.25) | 0.914 (PASS, thr 0.5) | 89 | 4/4 positive (PASS) |
| SPY | (324-combo grid search, none passing) | best found insufficient | -- | -- | -- | -- |

Adding the VIX gap-up condition reduced QQQ's ungated `2026-09-05-052`
config trade count from 104 to 91 and raised default-param Sharpe from
0.654 to 0.795; a further 324-combination fine-tune (`trend_window in
{150,200,250} x price_rsi_entry in {20,25,30} x vix_rsi_entry in
{85,90,95} x price_rsi_exit in {55,65,75} x max_hold_days in
{5,10,15,20}`) found a config clearing the Sharpe threshold (1.055) while
retaining strong TC-survival and MDD. The same fine-tune search on SPY,
however, found no passing configuration -- the gap-up condition, while
helping QQQ, was not sufficient to rescue SPY's near-miss.

Crypto not tested: VIX (CBOE equity implied-volatility index) has no
meaningful crypto analog, and this repo's `load_crypto` OHLCV data has no
VIX-equivalent signal source -- consistent with this repo's established
VIX-strategy pattern (see `2026-09-05_cvr3_vix_market_timing.py`,
`2026-09-05_vix_rsi2_connors_alvarez.py`) of testing VIX-signal strategies
on equity indices only.

## Decision: ACCEPTED (QQQ only)

QQQ passes Sharpe, max drawdown, transaction-cost survival, and manual
walk-forward. This directly resolves the `2026-09-05-052` near-miss for
QQQ by adding the previously-omitted TuringTrader-disclosed VIX gap-up
confirmation condition. SPY remains rejected even with this fix and an
extensive fine-tune search.
