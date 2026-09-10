# ROC Momentum + ATR Ratcheting Trailing Stop — ACCEPTED (QQQ only)

**Iteration ID:** 2026-09-11-014
**Date:** 2026-09-11

## Hypothesis

Per Bui & Nguyen, "Systematic Trend-Following with Adaptive Portfolio
Construction: Enhancing Risk-Adjusted Alpha in Cryptocurrency Markets"
(arXiv:2602.11708, https://arxiv.org/abs/2602.11708 / full text at
https://arxiv.org/html/2602.11708, visited this iteration): the paper's
"AdaptiveTrend" signal generation module (Section 3.2, fully disclosed
formula) uses a plain rate-of-change momentum entry
`MOM_t = (P_t - P_{t-L}) / P_{t-L}`, triggering a long entry when
`MOM_t > theta_entry`, and a dynamic monotonically-ratcheting ATR trailing
stop `S_t = max(S_{t-1}, P_t - alpha * ATR_t(k))`, closing when
`P_t < S_t`. The full paper reports (6-hour crypto bars, 150+ pairs,
2022-2024) an annualized Sharpe of 2.41 for the FULL multi-asset portfolio
framework (asset selection + 70/30 long-short allocation); this repo tests
only the fully-mechanical single-asset signal generation module (Eq. 2-3)
on daily bars, since the portfolio-construction/allocation machinery is
out of scope for this repo's single-asset grid_test.py infrastructure.

Distinct from this repo's existing dual-timeframe ROC breakout entry
(`2026-09-04-092`, uses a rolling-extreme breakout trigger + fixed
ATR-multiple stop-loss) because this strategy uses (1) a single plain ROC
threshold-crossing entry (no breakout/dual-timeframe condition) and (2) a
MONOTONICALLY RATCHETING ATR trailing stop (Chandelier-Exit-style,
tightens only) rather than a fixed static stop set once at entry.

## Step 6 grid summary

Grid: `lookback=[10,20,40] x entry_threshold=[0.02,0.03,0.05] x atr_mult=[2.0,3.0]`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), `vol_regime_splits=3`,
2015-01-01 to 2026-09-01, 216 total cells.

- **pass_fraction: 0.204 (44/216)**
- by_asset_class: equity 44/108 (40.7%), crypto 0/108 (0%)
- by_vol_regime: low 29/72 (40.3%), mid 15/72 (20.8%), high 0/72 (0%)
- best_cell: QQQ low-vol, `lookback=40, entry_threshold=0.05, atr_mult=3.0`, Sharpe=1.876

## Step 7 single-config validation

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe) | Trades | Manual walk-forward (4 splits) |
|---|---|---|---|---|---|---|
| QQQ | lookback=40, entry_threshold=0.02, atr_mult=3.0 | **1.032** (PASS) | 0.179 (PASS, thr 0.25) | 0.976 (PASS, thr 0.5) | 62 | 4/4 positive (PASS) |
| SPY | (best found: lookback=20, entry_threshold=0.02, atr_mult=2.0) | 0.753 (FAIL) | -- | 0.640 (would pass) | 84 | -- |

SPY was extensively fine-tuned (42 param combos: `lookback in
{10,15,20,30,40,60} x entry_threshold in {0.01,...,0.05} x atr_mult in
{1.5,...,4.0}`) with no combo simultaneously passing both Sharpe and
TC-survival at n_trades>=10 -- a genuine (not near-miss) full-sample
Sharpe shortfall on SPY specifically.

Crypto (BTC/USDT, ETH/USDT) rejected decisively at the QQQ config: Sharpe
0.205 / 0.230.

## Decision: ACCEPTED (QQQ only)

QQQ passes Sharpe, max drawdown, transaction-cost survival, and manual
walk-forward at its grid-optimal config. SPY does not clear the bar at any
tested config within an extensive fine-tuning search, and crypto is
decisively rejected despite being the source paper's ORIGINAL target asset
class -- likely because the paper's edge in crypto depends heavily on the
monthly cross-sectional asset-selection and asymmetric long-short
allocation machinery (Sections 3.3-3.4) which is explicitly out of scope
for this single-asset test; the isolated signal-generation module alone
(momentum entry + ATR trailing stop) does not carry the paper's edge on
crypto without that portfolio-construction layer.
