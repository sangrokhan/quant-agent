# Backtest Report: Two-Day RSI(2) Dip-Buy Mean Reversion

**Date:** 2026-09-27
**Strategy file:** `strategies/2026-09-27_rsi2_dip_vixgate_meanrev.py`
**Hypothesis id:** 2026-09-27-049

## Hypothesis

Per QuanterLab's "Navigating Mean Reversion: Breaking Down the Base
Mechanism" (Serhat Girgin,
https://quanterlab.com/research/navigating-mean-reversion-breaking-down-the-base-mechanism,
found via quantocracy.com's blog-mashup listing after `web_search`'s DDGS
backend returned "No results found" for the initial query): the
"plainest" mean-reversion rule, tested by the source across every S&P 500
member for 20 years -- buy on a day when 2-period RSI falls below 10
while the close is still above its 200-day average; sell when close is
back above its 5-day average. Source's own headline finding: unconditional
("every dip") trading barely survives realistic costs, but gating entries
to require the PRIOR day's VIX close >= 20 cuts trade frequency and keeps
more return after costs, with the edge concentrated in genuinely stressed
periods (2020-2022).

## Grid test summary (Step 6)

Two grids run: (a) plain (no VIX gate), `param_grid={"rsi_entry": [5, 10,
15], "exit_sma_window": [3, 5, 7]}`, equity=[QQQ, SPY] crypto=[BTC/USDT,
ETH/USDT]; (b) VIX-gated, `param_grid={"rsi_entry": [5, 10, 15],
"vix_threshold": [18, 20, 22]}`, equity=[QQQ, SPY] only.
`vol_regime_splits=3`, sample 2019-01-01 to 2026-09-01.

**Plain grid:** 108 cells, 36 passed (pass_fraction 0.333). by_asset_class:
equity 33/54 (0.61), crypto 3/54 (0.06 — mostly decisive crypto reject).
by_vol_regime: low 18/36 (0.50), mid 11/36 (0.31), high 7/36 (0.19). Best
cell: QQQ, low-vol, `rsi_entry=10/exit_sma_window=7`, Sharpe 2.50.

**VIX-gated grid:** 54 cells, 17 passed (pass_fraction 0.315), equity
only. Best cell: QQQ, high-vol, `rsi_entry=15/vix_threshold=18`, Sharpe
1.63.

## Single-config validation (Step 7) — plain config, `rsi_entry=10/exit_sma_window=7`, full sample

| Validator | QQQ | SPY | BTC/USDT | ETH/USDT |
|---|---|---|---|---|
| Sharpe ratio (>=1.0) | **PASS** 1.009 | **PASS** 1.009 | FAIL 0.354 | FAIL 0.568 |
| Max drawdown (<=0.25) | PASS 0.110 | PASS 0.081 | FAIL 0.398 | FAIL 0.379 |
| Transaction-cost survival (net Sharpe >=0.5) | PASS 0.878 (55 trades) | PASS 0.830 (58 trades) | FAIL 0.319 | PASS 0.541 |
| Walk-forward (manual 4-split substitute) | PASS 1.0 (4/4) | PASS 1.0 (4/4) | PASS 0.75 (3/4) | PASS 1.0 (4/4) |
| Parameter sensitivity (relative_std<=0.5, 25-cell grid) | PASS 0.205 | PASS 0.157 | PASS 0.110 | PASS 0.231 |

QQQ and SPY: **all 5 validators pass** (Sharpe is a narrow pass at
~1.009 for both, worth flagging as a genuine but thin margin rather than
a comfortable clear). Crypto (BTC/USDT, ETH/USDT): both decisively fail
Sharpe and MDD (MDD ~38-40% vs 25% threshold), consistent with the source
never claiming this rule generalizes beyond equities and this repo's
frequent finding that unconditional RSI(2)-family entries don't transfer
to crypto without additional risk controls.

The VIX-gated variant was also explored per the source's own headline
cost-survival finding, but the plain (no-gate) config at `rsi_entry=10/
exit_sma_window=7` already clears all 5 validators on both QQQ and SPY,
so the VIX-gate rescue was not needed this iteration (left as a candidate
enhancement/diversification angle for a future sub-iteration, e.g. if the
plain version's thin Sharpe margin degrades under a parameter retune).

## Decision

**Accepted for equity (QQQ, SPY)** at `rsi_entry=10, exit_sma_window=7,
trend_window=200, max_hold_days=15` (default), no VIX gate needed.
Crypto (BTC/USDT, ETH/USDT) rejected — decisive Sharpe and MDD failures.
