# David Varadi Oscillator (DVO) Mean Reversion with Trend Filter

**Hypothesis:** Per the David Varadi Oscillator (DVO), transcribed at
https://www.quantifiedstrategies.com/david-varadi-oscillator/ : DVO
detrends price via an n-period SMA of the ratio (Close/MedianPrice), then
takes a rolling percent-rank of that detrended ratio over a lookback window
(0-100 scale). Source's own stated rationale: reduces the trend component
so the oscillator tracks individual price swings more cleanly than RSI
("helps traders identify buy opportunities after pullback swings and sell
opportunities at the end of impulse swings"). We test long-only mean
reversion: long when DVO < entry_threshold gated by close above a
200-day SMA trend filter (matching the source's stated usage guidance:
"in an uptrend, you only look for a buy signal... at key support levels"),
exit on DVO > exit_threshold or a max_hold_days time-stop.

Source: https://www.quantifiedstrategies.com/david-varadi-oscillator/
(formula fully disclosed; exact numeric trading rules/AmiBroker code are
paywalled members-only, so entry/exit thresholds here are our own grid
sweep, not the source's exact published values.)

## Step 6 — Grid test (entry_threshold in {10,15,20}, exit_threshold in
{60,70}, max_hold_days in {7,10}, equity={QQQ,SPY}, crypto={BTC/USDT,
ETH/USDT}, vol_regime_splits=3, 2019-01-01 to 2026-09-01)

- Total cells: 144, passed: 33, **pass_fraction = 0.229**
- By asset class: equity 33/72 passed, **crypto 0/72 passed** (decisive fail)
- By vol regime: low 12/48, mid 6/48, high 15/48 — edge present across ALL
  THREE regimes (unlike most prior strategies in this repo, which typically
  concentrate in only one regime)
- Best avg-Sharpe config across QQQ+SPY: entry_threshold=15,
  exit_threshold=70, max_hold_days=7 (avg Sharpe 1.119, 4/6 cells passed)
- Best single cell: QQQ, entry=10/exit=60/hold=7, low-vol, Sharpe 1.482

## Step 7 — Single-config validators (entry_threshold=15, exit_threshold=70,
max_hold_days=7, full 2019-2026 sample, both QQQ and SPY)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | PASS 1.072 | PASS 1.110 |
| Max Drawdown (<= 0.25) | PASS 0.141 | PASS 0.081 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade) | PASS 0.914 (77 trades) | PASS 0.881 (70 trades) |
| Walk-forward (manual 4-split, sharpe>0 required, since `check_walk_forward` hits the pre-existing `vbt.utils.splitting` AttributeError bug) | PASS 3/4 splits | PASS 3/4 splits |
| Parameter sensitivity (relative_std <= 0.5, over the 12 QQQ param combos from Step 6's grid, avg Sharpe across vol regimes per combo) | PASS 0.186 (mean 0.861, std 0.160) | (shared grid) |

## Outcome: **ACCEPTED** (equity scope: QQQ and SPY, shared config)

All validators pass cleanly on BOTH QQQ and SPY with the same parameter
set (entry_threshold=15, exit_threshold=70, max_hold_days=7,
trend_window=200, sma_window=3, rank_lookback=252) — no per-symbol tuning
needed. Unlike most accepted strategies in this repo (usually QQQ-only,
SPY near-miss), this one clears the bar on both major equity indices with
identical settings, and the grid shows a genuinely low-relative-std,
stable parameter surface (not a narrow lucky corner). Crypto is a decisive
0/72 fail across the whole grid — strategy scope is explicitly equity-only.
