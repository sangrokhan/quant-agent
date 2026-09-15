# Backtest Report: John Carter TTM Scalper reversal-confirmation

**Strategy file:** `strategies/2026-09-16_ttm_scalper_reversal_confirmation.py`
**Date:** 2026-09-16
**Source:** https://www.tradingview.com/script/CddpDBGA-TTM-scalper-indicator-Strategy/
(HPotter's exact disclosed Pine v2 port of John Carter's TTM Scalper
indicator, from "Mastering the Trade")

## Hypothesis
Pure price-action swing-reversal-confirmation pattern using only the last
4 closes (no smoothing/no indicator parameters): `trigger_sell = (close[1]
< close) AND (close[2] < close[1] OR close[3] < close[1])`, `trigger_buy`
is the mirror. A state machine tracks the most recent confirmed reversal
direction; long-only implementation: long while in the "buy" (green)
state, flat while in the "sell" (red) state. First TTM Scalper strategy in
this repo -- distinct from all TTM Squeeze/TTM Trend entries already
tested.

## Step 6 — Grid test summary
Grid: `param_grid={use_trend_gate:[False,True], trend_window:[20,40,60]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`
-> total_cells=72, passed=23, **pass_fraction=0.319**.
- by_asset_class: equity 23/36 (0.639), crypto 0/36 (0.000, decisive)
- by_vol_regime: low 11/24 (0.458), mid 8/24 (0.333), high 4/24 (0.167)

Best-average-Sharpe config: `use_trend_gate=False` (an SMA trend gate
actively HURT this strategy -- likely because the reversal-confirmation
signal itself already captures short-term directional turns, and gating it
by a slower trend filter delays/filters out valid entries) for both QQQ and
SPY.

## Step 7 — Validators (best config, full sample)

| Symbol | Sharpe | MDD | TC net Sharpe | Walk-forward | Param sens |
|---|---|---|---|---|---|
| QQQ | 1.204 (pass) | pass | pass | pass | pass |
| SPY | 0.866 (**fail**, <1.0, near-miss) | 0.261 (**fail**, near-miss >0.25) | pass | pass | pass |

Crypto (BTC/USDT, ETH/USDT) decisively rejected at the grid stage (0/36
cells passed) -- the reversal-confirmation pattern doesn't hold up on
crypto's higher-frequency, noisier swing structure at all, not just a
risk-control gap (unlike several other this-cron-trigger crypto rejections
that were vol-targeting-overlay-rescuable).

## Decision
**Accept (QQQ only).** Reject SPY (near-miss on both Sharpe and MDD
simultaneously) and crypto (decisive, 0/36 grid cells). Note for a future
loop: SPY's double near-miss (Sharpe 0.866, MDD 0.261) is close enough that
a per-symbol parameter variant (though this strategy currently has no
tunable parameters besides the trend gate, which hurts performance) or a
position-sizing overlay might rescue it -- but the strategy's near-total
lack of tunable knobs (a pure 4-bar price-action pattern) limits the
rescue options compared to indicator-based strategies this cron trigger.
