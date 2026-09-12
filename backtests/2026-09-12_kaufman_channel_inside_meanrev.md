# Backtest Report: Kaufman "Inside Channel" Linear-Regression Band Mean Reversion

**Strategy file:** `strategies/2026-09-12_kaufman_channel_inside_meanrev.py`
**Hypothesis ID:** 2026-09-12-188
**Source:** https://financial-hacker.com/trading-the-channel/ (Petra Volkova,
covering Perry Kaufman's TASC 5/2025 article "Trading the Channel")

## Hypothesis

Fit a rolling linear-regression line over the last N closes; build an
upper/lower channel from the max/min deviation of price from that line over
the same window (`Zone = zone_factor * (HighDev + LowDev)`, literal source
formula). Kaufman's "Inside Channel" method: go long when price comes within
`Zone` of the lower band, flatten when price comes within `Zone` of the
upper band. No slope/trend-direction filter -- pure band-proximity
mean-reversion, long-only (source's WFO variant also trades short; kept
long-only here per repo convention).

## Grid test (Step 6): `lrc_window` in {20,40,80} x `zone_factor` in
{0.1,0.2,0.35}, symbols QQQ/SPY (equity) + BTC/USDT, ETH/USDT (crypto),
vol_regime_splits=3, 2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.25** (27/108 cells, `min_sharpe=1.0`,
  `max_allowed_mdd=0.25`)
- **By asset class:** equity 27/54 passed; **crypto 0/54 passed** (decisive
  fail -- the regression-channel edge does not transfer to crypto's higher
  baseline volatility/trend character).
- **By vol regime:** low 15/36, mid **0/36** (complete fail in mid-vol
  regime across both symbols/all params), high 12/36.
- **Best cell:** QQQ/SPY equity, low-vol regime, `lrc_window=20,
  zone_factor=0.35` (SPY Sharpe 1.92).
- **Worst cell:** SPY, `lrc_window=80, zone_factor=0.1`, mid-vol regime
  (Sharpe -0.59).
- Full-period (non-regime-split) average Sharpe per config: best QQQ config
  `lw=20/zf=0.35` avg 1.058; best SPY config `lw=40/zf=0.1` avg 1.173 (both
  averaged across the 3 vol-regime terciles).

## Single-config validation (Step 7)

| Symbol | Params | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd pass_frac | Param-sens rel.std | Trades |
|---|---|---|---|---|---|---|---|
| QQQ | lrc_window=20, zone_factor=0.35 | 1.099 (pass, thr 1.0) | 0.174 (pass, thr 0.25) | 1.065 (pass, thr 0.5) | 1.00 (pass, thr 0.75) | 0.314 (pass, thr 0.5) | 32 |
| SPY | lrc_window=40, zone_factor=0.1 | 1.118 (pass, thr 1.0) | 0.207 (pass, thr 0.25) | 1.103 (pass, thr 0.5) | 0.75 (pass, thr 0.75) | 0.127 (pass, thr 0.5) | 9 |

Walk-forward used a manual 4-equal-slice fallback (documented since
2026-09-03-002: `vbt.utils.splitting.RangeSplitter` is broken in this
vectorbt install).

Both configs pass all 5 validators (Sharpe, MDD, transaction-cost survival,
walk-forward, parameter sensitivity).

## Decision: **ACCEPT** (equity only: QQQ, SPY)

Reject scope: crypto (BTC/USDT, ETH/USDT) -- decisive 0/54 grid fail, not
retested at single-config level given the grid's unanimous failure.
Mid-volatility equity regime is also weak (0/36 in the grid, though the
full-period single-config validation above spans all regimes and still
passes headline thresholds) -- this strategy's edge appears concentrated in
low/high-vol regimes, worth flagging for any future regime-gated variant.
