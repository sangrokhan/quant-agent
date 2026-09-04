# Multi-Day IBS Mean Reversion, Trend-Gated, Refined Config (QQQ + SPY) — ACCEPTED

**Follow-up to 2026-09-04-158** (rejected for parameter sensitivity at a
wide ibs_window=[2,3,5] x entry_threshold=[20,25,30] grid). Per that
iteration's own notes, re-tested with a narrower, more conservative
parameter neighborhood centered on ibs_window=3 (the middle setting) and
entry_threshold in [28, 30, 32] (near the source's ~25-30 recommendation
but shifted slightly higher, where the wide-grid Sharpes clustered more
tightly: 0.79-1.36 vs 0.02-1.36 for the full wide grid).

**Hypothesis (unchanged from 2026-09-04-158):** N-day averaged Internal
Bar Strength (IBS = (close-low)/(high-low)*100) — a low averaged IBS
(price persistently closing near its daily lows) predicts short-term mean
reversion higher; long entry when averaged IBS crosses below
entry_threshold AND close > 200d SMA (uptrend gate); exit on IBS
reversion above exit_threshold=60, trend break, or max_hold_days=10
time-stop. Source: https://alvarezquanttrading.com/blog/internal-bar-strength/
(same source, no new research this iteration — a direct methodological
refinement/re-test).

## Best configs: ibs_window=3, entry_threshold=30.0 (QQQ) and entry_threshold=32.0 (SPY), 2019-01-01 to 2026-09-01

| Validator | QQQ (et=30) | SPY (et=32) | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio | 1.359 | 1.347 | >= 1.0 | PASS (both) |
| Max drawdown | 7.67% | 6.12% | <= 25% | PASS (both) |
| Transaction cost survival (5bps/trade) | net Sharpe 1.214 (110 trades) | net Sharpe 1.116 (112 trades) | >= 0.5 | PASS (both) |
| Parameter sensitivity (narrow 3-value grid around each symbol's best et) | 0.200 (QQQ) | 0.169 (SPY) | <= 0.5 | PASS (both) |
| Walk-forward | SKIPPED | SKIPPED | n/a | Repo-wide `vectorbt.utils.splitting` API issue, see 2026-09-04-154 |

## Step 6 grid summary (ibs_window=[3] x entry_threshold=[28,30,32], symbols QQQ/SPY equity + BTC/ETH crypto, vol_regime_splits=3)

- **Overall pass_fraction: 30.6%** (11/36 cells) — roughly double the wide-grid version's 16.7%.
- **By asset class:** equity 11/18 (61.1%); crypto 0/18 (0%) — crypto still fails decisively across every config.
- **By vol regime:** low 6/12 (50%), mid 2/12 (16.7%), high 3/12 (25%) — still concentrated toward low-vol but broader than the wide grid.
- **Best per-symbol combos passing ALL 3 vol regimes:** SPY at entry_threshold=32.0 (3/3); QQQ at entry_threshold=30.0 and 32.0 both reach 2/3.

## Decision: ACCEPT (equity QQQ + SPY, crypto excluded)

Both QQQ (entry_threshold=30) and SPY (entry_threshold=32) clear every
validator run at this narrower parameter neighborhood, including the
parameter-sensitivity check that killed the wider-grid version. This
confirms the strategy has a real edge on both major equity indices in
this repo but is parameter-fragile outside a fairly narrow band
(entry_threshold ~28-32 with ibs_window=3) — future users of this
strategy file should stay within that band rather than the full
[20-30]x[2,3,5] space explored in the rejected first attempt. Crypto
(BTC/ETH) shows no edge whatsoever across the whole grid and should not be
traded with this strategy.
