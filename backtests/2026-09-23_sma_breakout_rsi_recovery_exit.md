# 2026-09-23 — SMA(20) 2%-Breakout Entry, RSI(14) Recovery-Through-30 Exit

## Hypothesis

Per a Medium/Kryptera article ("Why This Strategy Beat Buy-and-Hold and
Still Drew Down 85%",
https://medium.com/@Kryptera/why-this-strategy-beat-buy-and-hold-and-still-drew-down-85-89d2c717eccf,
read via browser_exec this iteration — web_search DDGS/Yahoo backend
TLS-errored on every query attempted): a deliberately minimal 2-rule
system — buy when close closes more than 2% above its own 20-day SMA
(momentum-breakout confirmation), sell when the 14-period RSI crosses back
UP through 30 from below (an oversold-recovery exit, not a classic
overbought fade). Source's own free preview discloses only these two rules
(full walk-forward mechanics paywalled); this repo tests the rule directly
on QQQ/SPY/BTC/ETH rather than trusting the source's single-stock (RCL)
claim.

Source URL: https://medium.com/@Kryptera/why-this-strategy-beat-buy-and-hold-and-still-drew-down-85-89d2c717eccf

## Grid summary (Step 6)

- Grid: breakout_pct ∈ {0.01, 0.02} × rsi_exit_threshold ∈ {30, 40} ×
  {QQQ, SPY, BTC/USDT} × 3 vol terciles = 36 cells.
- pass_fraction: 11/36 = 0.306
- by_asset_class: equity 10/24 passed; crypto 1/12 passed
- by_vol_regime: low 9/12, mid 2/12, high 0/12 (edge concentrated in
  low-vol conditions, consistent with most trend/momentum strategies in
  this repo)
- best_cell: SPY low-vol, breakout_pct=0.01, rsi_exit=40, Sharpe 2.48
- worst_cell: QQQ high-vol, breakout_pct=0.02, rsi_exit=40, Sharpe -0.15
- Per-symbol full grid (QQQ): all 3 low/mid cells with rsi_exit=30 pass
  (Sharpe 2.21-2.39), high-vol cells all fail. Source's own default
  (breakout_pct=0.02, rsi_exit=30) is among the strongest QQQ configs.

## Single-config validation (Step 7) — QQQ, breakout_pct=0.02, rsi_exit_threshold=30

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio (full sample) | pass | 1.072 | 1.0 |
| max_drawdown | pass | 0.224 | 0.25 |
| transaction_cost_survival | pass | 1.037 (net Sharpe) | 0.5 |
| walk_forward (4-split, manual fallback) | pass | 1.0 pass_fraction (4/4) | 0.75 |
| parameter_sensitivity | pass | 0.166 relative std | 0.5 |

38 trades over the sample. All 5 validators pass.

### Cross-check (same config, other symbols, full sample)

- SPY: Sharpe 0.925, MDD 0.209 — near-miss (below 1.0 threshold), scope
  limited to QQQ.
- BTC/USDT: Sharpe 0.135, MDD 0.640 — decisive fail.
- ETH/USDT: Sharpe 0.111, MDD 0.783 — decisive fail.

## Decision: ACCEPTED (QQQ only)

QQQ passes all 5 validators at the source's own default parameters
(breakout_pct=0.02, rsi_exit_threshold=30). SPY is a near-miss (Sharpe
0.925) worth a future targeted-parameter revisit; crypto is decisively
out of scope (very high MDD, low Sharpe — the 2%-breakout-confirmation
entry likely fires too readily in crypto's higher baseline volatility,
and the RSI-recovery exit is too slow given crypto's larger absolute
drawdowns before RSI recovers through 30). Keeping strategy file and
report; scope in the knowledge base notes as QQQ-only.
