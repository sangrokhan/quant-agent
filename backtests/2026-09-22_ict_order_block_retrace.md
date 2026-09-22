# ICT Order Block Retrace — Backtest Report

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_ict_order_block_retrace.py`
**Source:** Ali Casey, StatOasis, "I Backtested ICT / Smart Money Concepts — What Survives"
(https://statoasis.com/overfit/research/ict-backtest-what-survives), read via
`browser_exec` this iteration (`web_search` DDGS backend TLS-errored on all
queries attempted this iteration).

## Hypothesis

The source codified 4 ICT/Smart Money Concepts entries and ran 648 backtests
on SPY/QQQ/DIA/IWM. Of the four, "Order Block" (a down-close bar confirmed by
a later up-impulse clearing `M x ATR20`, whose own range becomes a
support/retrace zone) showed the most structure: 81.5% of its 18 SPY variants
beat a frequency-matched random baseline, and it had the strongest (though
still sub-significance, t=+1.22) forward-return edge of the four ICT
concepts at the 5-day horizon. This repo re-tests the same codified rule
against this repo's own Sharpe/MDD/walk-forward/TC bar (a different, often
more tractable hurdle than the source's own "beat buy-and-hold on net
profit" bar, which none of the 648 backtests cleared).

## Grid test summary (Step 6)

Grid: `confirm_bars` in {3,5,8} x `atr_mult` in {0.75,1.0,1.5} x `hold_days`
in {5,10}, on QQQ/SPY (equity) and BTC/USDT, ETH/USDT (crypto), 3 realized-vol
regime terciles (low/mid/high), 2016-01-01 to 2026-09-01.

- **Total cells:** 216, **passed:** 56 (pass_fraction **0.259**)
- **By asset class:** equity 55/108 passed; crypto 1/108 passed (decisively
  crypto-unsuitable)
- **By vol regime:** low 36/72; mid 20/72; high 0/72 (edge concentrated in
  low-vol regime, fails entirely in high-vol regime — a real regime
  dependency, not a fluke)
- **Best cell:** SPY, confirm_bars=5, atr_mult=1.5, hold_days=10, low-vol
  regime, Sharpe 2.644
- **Worst cell:** SPY, confirm_bars=8, atr_mult=1.5, hold_days=5, high-vol
  regime, Sharpe -0.222

Primary config selected from grid aggregation (best average full-sample
Sharpe across QQQ/SPY, all vol regimes): `confirm_bars=5, atr_mult=1.0,
hold_days=10`.

## Single-config validators (Step 7) — QQQ

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **True** | 1.198 | 1.0 |
| Max drawdown | **False** | 0.364 | 0.25 |
| TC survival (net Sharpe, 10bps/trade, 434 trades) | True | 0.792 | 0.5 |
| Walk-forward (4 splits) | True | 1.0 pass fraction | 0.75 |
| Parameter sensitivity | True | rel std 0.105 | 0.5 |

## Single-config validators (Step 7) — SPY

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **False** | 0.724 | 1.0 |
| Max drawdown | **False** | 0.308 | 0.25 |
| TC survival | **False** | 0.312 | 0.5 |
| Walk-forward | True | 1.0 | 0.75 |
| Parameter sensitivity | True | rel std 0.145 | 0.5 |

## Decision: REJECTED

QQQ passes 4/5 validators (Sharpe, TC-survival, walk-forward, parameter
sensitivity all comfortably clear) but fails max-drawdown decisively (0.364
vs 0.25 threshold — not a near-miss). SPY fails Sharpe, MDD, and TC-survival.
Consistent with this repo's grid finding that the edge is concentrated in
the low-vol regime and vanishes entirely in the high-vol tercile (0/72
cells passed) — the strategy has no defense against a sustained drawdown
event (e.g. holds through crashes with a fixed 10-day time exit and no
stop-loss). A future iteration could attempt the standard rescue pattern
used elsewhere in this repo (SMA(200) trend gate and/or a formation-price
hard stop-loss, per `strategies/2026-09-08_formation_price_stoploss_trend.py`)
to address the MDD failure specifically, since the entry-quality metrics
(Sharpe, walk-forward, parameter stability) are otherwise sound on QQQ.
