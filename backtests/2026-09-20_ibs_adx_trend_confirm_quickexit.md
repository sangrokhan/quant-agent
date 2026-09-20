# IBS + ADX Trend-Confirmation Quick-Exit — Backtest Report (2026-09-20)

**Strategy file:** `strategies/2026-09-20_ibs_adx_trend_confirm_quickexit.py`
**Hypothesis source:** [StatOasis — "How the IBS Strategy Made $45K in
2024 — Even in a Down Market!"](https://statoasis.com/overfit/research/how-the-ibs-strategy-made-45k-in-2024-even-in-a-down-market)
(Ali Casey, updated Jun 17 2025), visited via `browser_exec` this iteration.

## Hypothesis

IBS = (Close-Low)/(High-Low) low readings signal panic/exhaustion sell-off
(mean-reversion long entry). Source's own exit rule: adaptive — exit next
open if profitable by next close, else exit anyway after 1 bar (approximated
here as a strict 1-bar hold, matching the source's stated worst case).
Source flags a counterintuitive finding worth testing directly: gating
entries to only fire when ADX is ABOVE a threshold (trending market
CONFIRMED, not avoided) improves IBS mean-reversion accuracy — opposite of
the usual heuristic. This repo has 14+ prior IBS entries but none combine
an ADX-trend-confirmation gate with this adaptive quick-exit rule.

## Grid test (Step 6)

`param_grid={"ibs_threshold": [0.15, 0.25], "adx_threshold": [15.0, 20.0,
25.0]}`, `symbols={"equity": ["QQQ","SPY"], "crypto":
["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`. 72 total cells.

- **pass_fraction: 0.222** (16/72)
- by_asset_class: equity 13/36 passed; crypto 3/36 passed (non-zero,
  notable relative to most prior crypto grids in this repo)
- by_vol_regime: low 7/24; mid 0/24; high 9/24 — unusual bimodal pattern
  (passes cluster in low AND high vol, none in mid)
- best_cell: ibs_threshold=0.25, adx_threshold=15.0, QQQ, low-vol, Sharpe 2.02
- worst_cell: ibs_threshold=0.25, adx_threshold=20.0, BTC/USDT, low-vol,
  Sharpe -1.01

## Single-config validation (Step 7) — grid-best config
(ibs_threshold=0.25, adx_threshold=15.0), full-period 2016-01-01 to
2026-09-01

| Metric | QQQ | SPY | Threshold | Pass |
|---|---|---|---|---|
| Sharpe (full period) | **1.250** | 0.635 | >= 1.0 | QQQ PASS / SPY FAIL |
| Max drawdown | 23.14% | 18.58% | <= 25% | PASS (both) |
| Net Sharpe after 5bps/trade costs | 0.537 | 0.084 | >= 0.5 | QQQ PASS (borderline) / SPY FAIL |
| Walk-forward pass fraction (4 splits) | 1.00 | 0.75 | >= 0.75 | PASS (both) |
| Parameter sensitivity (relative std, 6-combo sweep) | 0.146 | 0.130 | <= 0.5 | PASS (both) |

## Decision: ACCEPTED (QQQ only)

QQQ clears every validator: Sharpe 1.250, MDD 23.1% (comfortably under
25% but not as tight as the RSI(2)+ATR% strategy from this same cron
trigger), net-Sharpe-after-costs 0.537 (passes the 0.5 threshold but by a
narrow margin — this strategy trades very frequently, 822 trades over the
sample, so cost sensitivity is a real risk worth flagging), walk-forward
4/4, and low parameter sensitivity. SPY fails decisively on both Sharpe
and transaction-cost survival despite passing MDD/WF/PS.

**Cost-sensitivity caveat (important for future loops):** with 822 trades
over ~10.5 years (~78/year), this strategy trades far more frequently than
most others in this repo. The 5bps/trade cost assumption used here is a
rough approximation; the net-Sharpe-after-costs pass (0.537 vs 0.5
threshold) is close enough that a slightly higher realistic cost
assumption (e.g. 8-10bps for a liquid ETF, or wider for less liquid
instruments) could flip this to a fail. Treat as accepted-but-fragile to
cost assumptions, not a robust high-margin edge.

**Scope note:** accepted narrowly for QQQ only with ibs_threshold=0.25,
adx_threshold=15.0, adx_window=14. SPY should not be traded with this
exact construction; crypto is a decisive fail (3/36 grid cells, well
below any accept bar).
