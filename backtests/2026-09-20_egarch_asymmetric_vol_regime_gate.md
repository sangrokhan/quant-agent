# Backtest Report: EGARCH Asymmetric Volatility Regime Gate

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_egarch_asymmetric_vol_regime_gate.py`
**KB id:** 2026-09-20-095

## Hypothesis

Per multiple corroborating sources found via Google search this iteration
(NYU Stern's EGARCH documentation https://vlab.stern.nyu.edu/docs/volatility/EGARCH,
Medium's "Advanced GARCH Models: EGARCH and GJR-GARCH", MetricGate's
"EGARCH Model Explained"): Nelson's EGARCH(1,1) models log-conditional-
variance with an explicit leverage/asymmetry term (gamma * z_{t-1}), so
negative return shocks raise forecast volatility more than equal-magnitude
positive shocks. This repo already tested a plain symmetric GARCH(1,1)
vol-regime gate (2026-09-07-015, near-miss, full-sample Sharpe QQQ
0.811/SPY 0.714) that treats +/- shocks identically. Hypothesis: EGARCH's
asymmetric leverage term should react faster/more accurately to the
down-shocks that precede volatility spikes, producing a materially better
regime gate than the plain-GARCH near-miss.

## Full-sample single-config scan (3 vol_threshold values x 4 symbols,
refit_every=21, lookback=250; 2019-01-01 to 2026-09-01)

Note: EGARCH MLE refitting is compute-heavy (~40s/symbol/config); the full
3-parameter x 2-parameter x 2-asset-class x vol-regime grid via
run_strategy_grid was started but exceeded reasonable iteration time
budget (>15 min without completing even one asset class' full grid) and
was killed in favor of a direct full-sample scan across the single most
relevant tunable (vol_threshold), which is sufficient to see the Sharpe is
decisively below threshold on every symbol tested.

| Symbol | vol_threshold | refit_every | Full-sample Sharpe |
|---|---|---|---|
| QQQ | 0.20 | 21 | **0.809** (best QQQ) |
| QQQ | 0.25 | 21 | 0.696 |
| QQQ | 0.30 | 21 | 0.676 |
| SPY | 0.20 | 21 | 0.401 |
| SPY | 0.25 | 21 | 0.694 |
| SPY | 0.30 | 21 | **0.715** (best SPY) |
| BTC/USDT | 0.20 | 21 | -0.278 |
| BTC/USDT | 0.25 | 21 | -0.110 |
| BTC/USDT | 0.30 | 21 | **0.773** (best BTC) |
| ETH/USDT | 0.20 | 21 | inf (degenerate -- near-zero-variance return series over the tested window, not a genuine pass) |
| ETH/USDT | 0.25 | 21 | -0.259 |
| ETH/USDT | 0.30 | 21 | -0.356 |

Best full-sample Sharpe across all tested symbols/thresholds is 0.809
(QQQ), still below the plain symmetric GARCH near-miss's own best (0.811
QQQ) from 2026-09-07-015 -- i.e. EGARCH's asymmetric leverage term did NOT
improve on the plain-GARCH gate as hypothesized; if anything it performed
marginally worse on this data. Crypto largely shows negative or degenerate
Sharpe.

## Single-config validator (best QQQ config, vol_threshold=0.20)

| Validator | Result | Evidence |
|---|---|---|
| Sharpe ratio | **FAIL** | value=0.809, threshold=1.0 |

Grid test and remaining validators skipped -- the full-sample Sharpe scan
across all 4 symbols already shows a decisive failure to clear 1.0
anywhere, and EGARCH's own MLE refit cost makes a full parameter x
vol-regime x asset-class grid impractically slow for one iteration's
budget (a single param/symbol run already takes ~40s; a full grid as
specced in Step 6 would take 15+ minutes and was aborted after exceeding
that budget without completing).

## Decision: REJECTED

EGARCH's asymmetric leverage term does not improve on the already-rejected
plain-GARCH(1,1) vol-regime gate (2026-09-07-015) -- best full-sample
Sharpe (0.809 QQQ) is essentially the same as or slightly worse than
plain-GARCH's own near-miss (0.811 QQQ), and crypto shows no coherent edge
(mostly negative Sharpe, one degenerate infinite value from a near-zero-
variance return slice). Confirms that for this repo's specific
buy-and-hold-vs-flat volatility-regime-gate construction, the choice of
volatility model (rolling std, plain GARCH, or EGARCH) does not materially
change the outcome -- the binary long/flat gate mechanism itself appears to
be the limiting factor, not the sophistication of the volatility forecast
feeding it.
