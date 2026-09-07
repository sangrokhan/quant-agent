# CVR3 VIX Market Timing (Larry Connors & Dave Landry)

**Strategy file:** `strategies/2026-09-08_cvr3_vix_reversal_timing.py`
**Source:** https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/cvr3-vix-market-timing

## Hypothesis

Excessive VIX spikes (fear extremes) tend to mean-revert, and SPY/QQQ
often rally during that reversion. Source's own three-rule BUY signal
(all applied to the VIX index itself): (1) VIX daily low > VIX's own
10-day SMA, (2) VIX close >= 10% above its 10-day SMA
(PPO(1,10,1)>=10), (3) VIX close < VIX open (down candle on VIX). Exit:
VIX crosses back below the prior day's 10-day SMA, or a 2-4 day
time-stop. First strategy in this repo trading an equity index using a
SEPARATE real instrument's signal (^VIX, fetched via `data/loaders.py`),
distinct from all prior volatility-PROXY strategies (Williams VIX Fix,
ATR-based) which synthesize a fear proxy from the traded instrument's own
price.

## Grid test summary (Step 6)

`param_grid`: `entry_pct in {8,10,15}`, `max_hold_days in {2,3,4}`;
`vol_regime_splits=3`; symbols: equity QQQ/SPY; crypto BTC/USDT/ETH/USDT
(explicit falsification check -- no VIX analog exists for crypto, so the
strategy is always flat there by construction).

| asset_class | pass_fraction | low-vol | mid-vol | high-vol |
|---|---|---|---|---|
| equity (QQQ/SPY) | 14/54 (0.259) | 14/18 | 0/18 | 0/18 |
| crypto (BTC/ETH) | 0/54 (0.0, always-flat by construction) | 0/18 | 0/18 | 0/18 |

Best cell: `entry_pct=10, max_hold_days=3`, low-vol regime (SPY), Sharpe
2.35. Edge entirely confined to the low-vol tercile — makes intuitive
sense: VIX spikes of the magnitude this strategy requires (>=10% above
its own 10-day SMA) are themselves more common DURING mid/high-vol
periods, so the "low-vol slice" here likely captures the tail-end
recovery days right after a vol spike subsides, not sustained low-vol
market conditions.

## Single-config validation — best config: entry_pct=10, max_hold_days=3 (63 trades each)

| Symbol | Sharpe | MDD | TC-survival |
|---|---|---|---|
| SPY | ❌ 0.047 | ✅ 0.198 | ❌ -0.008 (net negative after costs) |
| QQQ | ❌ 0.150 | ✅ 0.181 | ❌ 0.102 |

Full-period (all-vol-regime) Sharpe is decisively poor for both symbols
(0.047 SPY, 0.150 QQQ) despite the low-vol grid slice looking attractive
— confirming the edge dilutes to near-zero once mid/high-vol periods
(where this VIX-spike condition is presumably triggered more often) are
included. Transaction costs turn SPY's already-weak edge net negative.

## Decision: **REJECTED** (equity and crypto both)

## Notes for future iterations

This is the first strategy in this repo to use real ^VIX data via
`data/loaders.py` — confirms the loader works for VIX-based ideas going
forward (useful capability for future iterations, e.g. VIX
term-structure or VIX-of-VIX strategies). The specific CVR3 rule itself
does not hold up on the full sample: the source's own examples note
"getting all three rules to align on the same day doesn't happen as
often as one would think" and suggests relaxing to a 3-day rule window to
increase signal frequency — a future iteration could test that relaxation
(any of the 3 conditions occurring within a 3-day window rather than all
on the same bar) if revisiting VIX-timing strategies.
