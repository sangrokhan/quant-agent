# 2026-09-13 Poor Man's Trend Program (Z-Scored Return/Vol Continuous Sizing) — Backtest Report

**Hypothesis:** Per
https://beyondpassive.substack.com/p/the-missing-asset-120-years-of-global
(read via browser_exec this iteration), a "poor man's trend program"
continuous-exposure rule: signal = trailing-period return / trailing
long-horizon volatility, clipped to [-1,1]; exposure = 0.5 + 0.5*signal
(no leverage, no shorting). Source's own 120-year annual global
multi-asset test (16-country equity/bond sleeves + gold) found this
price-only rule cut max drawdown roughly in half (59%->17%) while holding
return flat, with the benefit concentrated in stagflation regimes,
without ever being told what regime it was in. Also separately validated
by the source on 1968-2020 US daily data with multiple combined lookbacks.

Adapted to this repo's daily-bar single-asset contract: signal = trailing
`lookback_days` annualized return / trailing `vol_window`-day annualized
realized volatility, clipped [-1,1]; weight = 0.5 + 0.5*signal, clipped
[0,1]. First continuous-exposure (non-binary) sizing rule in this repo
based on a clipped return/vol z-score of the asset's own trailing
performance (distinct from the already-accepted pure inverse-vol-TARGETING
overlay 2026-09-08-165, which has no return/direction component).

## Single-config validators (full sample 2000-01-01 to 2026-09-01)

| Symbol | Config | Sharpe | MDD | Approx. rebalances (>5% weight chg) | Net Sharpe (10bps/trade) |
|---|---|---|---|---|---|
| SPY | lookback=252/vol_window=756 | 0.670 (FAIL) | 0.254 (FAIL) | 784 | 0.186 (FAIL) |
| SPY | lookback=126/vol_window=504 | 0.643 (FAIL) | 0.204 (PASS) | 1586 | -0.027 (FAIL) |
| QQQ | lookback=252/vol_window=756 | 0.815 (FAIL) | 0.278 (FAIL) | 733 | 0.413 (FAIL) |
| QQQ | lookback=126/vol_window=504 | 0.752 (FAIL) | 0.280 (FAIL) | 1433 | 0.129 (FAIL) |

Sharpe fails decisively on both symbols at all tested configs, and
transaction-cost survival fails badly — the continuous re-sizing at daily
frequency generates 700-1600+ meaningful weight changes over the sample
(vs the source's own annual-rebalance or slower multi-lookback daily
design), so per-trade cost drag compounds far more than a binary 0/1
position-flip strategy would. Walk-forward/parameter-sensitivity skipped
(already decisively rejected; `validators.check_walk_forward` also errors
in this environment as previously noted).

## Step 6 grid summary (lookback_days in [126,252] x vol_window in [504,756], SPY/QQQ + BTC/USDT/ETH/USDT, vol_regime_splits=3, window 2016-01-01 to 2026-09-01)

- 48 total cells, 14 passed (pass_fraction 0.292)
- **by_asset_class**: equity 14/24 (58%), crypto 0/24 (0%)
- **by_vol_regime**: low 8/16 (50%), mid 6/16 (38%), high 0/16 (0%)
- Best cell: lookback_days=252, vol_window=756, QQQ, low-vol regime, Sharpe 2.105
- Worst cell: lookback_days=126, vol_window=504, SPY, high-vol regime, Sharpe -0.084

## Decision: REJECTED

The 2016-2026 grid shows a genuinely broader pass rate than most rejected
strategies this trigger (spanning low AND mid vol regimes, 58% of equity
cells), suggesting the underlying idea has real merit — but full-sample
(2000-2026, including 2008/2020) Sharpe still falls short of 1.0 on both
symbols, and critically the continuous daily re-sizing mechanic generates
far more turnover than this repo's cost model can tolerate (net Sharpe
collapses to near-zero or negative once 10bps/trade is applied). This
directly reflects the mismatch between the source's own DESIGN
(annual-rebalance in the 120-year test, or a slower multi-lookback-signal
daily version in the 1968-2020 test) and this iteration's naive
"re-evaluate every day" adaptation, which was not source-faithful on
rebalancing cadence.

## Notes for future iterations

- The core sizing IDEA (clipped return/vol signal mapped continuously into
  exposure, rather than a binary on/off gate) is worth retrying with a
  MUCH slower rebalancing cadence (monthly, matching the source's own
  120-year annual-rebalance design, or at minimum only rebalancing when
  the signal moves past a meaningful threshold/hysteresis band) to control
  turnover — this iteration's decisive TC-survival failure is a
  turnover/cost problem, not necessarily evidence the underlying signal
  lacks edge (the grid's 0.292 pass_fraction with broad low+mid-vol
  coverage is one of the stronger grid results logged this cron trigger).
- If revisited, also consider testing the source's OWN documented
  multi-lookback (21/63/126/252-day) combined z-score construction rather
  than this iteration's single-lookback simplification.
