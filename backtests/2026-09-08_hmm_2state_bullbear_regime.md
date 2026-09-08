# Backtest Report: 2-State Gaussian HMM Bull/Bear Regime Filter (2026-09-08)

**Status: REJECTED** — strategy file kept in `strategies/` as a record of a
rejected attempt, not a live strategy.

## Hypothesis

Per QuantifiedStrategies.com "Hidden Markov Model Market Regimes"
(https://www.quantifiedstrategies.com/hidden-markov-model-market-regimes/),
a 2-state Gaussian HMM fit on daily log returns typically discovers one
"low-volatility bull" hidden state and one "high-volatility bear/crisis"
hidden state; avoiding trades during the detected bear regime is claimed to
improve Sharpe ratio vs a static always-invested strategy.

Implemented as a rolling walk-forward-refit `hmmlearn.GaussianHMM(n_components=2)`
fit on trailing `train_window` days of log returns (refit every `refit_every`
days, strictly no-lookahead), long only when the Viterbi-decoded latest
hidden state is the higher-mean ("bull") state.

## Single-config validator results (best grid config: `train_window=756`, `refit_every=21`)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Walk-forward | Param sensitivity | Trades |
|---|---|---|---|---|---|---|
| SPY | 0.988 ❌ (<1.0) | 0.254 ❌ (>0.25) | 0.984 ✅ | 1.0 ✅ | 0.037 ✅ | 4 |
| QQQ | 1.061 ✅ | 0.386 ❌ (>0.25, decisive) | 1.054 ✅ | 1.0 ✅ | 0.043 ✅ | 8 |

## Grid test summary

`param_grid={train_window:[504,756], refit_every:[21]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`
(2018-01-01 to 2026-09-01), 24 total cells.

- **Overall pass_fraction: 0.333** (8/24 cells) — highest of any strategy
  tested by this agent so far
- By asset class: equity 8/12 passed, **crypto 0/12 passed** (decisive reject)
- By vol regime: low 4/8, mid 2/8, high 2/8 — notably even distribution
  (unlike most rejected strategies which cluster entirely in the low-vol
  tercile), indicating the HMM genuinely adapts across regimes rather than
  acting as a disguised volatility filter
- Best cell: SPY, low-vol, Sharpe 2.491
- Worst cell: ETH/USDT, high-vol, Sharpe -0.069

## Decision

**Reject.** Both tested equities fail max drawdown at the grid's best
config — SPY borderline (0.254 vs 0.25 threshold, also a narrow Sharpe
fail) and QQQ decisively (0.386). Very low trade counts (4/8 over an 8.5yr
sample, since each HMM regime decode holds for extended periods) mean the
strategy rides through occasional large drawdowns while correctly avoiding
others, netting a still-substantial max drawdown despite the strong grid
pass_fraction and passing Sharpe/walk-forward/param-sensitivity in most
individual checks. Crypto rejected decisively (0/12 cells).

**Follow-up idea for a future iteration:** shorter `refit_every` (faster
regime-flip response) or a 3-state model (explicit "crash" state) to see if
MDD improves without destroying the Sharpe edge — flagged as a near-miss
worth revisiting.
