# Backtest Report: Williams VIX Fix + Stochastic RSI Confluence

**Date:** 2026-09-16 (iteration 1, cron trigger 2026-09-15 ~15:00 KST)
**Strategy file:** `strategies/2026-09-16_wvf_stochrsi_confluence.py`
**Knowledge base id:** see `knowledge_base/strategies_log.jsonl`

## Hypothesis

Per a Google AI-overview summary (TradingView/agenticks.ca community
writeups) of Williams VIX Fix (WVF) combined with an independent momentum
oscillator confirmation: enter long when WVF spikes above its own rolling
Bollinger upper band (capitulation/panic spike) **AND** Stochastic RSI %K is
below an oversold threshold on the same bar (confirms genuine oversold
conditions, not just a volatility spike). Exit when Stochastic RSI %K
crosses back above an overbought threshold, or a `max_hold_days` time-stop.

Source read via `browser_exec` fallback (Google search AI overview) after
`web_search`'s DDGS backend failed with a Yahoo/TLS connection error on the
first query this iteration.

This repo has 2 prior standalone WVF entries (2026-09-06-115 rejected;
2026-09-10-099 accepted QQQ only via a different PercentRank-based trigger).
This iteration is distinct: it re-tests the Bollinger-band spike trigger
(which alone failed in 2026-09-06-115) but adds an independent
Stochastic-RSI oversold confirmation gate and a symmetric oscillator exit.

## Grid test summary (Step 6)

`param_grid={oversold_threshold: [15,20,25], wvf_bb_std: [1.5,2.0],
max_hold_days: [10,15]}`, `symbols={equity: [QQQ,SPY], crypto:
[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`.

- total_cells: 144, passed_cells: 24, **pass_fraction: 0.167**
- by_asset_class: equity 24/72 passed, crypto 0/72 passed
- by_vol_regime: low 24/48, mid 0/48, high 0/48
- best_cell: equity/SPY/low-vol, sharpe 3.19 (oversold=25, bb_std=2.0, hold=15)
- worst_cell: crypto/BTC-USDT/low-vol, sharpe -0.60

The edge is confined almost entirely to the low-volatility tercile on
equities; it decays in mid/high-vol regimes and never clears the crypto bar
in any of the 72 crypto cells tested.

Best full-grid config selected for single-config validation:
`oversold_threshold=25.0, wvf_bb_std=1.5, max_hold_days=15` (highest average
equity Sharpe across the param sweep).

## Single-config validator results (Step 7)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity | Overall |
|---|---|---|---|---|---|---|
| QQQ | 1.087 (pass) | 0.230 (pass) | 0.919 (pass) | 1.00 (pass) | 0.213 rel-std (pass) | **ACCEPT** |
| SPY | 0.657 (fail) | 0.256 (fail) | 0.483 (fail) | 0.75 (pass) | 0.081 rel-std (pass) | REJECT |
| BTC/USDT | 0.371 (fail) | 0.592 (fail) | 0.316 (fail) | 0.75 (pass) | 0.237 rel-std (pass) | REJECT |

## Decision

**Accept QQQ only.** SPY and both crypto symbols fail multiple validators
decisively (Sharpe, MDD, and TC-survival all miss on SPY and BTC/USDT). The
full-sample QQQ Sharpe (1.087) is a much thinner margin than the grid's
low-vol-tercile Sharpe (up to 3.19), consistent with the grid finding that
the edge is concentrated in low-vol regimes and gets diluted across the
full mixed-regime sample — flagged for future monitoring/regime-gating
follow-up.

Strategy file and this report are kept as the record of a QQQ-only accepted
strategy (scope-limited, not a broad multi-asset accept).
