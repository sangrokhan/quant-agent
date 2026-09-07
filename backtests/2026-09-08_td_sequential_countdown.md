# TD Sequential Setup + Countdown Confirmation

**Strategy file:** `strategies/2026-09-08_td_sequential_countdown.py`
**Source:** https://pinescriptforge.com/strategy/td-sequential

## Hypothesis

Direct follow-up to already-rejected simple TD Buy Setup
(`2026-09-04-032`, 9-count consecutive-close exhaustion signal alone,
rejected). Source explicitly states "TD 13 Countdown is a stronger
signal" than the Setup alone — a secondary confirmation count (13
cumulative bars where close <= low 2 bars prior, following a completed
Setup) that must also complete. Tests whether adding this rarer,
higher-confidence confirmation layer rescues the previously-rejected
9-count-only idea.

## Grid test summary (Step 6)

`param_grid`: `countdown_count in {9,13}`, `exit_sma_period in {5,10,20}`;
`vol_regime_splits=3`; symbols: equity QQQ/SPY, crypto BTC/USDT/ETH/USDT.

| asset_class | pass_fraction | low-vol | mid-vol | high-vol |
|---|---|---|---|---|
| equity (QQQ/SPY) | 11/36 (0.306) | 2/24 | 1/24 | 8/24 |
| crypto (BTC/ETH) | 0/36 (0.0) | 0/24 | 0/24 | 0/24 |

Best cell: `countdown_count=13, exit_sma_period=10`, low-vol regime
(QQQ), Sharpe 1.72. Crypto rejected decisively across all cells.

## Single-config validation (Step 7) — best config: countdown_count=13, exit_sma_period=10 (QQQ, 10 trades over full period)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ (very close) | 0.974 | 1.0 |
| Max drawdown | ✅ (excellent) | 0.024 | 0.25 |
| Transaction cost survival | ✅ | 0.954 net Sharpe | 0.5 |
| Parameter sensitivity (6-cell equity grid) | ✅ | relative_std 0.468 | 0.5 |

Walk-forward not run given only 10 total trades over the ~7.5-year
sample — a 4-way split would leave each fold with only 2-3 trades,
too few for a meaningful per-split Sharpe estimate.

## Decision: **REJECTED** (very close near-miss, low trade-count caveat)

Sharpe 0.974 is the closest near-miss recorded this cron trigger (0.026
below threshold), with excellent MDD (0.024, far under budget) and
passing TC-survival and parameter-sensitivity. However, the strategy only
generated 10 trades over the full ~7.5-year QQQ backtest (the Countdown
confirmation requirement is, as the source itself notes, rare) — a Sharpe
estimate from 10 trades carries wide statistical uncertainty, and the
grid's own pass_fraction (0.306, concentrated in high-vol not low-vol
unlike most other accepted strategies in this log) suggests limited
robustness beyond this specific best cell.

**Notes for future iterations:** this is worth flagging as a genuine
near-miss for a future revisit — try loosening `countdown_count` to
increase trade frequency (e.g. testing intermediate values 10-12) to get
a more statistically reliable Sharpe estimate, or testing on a longer
equity history if available. The simplified Countdown implementation here
also omits the full DeMark recursion's setup-cancellation/"true low"
qualifying conditions — a more faithful implementation might behave
differently.
