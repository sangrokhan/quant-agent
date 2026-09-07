# Gap-Down Long (ATR-drop entry + SMA/target/time exit)

**Hypothesis:** Per https://www.quantifiedstrategies.com/gap-down-strategy-in-stocks-going-long/,
a gap-down day (today's high < yesterday's low) with below-average volume
(controlled, non-panic selloff) followed by a further 0.5x ATR(50) drop
from the NEXT day's open (capitulation confirmation) is a long entry; exit
on close > 10-day SMA, +7.5% target, or a 15-day time-stop. Distinct from
already-rejected same-day gap-fade variants in this repo (2026-09-03-010,
2026-09-08-016) -- this is a multi-day-hold, volume-filtered, delayed-entry
mechanic.

**Strategy file:** `strategies/2026-09-08_gap_down_atr_sma_exit.py`

## Grid test (Step 6)

`param_grid={"entry_atr_mult": [0.3, 0.5, 0.7], "target_gain": [0.05, 0.075]}`,
`symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- 72 total cells, 4 passed (pass_fraction=0.056) -- decisive fail
- By asset class: equity 4/36, crypto 0/36
- By vol regime: low 2/24, mid 2/24, high 0/24
- Best cell: SPY, entry_atr_mult=0.3/target_gain=0.05, low-vol regime, Sharpe 1.15
- Worst cell: QQQ, entry_atr_mult=0.5/target_gain=0.05, high-vol regime, Sharpe -0.03

## Single-config validators (Step 7) -- best config entry_atr_mult=0.3/target_gain=0.05

| Metric | SPY | QQQ |
|---|---|---|
| Sharpe | 0.585 FAIL | 0.080 FAIL |
| Max drawdown | 6.9% PASS | 9.6% PASS |
| TC-survival (10bps) | 0.501 PASS (marginal) | 0.060 FAIL |
| num_trades | 12 | 5 |

## Decision (Step 8)

**Reject.** Grid pass_fraction only 5.6% (4/72), and the best grid cell's
isolated low-vol-regime Sharpe (1.15) does not hold up full-sample on
either equity symbol (SPY 0.585, QQQ 0.080 -- both fail the >=1.0
threshold). Signal is also extremely sparse (5-12 total trades over 7.7yr
on the primary equities), consistent with a compound multi-condition filter
(gap-down + low-volume + next-day ATR-drop trigger) that rarely fires and
produces high-variance, unreliable results. Crypto rejected decisively
(0/36 cells) as expected -- no discrete overnight session gap exists in a
24/7 market.
