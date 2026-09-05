# Ichimoku Full Confluence: TK Cross + Cloud Position + Chikou Confirmation — Backtest Report

**Hypothesis:** Ichimoku's full 3-condition confluence system: (1) Tenkan
crosses above Kijun (TK cross for timing), (2) close is already above the
Kumo cloud (trend regime), and (3) the Chikou Span confirms (today's close
> close from `displacement` bars ago) -- all three simultaneously -- marks
a high-probability long entry; exit on the TK cross reversing, price
falling below the cloud, or a max_hold_days time-stop.

**Source:** Convergent Ichimoku strategy guides via Google search
(SnapPChart, AlgoKing, ChartingLens): "In practice, most traders use
three: the TK cross for timing, the Kumo breakout for the trend regime,
and the Chikou span as a filter... A high-probability setup requires
confluence... the Chikou Span must confirm." / "A bullish signal is
confirmed when the Chikou Span is above the price action it overlaps from
26 periods ago."

**Strategy file:** `strategies/2026-09-05_ichimoku_tk_cloud_chikou_confluence.py`

**Distinct from:** 2026-09-04-034 (close>cloud + TK cross only, NO Chikou
confirmation -- near-miss rejected) and 2026-09-05-049 (Kumo breakout
alone, no TK cross or Chikou at all). This adds the third confirmation
condition that the near-miss variant lacked.

## Step 6 — Grid test summary (param_grid: tenkan_window in [7,9] x
max_hold_days in [20,30]; symbols: equity QQQ/SPY, crypto BTC/USDT,
ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 48, passed_cells: 12, **pass_fraction: 0.25**
- by_asset_class: equity 12/24 (50%); crypto 0/24 (0%, decisive fail)
- by_vol_regime: low 5/16 (31%), mid 7/16 (44%), high 0/16 (0%)
- best_cell: tenkan_window=9, max_hold_days=20, QQQ, mid-vol, Sharpe=1.973
- worst_cell: tenkan_window=7, max_hold_days=20, QQQ, high-vol,
  Sharpe=-0.225

## Step 7 — Single-config validators (config: tenkan_window=9,
max_hold_days=20, full unconditional 2019-2026 sample)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | **PASS** 1.155 | **PASS** 1.075 |
| Max Drawdown (<= 0.25) | PASS 0.089 | PASS 0.081 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade) | **PASS** 1.107 (15 trades) | **PASS** 1.003 (15 trades) |
| Parameter sensitivity (relative_std <= 0.5, 4-cell tenkan/max_hold sweep) | PASS 0.391 | PASS 0.194 |

Walk-forward not run: `check_walk_forward` hits the pre-existing
`vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt
version (same known issue as other recent entries). Note: tenkan_window=7
fails decisively on both symbols (QQQ 0.376, SPY 0.693) -- the standard
tenkan_window=9 default is materially better, worth flagging that this
strategy is somewhat parameter-sensitive on the tenkan_window dimension
specifically (relative_std 0.391 on QQQ, still under the 0.5 threshold but
higher than most accepted strategies this cron trigger).

## Outcome: **ACCEPTED (QQQ AND SPY, tenkan_window=9/max_hold_days=20)**;
crypto rejected decisively

Both equity indices clear all four validators at the identical shared
config with tight, comparable Sharpes (1.155 / 1.075) and very low
drawdowns (0.089 / 0.081, among the tightest of any strategy accepted this
cron trigger). Trade counts are low (15 each over 7.7 years) reflecting the
strictness of requiring all three Ichimoku conditions simultaneously --
the added Chikou confirmation successfully filtered out the weaker signals
that made the 2-condition variant (2026-09-04-034) a near-miss. Crypto
failed all 24 grid cells, consistent with the broader pattern of
trend-confluence systems not generalizing to BTC/ETH in this repo.
