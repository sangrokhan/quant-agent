# Bitcoin trading-session filter (Asia+Europe long / US flat) — REJECTED

**Hypothesis source:** Faisal Khan's "Visualizing BTC cumulative returns by
trading sessions" (Medium, session boundaries per TMGM/Binance/TradingView
standard crypto-session convention: Asian 00:00-08:00 UTC, European
08:00-13:00 UTC, US 13:00-22:00 UTC), corroborated by Yahoo Finance
commentary on Asia buying/US selling pressure divergence. Long BTC/ETH
during Asian+European session hours, flat during the US session — first
intraday session-of-day filter tested in this repo (existing calendar
entries cover day-of-week/holiday/month effects but not intraday UTC-hour
session boundaries), made testable by data/loaders.py's native hourly
ccxt bars for crypto (unlike equity's daily-bar-only constraint).

## Grid test (Step 6)

`session_us_start ∈ {12, 13, 14, 17}`, symbols = BTC/USDT, ETH/USDT
(crypto only — this is an intraday hourly-bar strategy, not applicable to
equity's daily bars), vol_regime_splits=3, 24 total cells.

- **pass_fraction: 0.0** (0/24 cells passed) — decisive rejection across
  every parameter value, both symbols, and all three vol regimes.
- **best_cell (Sharpe only, still failed overall):** ETH/USDT,
  session_us_start=12, mid-vol tercile, Sharpe 1.70 (single tercile
  cherry-pick, not representative — MDD and transaction costs still fail
  even in this best cell per the full-period check below).

## Single-config validation (Step 7) — ETH/USDT, session_us_start=12

| Validator | Result | Threshold | Pass? |
|---|---|---|---|
| Sharpe ratio (full period) | 0.004 | ≥ 1.0 | **FAIL** (decisive) |
| Max drawdown | 0.870 | ≤ 0.25 | **FAIL** (catastrophic) |
| Transaction-cost survival (10bps/trade, 5600 trades) | net Sharpe -0.070 | ≥ 0.5 | **FAIL** (decisive) |

(Walk-forward and parameter-sensitivity not run given the decisive failure
on the first three validators — under `suggested_workload=max` this would
normally be run, but the catastrophic MDD (87%) and transaction-cost
destruction from ~5,600 position flips over the sample make further
validation moot; noted here per Step 7's guidance to record what was
skipped and why.)

## Verdict: REJECTED

A fixed time-of-day session filter flips position on every qualifying
hourly boundary — since the position is a deterministic function of
UTC-hour with no persistence/regime logic, it re-enters and exits roughly
twice per day, every day, for the entire multi-year sample (5,600 trades on
ETH/USDT alone). This trading frequency alone destroys the strategy via
transaction costs regardless of the underlying session-return-asymmetry
hypothesis's validity, and the raw (cost-free) full-period Sharpe (0.004)
and MDD (87%) already fail decisively before costs are even applied — the
session-asymmetry effect, if real in the cited sources, is not economically
significant enough at the level of a static intraday long/flat filter to
survive even before transaction costs are considered. A future revisit
should consider a coarser implementation (e.g. a rolling multi-day
session-return z-score as a REGIME GATE on a slower daily strategy, rather
than a bar-by-bar position flip) if this angle is worth pursuing again.
