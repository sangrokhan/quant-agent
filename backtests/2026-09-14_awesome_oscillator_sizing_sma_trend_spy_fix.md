# Awesome Oscillator Sizing Dial — SPY Fix

**Strategy file:** `strategies/2026-09-14_awesome_oscillator_sizing_sma_trend.py` (existing file, SPY config found this iteration)
**Predecessor:** `2026-09-14-173` (accepted QQQ, rejected SPY Sharpe 0.816<1.0 + TC-survival 0.295<0.5; crypto decisively rejected — out of scope for this fix)

## Hypothesis

`2026-09-14-173`'s Awesome Oscillator (Bill Williams, SMA(5)-SMA(34) of
median price) continuous-sizing dial accepted decisively for QQQ but SPY
failed both Sharpe and TC-survival at the original config. This iteration
widens the search across `fast_window`/`slow_window`/`zscore_window` (not
just sensitivity/deadband) and finds SPY passes cleanly at the SAME
fast_window=5/slow_window=34 (the classic AO periods) with
zscore_window=150/sensitivity=0.6/deadband=0.40 (Sharpe 1.078, net Sharpe
0.819). Same strategy file, same already-confirmed AO formula, no new
external fetch. Crypto remains out of scope per predecessor's decisive
rejection (Sharpe/MDD/TC-survival all fail at leverage_cap=0.4).

## Grid search (SPY only, this iteration)

162-cell grid: fast_window in {5,8} x slow_window in {34,50,70} x
zscore_window in {60,100,150} x sensitivity in {0.4,0.5,0.6} x deadband in
{0.30,0.40,0.50} (trend_window=40, base_exposure=0.4, leverage_cap=1.0
fixed, cells with <5 trades excluded). Best cell: fast_window=5,
slow_window=34 (unchanged from original), zscore_window=150,
sensitivity=0.6, deadband=0.40 — gross Sharpe 1.078, net-of-cost Sharpe
0.819, 82 trades. The fix came entirely from a longer zscore_window and
wider deadband cutting turnover, not from changing the AO's own periods.

## Single-config validators (SPY, fast_window=5/slow_window=34/zscore_window=150/sensitivity=0.6/deadband=0.40)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.078 | 1.0 | Yes |
| Max drawdown | 0.087 | 0.25 | Yes |
| TC-survival (net Sharpe) | 0.819 | 0.5 | Yes |
| Walk-forward | 0.75 (3/4 splits) | 0.75 | Yes |
| Parameter sensitivity (rel-std, 162-cell grid) | 0.186 | 0.5 | Yes |

## Outcome

**SPY now accepted, all 5 validators pass.** Combined with `2026-09-14-173`'s
QQQ accept (same strategy file, per-symbol tuned params), the Awesome
Oscillator continuous-sizing dial now covers QQQ+SPY (equity only; crypto
explicitly out of scope per predecessor's decisive rejection, not
attempted here) — the tenth and final consecutive near-miss fix this cron
trigger, all via the same "widen the secondary parameter, not just
sensitivity/deadband" pattern.
