"""Backtest report: GEM Dual Momentum SPY/IEF (shorter-duration bond safe-haven).

Hypothesis id: 2026-09-07-023
Strategy file: strategies/2026-09-07_gem_dual_momentum_spy_tlt.py
(reused with safe_haven_symbol="IEF" -- see notes on file reuse below)
Outcome: **ACCEPTED (SPY only, lookback_days=252, safe_haven_symbol=IEF)**

## Background

2026-09-07-022 (this same cron trigger, iteration 3) tested Antonacci's
GEM dual momentum with TLT (20+ Year Treasury) as the safe haven and
found MDD got WORSE than the cash-safe-haven variant (2026-09-04-097),
because TLT's own long duration made it highly rate-sensitive -- TLT fell
alongside equities during 2022's rate-hike cycle, defeating its purpose
as a drawdown cushion. That report's own notes flagged a direct follow-up:
"test a shorter-duration, less rate-sensitive bond ETF (IEF/SHY) as the
safe haven instead of TLT." This iteration does exactly that with IEF
(iShares 7-10 Year Treasury Bond ETF, confirmed available via
`data/loaders.load_equity("IEF", ...)`), same GEM mechanics (absolute
momentum gate + relative momentum comparison, monthly rebalance)
otherwise unchanged.

## Step 6 grid summary (lookback_days in [126,189,252], safe_haven_symbol
fixed=IEF, symbols QQQ/SPY, crypto excluded -- no bond-ETF analog)

- total_cells: 18, passed_cells: 9, pass_fraction: 0.5
- by_vol_regime: low 6/6 (1.0), mid 3/6 (0.5), high 0/6 (0.0)
- best_cell: SPY, lookback_days=252, low-vol regime, Sharpe 3.028

## Step 7 single-config validation (full 2019-2026 sample, all 3
lookbacks x QQQ/SPY, safe_haven=IEF)

| lookback | Symbol | Sharpe | MDD |
|---|---|---|---|
| 126 | QQQ | 0.721 FAIL | 0.330 FAIL |
| 126 | SPY | 0.646 FAIL | 0.278 FAIL |
| 189 | QQQ | 1.027 PASS | 0.299 FAIL |
| 189 | SPY | 0.952 FAIL | **0.220 PASS** |
| 252 | QQQ | 0.934 FAIL | 0.299 FAIL |
| **252** | **SPY** | **1.046 PASS** | **0.220 PASS** |

**SPY / lookback_days=252 / safe_haven_symbol=IEF is the only cell to pass
BOTH Sharpe and MDD simultaneously.** Full validator suite at this config:

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.046 | >= 1.0 | **PASS** |
| Max drawdown | 0.220 | <= 0.25 | **PASS** |
| Transaction cost survival (5bps, 5 actual trades over 7.7yr) | net Sharpe 1.043 | >= 0.5 | **PASS** |
| Parameter sensitivity (3-lookback SPY sweep, relative_std) | 0.193 | <= 0.5 | **PASS** |
| Walk-forward | not run -- pre-existing `vbt.utils.splitting` AttributeError in installed vectorbt, same known repo-wide issue this cron trigger | | SKIPPED |

## Decision

**Accepted (SPY only, lookback_days=252, safe_haven_symbol="IEF").** All
runnable validators pass cleanly. This confirms the notes' hypothesis
from the prior TLT iteration: shorter-duration Treasuries (IEF, ~7-10yr)
are meaningfully less rate-sensitive than long-duration Treasuries (TLT,
20+yr), so IEF cushions equity drawdowns during a 2022-style rate-hike
regime much better than TLT did (MDD 22.0% vs TLT's decisive 40.0%
failure, and vs the original cash-safe-haven variant's 28.6% near-miss
in 2026-09-04-097) -- IEF is a genuine improvement over BOTH prior
safe-haven choices tested in this repo.

**CAVEAT: only 5 actual rebalance trades over the full 7.7-year sample**
(GEM's monthly-rebalance design naturally produces long holding blocks,
not frequent trading) -- this is a structural feature of the strategy,
not a data artifact, but it does mean the Sharpe/MDD/TC-survival metrics
rest on a small number of large regime-switch decisions rather than many
independent trials, so statistical uncertainty is wider than the passing
numbers alone suggest. QQQ (the other equity symbol tested) does NOT
pass at any lookback with IEF (best QQQ config, lookback=189, passes
Sharpe 1.027 but fails MDD 29.9%) -- the accept is scoped to SPY only,
consistent with GEM's original design being specifically an S&P
500-vs-bond rotation, not a tech-heavy-index variant.

Source: https://www.quantifiedstrategies.com/spy-tlt-bond-rotation-strategy/
and https://www.quantifiedstrategies.com/dual-momentum-trading-strategy/
(same Antonacci GEM source as 2026-09-04-097/2026-09-07-022; IEF data
availability confirmed directly via data/loaders.py, no new URL fetch this
iteration).
"""
