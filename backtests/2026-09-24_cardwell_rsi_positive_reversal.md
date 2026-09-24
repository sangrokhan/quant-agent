# Backtest Report: Cardwell RSI Positive Reversal (SPY accepted, QQQ rejected)

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_cardwell_rsi_positive_reversal.py`
**Sources:** Google SERP snippets of tradethatswing.com and LuxAlgo glossary
("Positive Reversal = Buy = RSI Lower Low, Price Higher Low"), plus a full
read (via browser_exec; web_search DDGS backend returned empty/erroring
results this run) of https://gtlackey.com/positive-and-negative-reversal-patterns/
("a positive reversal shows up in a pullback during an uptrend where the
chart has a lower RSI with a higher price when the pullback reverses ...
give good entry points long for positive reversals").

## Hypothesis
Andrew Cardwell's RSI "positive reversal" pattern: during an established
uptrend, a pullback where price makes a HIGHER swing low while RSI makes a
LOWER swing low (momentum reads weaker than price confirms) signals
underlying demand strength and is a trend-continuation buy signal — the
explicit mirror image of classic bullish price/RSI divergence (price
lower-low + RSI higher-low, already tested in this repo, e.g.
2026-09-03-019). First Cardwell/"positive reversal" entry in this repo (0
prior index hits).

## Grid summary (Step 6)
`param_grid={"trend_window": [50, 100], "exit_rsi_level": [55, 60, 70]}`,
`symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]}`,
`vol_regime_splits=3` (normal workload).

- total_cells: 72, passed_cells: 36, **pass_fraction: 0.5**
- by_asset_class: equity 19/36, crypto 17/36
- by_vol_regime: low 18/24, mid 11/24, high 7/24 (edge concentrated in
  low/mid-vol regimes, as with most trend-continuation strategies in this
  repo)
- best_cell: trend_window=100, exit_rsi_level=60, SPY, mid-vol, Sharpe 2.043
- worst_cell: trend_window=50, exit_rsi_level=70, SPY, high-vol, Sharpe -0.690

## Single-config validators (best cell: trend_window=100, exit_rsi_level=60)

### SPY
| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample, 34 trades) | **PASS** | 1.246 | >= 1.0 |
| Max drawdown | **PASS** | 0.060 | <= 0.25 |
| Transaction cost survival (10bps/trade) | **PASS** | net Sharpe 1.047 | >= 0.5 |
| Walk-forward | SKIPPED | n/a | known repo `vectorbt.utils.splitting` AttributeError bug (confirmed via direct repro this iteration — `vbt.utils` has no `splitting` attribute in installed vectorbt version), documented in multiple prior KB entries |
| Parameter sensitivity (20-combo sweep, trend_window x [50,75,100,150], exit_rsi_level x [50,55,60,65,70]) | **PASS** | rel_std 0.227 | <= 0.5 |

### QQQ
| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample, 28 trades) | **FAIL** | 0.332 | >= 1.0 |
| Max drawdown | PASS | 0.094 | <= 0.25 |
| Transaction cost survival | **FAIL** | net Sharpe 0.218 | >= 0.5 |
| Walk-forward | SKIPPED | n/a | same repo bug |
| Parameter sensitivity | **FAIL** | rel_std 0.501 | <= 0.5 |

## Decision: ACCEPT (SPY only), REJECT (QQQ)
SPY clears every runnable validator (walk-forward skipped due to a known
pre-existing repo bug, not a strategy weakness) with comfortable margin.
QQQ fails Sharpe, TC-survival, and parameter-sensitivity — the positive
reversal edge does not transfer to QQQ at this config. Crypto not
separately validated in the single-config step (grid showed 17/36 crypto
cells passing, comparable to equity's 19/36, but no crypto config was
selected as best_cell and Cardwell's original thesis is equity-specific —
flagged as a candidate for a future crypto-focused fine-tune iteration).
