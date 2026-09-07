# Down Monday -> Tuesday Reversal (day-of-week seasonality)

**Hypothesis:** Per https://www.quantifiedstrategies.com/tuesday-reversals-in-sp-500/
and https://www.quantifiedstrategies.com/day-of-the-week-effect/, when
Monday's close is lower than the prior session's close ("down Monday"),
going long at Monday's close and exiting at Tuesday's close captures a
recurring mean-reversion edge in US index ETFs. First pure day-of-week
seasonality strategy tested in this repo.

**Strategy file:** `strategies/2026-09-08_down_monday_tuesday_reversal.py`
(`hold_days` param, default 1 = literal 1-day replication of the source rule)

## Grid test (Step 6)

`param_grid={"hold_days": [1, 2, 3]}`, `symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]}`, `vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- 36 total cells, 10 passed (pass_fraction=0.278)
- By asset class: equity 10/18 passed; crypto 0/18 (decisive fail on crypto)
- By vol regime: low 2/12, mid 2/12, high 6/12 (edge concentrated in higher-vol regimes -- consistent with mean-reversion strategies typically working better when moves are larger)
- Best cell: SPY, hold_days=1, high-vol regime, Sharpe 1.64
- Worst cell: QQQ, hold_days=1, low-vol regime, Sharpe -0.51

## Single-config validators (Step 7) -- primary config hold_days=1

| Validator | SPY | QQQ | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.015 PASS | 0.706 FAIL | >= 1.0 |
| Max drawdown | 4.2% PASS | 8.5% PASS | <= 25% |
| TC-survival (5bps/trade) | 0.766 PASS | 0.527 PASS | >= 0.5 |
| Walk-forward (manual 4-split) | 4/4 positive, 1.0 PASS | 4/4 positive, 1.0 PASS | >= 0.75 |
| Parameter sensitivity (hold_days 1/2/3 relative std) | 0.137 PASS | 0.203 PASS | <= 0.5 |

Note: `validation/validators.py::check_walk_forward` raises
`AttributeError: module 'vectorbt.utils' has no attribute 'splitting'` with
the installed vectorbt==1.1.0 (pre-existing repo issue, seen in prior
iterations e.g. 2026-09-08-111/112/113) -- used a manual 4-equal-period split
stand-in instead (per-split Sharpe > 0 counted as pass), consistent with
those prior iterations' documented workaround.

## Decision (Step 8)

**Accept for SPY** (all 5 validators pass on the primary hold_days=1 config,
num_trades=141 over 7.7yr, ~1 trade every ~2 weeks). **QQQ is a near-miss**
(Sharpe 0.706 fails the >=1.0 threshold, but MDD/TC/walk-forward/param-
sensitivity all pass) -- record as scope-limited: this strategy's edge is
SPY-specific, not QQQ-transferable. **Crypto rejected decisively** (0/18
grid cells) -- day-of-week seasonality does not apply to a market that
trades 24/7 with no Friday/Monday closing-price discontinuity, which
matches the a priori expectation for a calendar effect tied to weekly market
closure.
