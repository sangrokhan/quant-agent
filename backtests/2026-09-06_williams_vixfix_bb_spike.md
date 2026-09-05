# Williams VIX Fix Bollinger-Band Spike Oversold Bounce — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_williams_vixfix_bb_spike.py`
**Source:** https://pineify.app/resources/blog/cm-williams-vix-fix-finds-market-bottoms-indicator-tradingview-pine-script

## Hypothesis

Larry Williams' VIX Fix (WVF = 100*(HighestClose(N)-Low)/HighestClose(N))
is a synthetic, options-free fear/volatility proxy. A spike of WVF above
its own rolling Bollinger upper band (2 std) signals statistically extreme
panic selling, historically preceding a short-term bounce. Long entry on
the spike; exit when WVF reverts below its own Bollinger midline, or a
max_hold_days time-stop.

## Grid-test summary (Step 6)

Grid: `wvf_window in {14,22}`, `bb_std in {2.0,2.5}`, `max_hold_days in
{5,10}`, symbols `{QQQ, SPY}` (equity) x `{BTC/USDT, ETH/USDT}` (crypto), 3
vol-regime terciles, 2018-01-01..2026-09-01.

- **Overall pass fraction:** 16/96 = 16.7%
- **By asset class:** equity 16/48 (33.3%); crypto 0/48 (0%) — decisive
  crypto rejection.
- **By vol regime:** low 16/32 (50%), mid 0/32 (0%), high 0/32 (0%) —
  striking: ALL passes are confined to the low-vol tercile; the strategy
  fails completely in mid/high volatility, which is somewhat counter to the
  premise (a "panic spike" indicator failing specifically in higher-vol
  conditions where panics are more common) -- suggests the low-vol tercile
  passes may reflect a handful of shallow, quickly-mean-reverting dips
  rather than genuine capitulation-bounce trades.
- **Best cell:** SPY, low-vol, wvf_window=14/bb_std=2.0/max_hold_days=5,
  Sharpe 2.56 (single tercile, not full-sample representative).
- **Worst cell:** QQQ, high-vol, wvf_window=22/bb_std=2.5/max_hold_days=10,
  Sharpe -0.57.

## Single-config validator results (best grid cell config, full sample)

`wvf_window=14, bb_std=2.0, max_hold_days=5`

### SPY (2018-01-01 .. 2026-09-01)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 0.596 | >= 1.0 | ❌ |
| Max drawdown | 16.5% | <= 25% | ✅ |
| TC survival (10bps/trade, 75 trades) | net Sharpe 0.450 | >= 0.5 | ❌ |
| Walk-forward (4 splits) | 3/4 positive (75%) | >= 75% | ✅ |
| Parameter sensitivity | relative std 0.16 | <= 0.5 | ✅ |

### QQQ (2018-01-01 .. 2026-09-01), same config

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 0.908 | >= 1.0 | ❌ (near-miss) |
| Max drawdown | 9.6% | <= 25% | ✅ |
| TC survival (10bps/trade, 71 trades) | net Sharpe 0.789 | >= 0.5 | ✅ |
| Walk-forward (4 splits) | 4/4 positive (100%) | >= 75% | ✅ |
| Parameter sensitivity | relative std 0.62 | <= 0.5 | ❌ |

QQQ is a near-miss on Sharpe (0.908 vs 1.0 threshold) but fails parameter
sensitivity (0.62 vs 0.5 threshold) -- the 8-cell param grid ranges from
Sharpe -0.08 to 0.91, too wide a spread to trust this exact config as
robust.

## Decision

**Reject.** Neither symbol clears all validators: SPY fails Sharpe and
TC-survival; QQQ is a Sharpe near-miss but fails parameter sensitivity
(fragile across nearby parameter values). Crypto rejected decisively (0/48
grid cells). The striking low-vol-only pass pattern (0% in mid/high vol)
also undercuts the "panic spike" economic rationale and suggests the
apparent edge may be a shallow-dip-buying artifact rather than genuine
capitulation timing.
