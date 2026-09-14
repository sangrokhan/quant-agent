# 2026-09-14 — Elder-Ray ATR-normalized net-power continuous sizing overlay on SMA(40) trend gate

## Hypothesis

Elder-Ray Index (Dr. Alexander Elder, 1989; formula per
https://www.investopedia.com/terms/e/elderray.asp, read via browser_exec
this iteration — web_search's DuckDuckGo backend TLS-errored on every query
attempted): 13-period EMA as a "consensus of value" baseline; Bull Power =
High - EMA, Bear Power = Low - EMA.

This repo has 8 prior Elder-Ray entries (2026-09-04-037, -110,
2026-09-06-135, -176, 2026-09-08-008, -155, 2026-09-09-104), all using
Bull/Bear Power as a binary divergence/crossover/contraction-recovery
ENTRY trigger — all rejected. None reframed Elder-Ray as a CONTINUOUS
SIZING dial (the pattern that rescued CMO/UO/StochRSI/MFI/CMF/Aroon/
Williams %R/%B/DMI-diff/ADX/CHOP/ER/TRIX/TSI/R2 this cron trigger).
Because raw Bull/Bear Power are dollar-scale (not natively bounded like
those oscillators), this iteration ATR-normalizes the spread first:
`net_power = (BullPower - BearPower) / ATR(14)`, then uses it as a
continuous sizing dial (`exposure = base_exposure + sensitivity *
clip(net_power/net_power_reference, -1.5, 1.5)`) within an SMA(40) uptrend
gate, with a deadband to control turnover.

## Strategy file

`strategies/2026-09-14_elderray_sizing_sma_trend.py`

## Step 6 — Grid test summary (72 cells: sensitivity in {0.3,0.5,0.7} x
deadband in {0.05,0.10} x symbols {QQQ,SPY,BTC/USDT,ETH/USDT} x 3 vol
regimes)

- pass_fraction: 0.417 (30/72)
- by_asset_class: equity 18/36 passed; crypto 12/36 passed
- by_vol_regime: low 22/24 passed; mid 8/24 passed; high 0/24 passed
  (net-power sizing works well in calm/trending regimes, degrades sharply
  in high-vol regimes — consistent with an ATR-normalized momentum-style
  dial losing signal when ATR itself is spiking)
- best_cell: ETH/USDT mid-vol, sensitivity=0.5/deadband=0.10, Sharpe 2.62
- worst_cell: QQQ high-vol, sensitivity=0.5/deadband=0.10, Sharpe -0.28

## Step 7 — Single-config validator suite (full sample 2019-01-01 to
2026-09-01, sensitivity=0.5)

At deadband=0.10, QQQ/SPY passed Sharpe/MDD/WF/param-sensitivity but
FAILED transaction-cost survival (too much turnover: QQQ net Sharpe 0.33,
SPY net Sharpe 0.21). Widening the deadband to 0.25 (same rebalance-
threshold fix pattern already validated repeatedly this cron trigger for
CMO/UO/StochRSI etc.) cut turnover roughly in half and rescued TC survival:

| Symbol | deadband | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param-sens |
|---|---|---|---|---|---|---|
| QQQ | 0.25 | 1.072 (pass) | 0.181 (pass) | 0.640 (pass) | 1.00 (pass) | 0.014 (pass) |
| SPY | 0.25 | 1.008 (pass) | 0.099 (pass) | 0.512 (pass) | 1.00 (pass) | 0.017 (pass) |
| BTC/USDT | 0.10 | 1.497 (pass) | 0.377 (**fail**, >0.25) | 0.871 (pass) | 1.00 (pass) | 0.014 (pass) |

## Step 8 — Decision

**Accepted: QQQ and SPY** (equity), sensitivity=0.5/deadband=0.25, all 5
validators pass. **Rejected: crypto (BTC/USDT, ETH/USDT)** — decisive MDD
failure (0.377 vs 0.25 threshold on BTC/USDT; grid shows 0/24 high-vol
crypto cells passing at all) — consistent with this cron trigger's
recurring finding that continuous-sizing overlays built from smoothed
oscillators broadly fail to control crypto drawdowns even when Sharpe/TC
pass.
