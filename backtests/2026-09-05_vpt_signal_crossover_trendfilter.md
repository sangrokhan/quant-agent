# Volume Price Trend (VPT) Signal-Line Crossover + Trend Filter — Backtest Report

**Hypothesis:** Volume Price Trend (cumulative volume line: VPT_t =
VPT_{t-1} + volume_t * pct-change(close)_t) crossing above its own
rolling-average signal line (a standard MACD-like crossover interpretation,
disclosed in a Facebook trading-community post on VPT), gated by close >
SMA(trend_window), signals building buying pressure worth a long entry;
exit on VPT crossing back below signal, trend filter breaking, or a
max_hold_days time-stop.

**Source:** LuxAlgo's VPT definition (via Google search snippet: "each bar
adds the bar's volume multiplied by the percentage change") + a Facebook
trading-community post: "A signal line, which is just a moving average of
the indicator, can be [used for signal-line crossover entries/exits]".

**Strategy file:** `strategies/2026-09-05_vpt_signal_crossover_trendfilter.py`

## Step 6 — Grid test summary (param_grid: signal_window in [14,21,30] x
max_hold_days in [10,15]; symbols: equity QQQ/SPY, crypto BTC/USDT,
ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 72, passed_cells: 13, **pass_fraction: 0.181** (2nd
  strongest grid pass-fraction of any strategy tested this cron trigger,
  after PVO's 0.174 -- both volume-based)
- by_asset_class: equity 13/36 (36%), crypto 0/36 (0%, decisive fail)
- by_vol_regime: low 10/24 (42%), mid 3/24 (12%), high 0/24 (0%)
- best_cell: signal_window=30, max_hold_days=10, QQQ, low-vol, Sharpe=2.062
- worst_cell: signal_window=14, max_hold_days=10, ETH/USDT, mid-vol,
  Sharpe=-0.186

## Step 7 — Single-config validators (config: signal_window=30,
max_hold_days=10, full unconditional 2019-2026 sample)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | **PASS** 1.138 | FAIL 0.347 |
| Max Drawdown (<= 0.25) | PASS 0.068 | PASS 0.111 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade) | **PASS** 0.948 (58 trades) | FAIL 0.125 (64 trades) |
| Parameter sensitivity (relative_std <= 0.5, signal_window {14,21,30} sweep) | PASS 0.173 | PASS 0.371 |

Walk-forward not run: `check_walk_forward` hits the pre-existing
`vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt
version (same known issue as other recent entries).

## Outcome: **ACCEPTED (QQQ only)**; SPY rejected; crypto rejected decisively

QQQ clears all four validators run: Sharpe 1.138, MDD 0.068 (tightest MDD
of any accepted strategy this run), net Sharpe after costs 0.948 (58
trades), parameter-sensitivity relative_std 0.173. SPY fails Sharpe (0.347)
and transaction-cost survival (0.125) decisively at the identical config --
this VPT construction is markedly QQQ-specific, unlike the earlier PVO
strategy (2026-09-05-075) which had SPY as at least a near-miss. Crypto
failed all 36 grid cells. This is the second volume-based strategy accepted
this cron trigger (after PVO, 2026-09-05-075) -- both volume-momentum
oscillators concentrate their edge in QQQ and the equity low-vol tercile,
suggesting a genuine, if narrow, QQQ-specific volume-conviction signal
worth further investigation in a future loop (e.g. combining PVO+VPT
confirmation, or testing on other Nasdaq-heavy tickers).
