# Backtest Report: 3-State Gaussian HMM Risk-Adjusted-State Regime Filter

**Strategy file:** `strategies/2026-09-09_hmm_3state_sharpe_regime.py`
**Date:** 2026-09-09
**Source:** https://www.quantstart.com/articles/market-regime-detection-using-hidden-markov-models-in-qstrader/
(background/methodology), direct refinement of rejected entry `2026-09-08-173`
(2-state Gaussian HMM, source: https://www.quantifiedstrategies.com/hidden-markov-model-market-regimes-how-hmm-detects-market-regimes-in-trading-strategies/)

## Hypothesis

The prior 2-state HMM regime filter (2026-09-08-173) picked the state with
the HIGHEST MEAN return as "bull" and stayed invested whenever decoded into
it. Its diagnosed failure: QQQ MDD 0.386 (decisive fail) despite Sharpe 1.061
passing -- the "bull" state absorbed both calm low-vol uptrends AND
higher-volatility melt-up/euphoria periods (still positive mean, high
variance). Fix tested here: fit a 3-state Gaussian HMM (adds a distinct
mid/transition state) and select the invested state by an in-sample
risk-adjusted score (mean/std, a per-state Sharpe proxy) instead of raw mean
return, to explicitly avoid high-mean-but-high-vol euphoria regimes. Same
rolling walk-forward refit (no lookahead) as the prior strategy.

## Grid test summary (Step 6)

Grid: `train_window` in [504, 756], `refit_every` in [21, 42] x
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles (low/mid/high)
= 48 cells, 2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.146** (7/48 cells passed both Sharpe>=1.0 and MDD<=0.25)
- **By asset class:** equity 7/24 passed, **crypto 0/24 passed** (decisive crypto failure)
- **By vol regime:** low 5/16, mid 0/16, high 2/16
- **Best cell:** QQQ, train_window=756, refit_every=42, low-vol regime, Sharpe=1.875
- **Worst cell:** SPY, train_window=504, refit_every=42, mid-vol regime, Sharpe=-0.646

## Single-config validation (Step 7): train_window=756, refit_every=42

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.909 (FAIL) | 0.985 (FAIL, near-miss) | >= 1.0 |
| Max drawdown | 0.216 (PASS) | 0.190 (PASS) | <= 0.25 |
| Net Sharpe after costs (10bps/trade) | 0.892 (PASS) | 0.971 (PASS) | >= 0.5 |
| Walk-forward pass fraction (4 manual equal slices) | 1.0 (PASS) | 1.0 (PASS) | >= 0.75 |
| Parameter sensitivity relative std | 0.112 (PASS) | 0.126 (PASS) | <= 0.5 |
| Num trades | 16 | 9 | -- |

## Comparison to prior 2-state HMM (2026-09-08-173, best cell same params)

| | 2-state (highest-mean) | 3-state (risk-adjusted) |
|---|---|---|
| QQQ Sharpe | 1.061 (pass) | 0.909 (fail) |
| QQQ MDD | 0.386 (**decisive fail**) | 0.216 (**pass, fixed**) |
| SPY Sharpe | 0.988 (near-miss fail) | 0.985 (near-miss fail) |
| SPY MDD | 0.254 (near-miss fail) | 0.190 (**pass, fixed**) |
| Grid pass_fraction | 0.333 | 0.146 |

The risk-adjusted state-selection fix worked exactly as intended on
drawdown (both symbols now comfortably pass MDD, resolving the prior
version's decisive QQQ failure) but this came at the cost of Sharpe: the
3-state model spends less time invested (fewer trades, 16 vs prior's
4-8 -- actually more trades here, refit_every=42 differs from prior's
also-tested combos) in a narrower "calm" state, damping both drawdown and
return, and both symbols now narrowly miss the Sharpe>=1.0 threshold.
Grid pass_fraction also dropped (0.146 vs 0.333) -- the fix is not a net
improvement over the original despite fixing its worst failure mode.

## Decision

**Reject.** Sharpe ratio fails for both QQQ (0.909) and SPY (0.985, a
narrow ~1.5% miss) despite passing every other validator (MDD, transaction
costs, walk-forward, parameter sensitivity). Logged as a near-miss: a
future iteration could try lowering `refit_every` further (more responsive
regime switching) or blending the risk-adjusted state selection with a
minimum-time-invested floor to recover some of the lost Sharpe without
reintroducing the original's drawdown blowup.
