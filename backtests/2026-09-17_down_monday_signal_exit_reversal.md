# Down-Monday Reversal with Signal-Based Exit (2026-09-17)

## Hypothesis

Per EdgeLab Trading's "Turnaround Tuesday" writeup
(https://edgelabtrading.com/blog/turnaround-tuesday/, read via `browser_exec`
this iteration — search-engine results pointing at Substack articles on the
same topic were paywalled), the disclosed exact rule is:

> "if Monday closes below the previous trading day's close, buy at Monday's
> close. Exit: sell at the first daily close above the previous day's high."

The source reports (QQQ, 2003–2026, 0.05% round-trip commission): in-sample
(2003-2018) Sharpe 0.89, out-of-sample (2019-2026) Sharpe 1.17, MDD -9.9%;
independent confirmation on SPY OOS Sharpe 1.23, MDD -11.3%; time-in-market
only ~18-25%.

This repo already had two related-but-distinct entries:
- `2026-09-08-116` "Down Monday -> Tuesday": same single-down-Monday entry
  condition, but a FIXED 1-day hold exit. Accepted SPY only, QQQ near-miss
  (Sharpe 0.706).
- `2026-09-08-135` "Turnaround Tue/Wed 3-day-streak": uses the same
  signal-based exit (close > yesterday's high) but requires a 3-day decline
  entry trigger on Tue/Wed, not a single down-Monday.

Neither tests "single down-Monday entry + signal-based exit" — the
combination EdgeLab's rule actually describes — so this is a distinct,
source-grounded novelty-checked hypothesis, not an invented recombination.

## Strategy file

`strategies/2026-09-17_down_monday_signal_exit_reversal.py`

- Entry: today is Monday AND Monday's close < previous session's close.
- Exit: close crosses above the *previous day's high* (source's exact rule),
  or a `max_hold_days` time-stop backstop (source discloses none; added as
  standard risk control and included in the parameter grid).

## Grid test (`scripts/run_grid_down_monday_signal_exit.py`)

`param_grid={"max_hold_days": [5, 10, 15]}`, symbols `{equity: [QQQ, SPY],
crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`. 36 cells total.

- `pass_fraction`: 0.306 (11/36)
- `by_asset_class`: equity 11/18, crypto 0/18 (decisive fail)
- `by_vol_regime`: low 1/12, mid 4/12, high 6/12 (edge concentrated in
  mid/high-vol regimes — consistent with a panic-Monday mean-reversion
  mechanism)
- `best_cell`: SPY, max_hold_days=15, high-vol regime, Sharpe 2.13
- `worst_cell`: ETH/USDT, max_hold_days=10, low-vol regime, Sharpe -0.43

## Full-sample validators (`scripts/validate_down_monday_signal_exit.py`, max_hold_days=10, QQQ+SPY, 2019-2026)

| Validator | QQQ | SPY | Threshold | Pass |
|---|---|---|---|---|
| Sharpe ratio | 1.273 | 1.515 | ≥1.0 | ✅ both |
| Max drawdown | 0.091 | 0.118 | ≤0.25 | ✅ both |
| TC survival (10bps/trade, 126/133 trades) | net Sharpe 1.028 | net Sharpe 1.166 | ≥0.5 | ✅ both |
| Walk-forward (manual 4-split fallback; `vectorbt.utils.splitting` missing in installed vectorbt 1.1.0, same known issue as prior entries) | 4/4 splits positive (0.82, 2.36, 0.92, 0.97) | 4/4 splits positive (0.89, 3.16, 1.67, 1.05) | ≥0.75 pass_fraction | ✅ both (1.0) |
| Parameter sensitivity (max_hold_days ∈ {5,10,15} on QQQ, Sharpe 1.183/1.273/1.308) | relative_std 0.042 | — | ≤0.5 | ✅ |

## Decision: ACCEPT (equity only — QQQ + SPY)

All 5 validators pass for both equity symbols. Crypto is decisively rejected
(0/18 grid cells) — the strategy is scoped to equity only per the grid's
honest breakdown. Config: `max_hold_days=10` (mid-range of the tested grid;
15 is marginally better full-sample but 10 is more conservative against the
time-stop rarely-binding in practice — trade count and Sharpe are close
across 5/10/15, per the low parameter-sensitivity result).
