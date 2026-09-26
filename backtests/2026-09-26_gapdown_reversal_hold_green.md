# Backtest Report: SPY/QQQ Gap-Down Reversal (Buy Weak Open, Hold Until Green) (2026-09-26)

**Strategy file:** `strategies/2026-09-26_gapdown_reversal_hold_green.py`
**KB id:** 2026-09-26-010

## Hypothesis

SetupAlpha's "The SIMPLEST Gap-Down Reversal Trading Strategy of All Time"
(https://setup4alpha.substack.com/p/the-simplest-gap-down-reversal-trading,
public disclosed rule — full RealTest script paywalled): buy SPY when the
next session's open is below the previous session's low (single condition,
no filters); hold until SPY "prints a green day". Implemented both
candidate "green day" definitions (`close_gt_open` and
`close_gt_prior_close`) as a param, plus a `max_hold_days=15` safety
time-stop (source rule has none disclosed).

## Grid test (Step 6)

`green_day_definition` in {close_gt_open, close_gt_prior_close} x
`max_hold_days` in {5, 15, 30}, QQQ/SPY + BTC/USDT/ETH/USDT,
vol_regime_splits=3, 2016-2026 (72 cells):

- **pass_fraction = 0.208 (15/72)**
- by_asset_class: equity 15/36, **crypto 0/36** (expected — no discrete
  session gap on 24/7 crypto, confirms this is a genuine equity-session
  phenomenon, not spuriously fit)
- by_vol_regime: low 0/24, mid 9/24, high 6/24
- best_cell: `green_day_definition=close_gt_open, max_hold_days=15`, SPY,
  mid-vol, Sharpe 1.539
- worst_cell: same config, SPY, low-vol, Sharpe 0.201

## Single-config validation (Step 7)

Config: `green_day_definition=close_gt_open, max_hold_days=15`, full sample
2016-2026.

| Metric | QQQ | SPY |
|---|---|---|
| Sharpe | 0.734 (**fail**, <1.0) | 0.782 (**fail**, <1.0) |
| Max Drawdown | 0.166 (pass, ≤0.25) | 0.197 (pass, ≤0.25) |
| Net Sharpe after 10bps costs | 0.356 (**fail**, <0.5) | 0.299 (**fail**, <0.5) |
| Walk-forward (manual 4-split) | 1.0 (pass, ≥0.75) | 1.0 (pass, ≥0.75) |
| Parameter sensitivity (rel. std) | 0.150 (pass, ≤0.5) | 0.146 (pass, ≤0.5) |
| num_trades | 287 | 309 |

## Decision

**REJECT (both QQQ and SPY)**. The strategy's entry condition (open below
prior day's low) fires very frequently on daily bars — 287-309 trades over
~10.5 years is roughly one trade every 9 trading days — which the grid's
mid-vol-tercile Sharpe (1.54 on SPY) masked as a promising cell. Full-sample
single-config validation exposes decisive failures on BOTH Sharpe (<1.0)
and transaction-cost survival (net Sharpe ~0.3-0.36 after just 10bps/trade),
consistent with this repo's established pattern where high trade-frequency
strategies look attractive in a vol-regime-sliced grid but collapse once
realistic turnover costs and the full sample are applied together (same
failure mode flagged in 2026-09-26-006's ETH/USDT cell this cron trigger).
Source's own note that "it did not beat buy-and-hold" is consistent with
this outcome. Crypto's clean 0/36 grid fail is a useful falsification
confirming the mechanism requires a discrete session gap, not spurious
data-mining.

## Source

https://setup4alpha.substack.com/p/the-simplest-gap-down-reversal-trading
(public disclosed entry rule; RealTest script/exact "green day" definition
paywalled — both plausible definitions tested here) — read via
`browser_exec` (web_search surfaced the URL, page content fetched directly).
