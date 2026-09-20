# Chaos-to-Order Transition (Correlation Dimension) Strategy — Backtest Report (2026-09-21)

## Hypothesis

Per PyQuantLab's "A Chaos Theory-Based Trading Strategy in Backtrader"
(Medium, Jun 2025, https://pyquantlab.medium.com/a-chaos-theory-based-trading-strategy-in-backtrader-46bde42bdcb6,
read via `browser_exec` after `web_search`'s DDGS backend TLS-erroring on
the correlation-dimension follow-up query, full backtrader source code
disclosed): enter only on the specific TRANSITION event where the rolling
largest Lyapunov exponent crosses DOWN through a threshold (chaotic ->
ordered regime change) AND the rolling Grassberger-Procaccia correlation
dimension is below a threshold (simple/low-complexity attractor), gated by
an SMA trend filter for direction. Exit when the Lyapunov exponent rises
back above 2x the threshold ("chaos resuming").

Distinct from this repo's prior Lyapunov-Hurst strategy (2026-09-20-150,
accepted QQQ) in two ways: (1) triggers on the TRANSITION/crossing event
itself, not a persistent-state gate; (2) substitutes Grassberger-Procaccia
correlation dimension for the Hurst-persistence filter. First
correlation-dimension-based strategy in this repo.

## Single-config validators (grid-best overall config: ETH/USDT,
`trend_window=100, lyap_threshold=0.4, corr_dim_threshold=1.7`)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.679 | ≥ 1.0 |
| Max drawdown | ❌ | 0.364 | ≤ 0.25 |
| Transaction cost survival (10bps/trade, 15 trades) | ✅ | net Sharpe 0.673 | ≥ 0.5 |
| Walk-forward (4 splits, manual fallback) | ❌ | 0.5 pass fraction | ≥ 0.75 |
| Parameter sensitivity (8-combo grid, relative std) | ❌ | 1.157 | ≤ 0.5 |

Full sample: 2018-01-01 to 2026-09-01, daily bars.

## Grid test summary (Step 6)

Grid: `trend_window ∈ {50,100} × lyap_threshold ∈ {0.40,0.45} ×
corr_dim_threshold ∈ {1.5,1.7}` × symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}` ×
3 vol-regime terciles = 96 cells.

- **Overall pass fraction: 0.2083 (20/96)**
- By asset class: equity 15/48 (0.313), crypto 5/48 (0.104)
- By vol regime: low 8/32 (0.25), mid 9/32 (0.281), high 3/32 (0.094)
- Best cell overall: ETH/USDT, mid-vol tercile, `trend_window=100,
  lyap_threshold=0.4, corr_dim_threshold=1.7` — Sharpe 2.076
- Best per-symbol cells: QQQ Sharpe 1.653 (mid-vol), SPY Sharpe 1.640
  (high-vol), BTC/USDT Sharpe 0.984 (high-vol), ETH/USDT Sharpe 2.076 (mid-vol)
- Worst cell: SPY, mid-vol tercile, `trend_window=100, lyap_threshold=0.4,
  corr_dim_threshold=1.5` — Sharpe -1.144

**Honest scope**: the transition-trigger design produces very few trades
(15 over the full ETH/USDT sample) — good individual per-regime Sharpe
values are highly sensitive to the specific vol-regime slice and don't
generalize to the full-sample validators, and the very low trade count
(15) makes the parameter-sensitivity check (relative std 1.157) fail badly:
small threshold perturbations move the (already sparse) trade set
substantially. The rare-transition-event design trades too infrequently
for the standard validator suite to give confident pass/fail signal at any
individual symbol.

## Decision

**Reject.** 4 of 5 full-sample validators fail on the grid-best config
(ETH/USDT). Only transaction-cost survival passes (unsurprising given only
15 trades). Strategy file and report kept as a record of a rejected
attempt. Future note: the underlying chaos-transition TRIGGER concept
(cross below threshold, not persistent gate) may still be worth revisiting
paired with a higher-frequency base signal or a less sparse trigger
condition (e.g. OR instead of AND between the Lyapunov-transition and
correlation-dimension conditions) to get enough trades for a
statistically meaningful validator run.

Sources visited this iteration:
- https://pyquantlab.medium.com/a-chaos-theory-based-trading-strategy-in-backtrader-46bde42bdcb6 (primary source, browser_exec, full backtrader code disclosed)
