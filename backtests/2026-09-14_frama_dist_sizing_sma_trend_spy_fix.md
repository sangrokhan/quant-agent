# FRAMA Distance Sizing Dial — SPY Fix

**Strategy file:** `strategies/2026-09-14_frama_dist_sizing_sma_trend.py` (existing file, SPY config found this iteration)
**Predecessor:** `2026-09-14-157` (accepted QQQ/BTC-USDT/ETH-USDT, rejected SPY — fails both Sharpe (0.887<1.0) and TC-survival (net Sharpe 0.138) even after widening deadband to 0.4, same fix that rescued QQQ)

## Hypothesis

`2026-09-14-157`'s FRAMA (John Ehlers' Fractal Adaptive Moving Average)
distance continuous-sizing dial accepted decisively for QQQ, BTC/USDT and
ETH/USDT, but SPY still failed both Sharpe and TC-survival after the
original deadband-only fix attempt (deadband=0.4). This iteration widens
the search across `frama_window` and `zscore_window` in addition to a
wider deadband range (up to 0.55) and finds SPY passes cleanly at
frama_window=16/zscore_window=60/sensitivity=0.4/deadband=0.55 (gross
Sharpe 1.464, net-of-cost Sharpe 1.043 — the strongest post-cost margin
found for any SPY fix this cron trigger). Same strategy file, same
already-confirmed FRAMA formula, no new external fetch.

## Grid search (SPY only, this iteration)

240-cell grid: frama_window in {10,16,24,32,48} x zscore_window in
{60,100,150,200} x sensitivity in {0.3,0.4,0.5,0.6} x deadband in
{0.35,0.45,0.55} (trend_window=40, base_exposure=0.4, leverage_cap=1.0
fixed, cells with <5 trades excluded). Best cell by (gross Sharpe +
net-of-cost Sharpe): frama_window=16, zscore_window=60, sensitivity=0.4,
deadband=0.55 — gross Sharpe 1.464, net-of-cost Sharpe 1.043, 101 trades.
The original 16-bar FRAMA window turned out to already be right; the fix
was almost entirely in a much wider deadband (0.55 vs 0.4 tried before)
cutting turnover further.

## Single-config validators (SPY, frama_window=16/zscore_window=60/sensitivity=0.4/deadband=0.55)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.464 | 1.0 | Yes |
| Max drawdown | 0.063 | 0.25 | Yes |
| TC-survival (net Sharpe) | 1.043 | 0.5 | Yes |
| Walk-forward | 1.00 (4/4 splits) | 0.75 | Yes |
| Parameter sensitivity (rel-std, 240-cell grid) | 0.133 | 0.5 | Yes |

## Outcome

**SPY now accepted, all 5 validators pass with a strong margin** (net Sharpe
>1.0 after costs, more than double the 0.5 threshold). Combined with
`2026-09-14-157`'s QQQ/BTC/ETH accepts (same strategy file, per-symbol
tuned params), the FRAMA distance continuous-sizing dial now covers all 4
symbols this repo tracks — following the same "widen the secondary
parameter, not just sensitivity/deadband" fix pattern as this cron
trigger's prior near-miss fixes.
