# ETH/USDT SuperTrend + Vol-Targeting -- Extension Attempt

Direct follow-up to 2026-09-13-030 (SOL/USDT SuperTrend+vol-targeting,
accepted). Tests whether the same mechanism extends to XRP/USDT, BTC/USDT,
ETH/USDT with per-symbol tuned parameters.

## Search results

- XRP/USDT: no config found (across target_annual_vol 0.08-0.20 x
  multiplier 2.0-3.5 x atr_period 10/14) simultaneously clearing both
  Sharpe>=1.0 and MDD<=0.25.
- BTC/USDT: same, no config found.
- ETH/USDT: best config (atr_period=14, multiplier=2.0,
  target_annual_vol=0.20) is a genuine near-miss:

| Metric | Value | Threshold | Pass? |
|---|---|---|---|
| Sharpe | 1.084 | 1.0 | pass |
| MDD | 0.215 | 0.25 | pass |
| Net Sharpe after costs (10bps) | 0.469 | 0.5 | FAIL (narrow) |
| Walk-forward | 1.0 | 0.75 | pass |
| Parameter sensitivity | 0.089 | 0.5 | pass |

A wider search (target_annual_vol 0.15-0.30 x multiplier 2.0-4.0 x
atr_period 10/14/20) found no config on ETH/USDT clearing all four
validators simultaneously -- widening the ATR-based bands to reduce trade
frequency (and thus transaction-cost drag) also reduces the Sharpe/MDD
combination below threshold.

## Verdict: REJECTED for XRP/BTC/ETH (SOL/USDT remains the sole accept)

The SuperTrend+vol-targeting mechanism from 2026-09-13-030 does not
generalize cleanly to XRP/USDT, BTC/USDT, or ETH/USDT -- SOL/USDT's
specific combination of high volatility and sustained multi-year trend
persistence (both bull and bear) appears to be what makes the underlying
signal + de-risking overlay work; the other three symbols either lack a
config clearing MDD/Sharpe together (XRP, BTC) or clear those two but fail
transaction-cost survival due to higher trade frequency relative to net
edge (ETH, 424 trades over the sample, net Sharpe 0.469 narrowly below the
0.5 threshold). This confirms 2026-09-13-030's own scoping note that the
accepted strategy is SOL/USDT-specific, not a general crypto altcoin
recipe.
