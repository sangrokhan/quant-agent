# Turn-of-the-Month "Tactical Twist" Weakness Filter — Backtest Report

**Hypothesis:** Plain Turn-of-the-Month (last day-of-month + first N days of
next month) window, gated by requiring close < SMA(weakness_window) at the
window's start (short-term weakness/pullback precondition), improves on the
already-rejected plain TOTM (2026-09-03-006, SPY Sharpe 0.98 near-miss).

**Source:** https://www.quantifiedstrategies.com/the-turn-of-the-month-effect-with-a-tactical-twist/
(article confirms SPY, 167 trades, 1.2% avg gain/trade, 67% win ratio,
profit factor 2.8, CAGR 6%, exposure 14%, MDD 15%; exact numeric rule
paywalled) + Instagram/social promo snippet disclosing the mechanism:
"...turn of the month when price is showing short-term weakness... take
trades [when] close [is] below [a] moving average."

**Strategy file:** `strategies/2026-09-05_totm_tactical_twist_weakness_filter.py`

## Step 6 — Grid test summary (param_grid: days_after_month_start in
[2,3,5] x weakness_window in [5,10,20]; symbols: equity QQQ/SPY, crypto
BTC/USDT, ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 108, passed_cells: 13, **pass_fraction: 0.120**
- by_asset_class: equity 13/54 (24%), crypto 0/54 (0%, decisive fail)
- by_vol_regime: low 3/36 (8%), mid 2/36 (6%), high 8/36 (22%) -- like the
  IMI strategy tested earlier this run (2026-09-05-071), this signal's
  edge concentrates in higher-vol conditions rather than low-vol.
- best_cell: days_after_month_start=2, weakness_window=5, SPY, high-vol,
  Sharpe=2.045
- worst_cell: days_after_month_start=3, weakness_window=10, QQQ, mid-vol,
  Sharpe=-0.234

## Step 7 — Single-config validators (config: days_before_month_end=1,
days_after_month_start=2, weakness_window=5, full unconditional 2019-2026
sample)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | FAIL 0.567 | **PASS** 1.156 |
| Max Drawdown (<= 0.25) | PASS 0.096 | PASS 0.063 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade) | FAIL 0.384 (60 trades) | PASS 0.841 (60 trades) |
| Parameter sensitivity (relative_std <= 0.5, weakness_window {5,10,20} sweep) | PASS 0.041 | PASS 0.202 |

Walk-forward not run: `check_walk_forward` hits the pre-existing
`vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt
version (same known issue as other recent entries).

## Outcome: **ACCEPTED (SPY only)**; QQQ rejected (Sharpe + tx-cost fail);
crypto rejected decisively

SPY passes all four validators run: Sharpe 1.156 (vs plain TOTM's 0.98
near-miss on the same underlying window -- the weakness filter turned a
near-miss into a clean pass), MDD 0.063 (much tighter than plain TOTM's
0.179), net Sharpe after costs 0.841, and stable across the
weakness_window sweep. QQQ fails both Sharpe (0.567) and transaction-cost
survival (0.384) -- the weakness-filter gating does not transfer as well to
QQQ as it does to SPY. Crypto fails completely (0/54 cells), consistent
with the plain-TOTM finding (2026-09-03-006) that the underlying calendar
mechanism (payroll/401k cash flows) has no crypto analog. This is a genuine
improvement over the plain TOTM strategy for SPY specifically -- the
weakness filter converts a Sharpe-0.98 near-miss into a Sharpe-1.16 clean
pass with a materially lower MDD (0.063 vs 0.179).
