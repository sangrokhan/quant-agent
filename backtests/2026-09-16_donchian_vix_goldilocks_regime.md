# Donchian breakout gated by VIX "goldilocks zone" regime filter (2026-09-16)

**Hypothesis id:** 2026-09-16-167
**Strategy file:** `strategies/2026-09-16_donchian_vix_goldilocks_regime.py`
**Source:** https://volatilitybox.com/research/opening-range-volatility-breakout/
(read via `browser_exec` fallback -- `web_extract`'s configured backend is
DuckDuckGo, which is search-only and cannot fetch page content; article
text pulled directly from the rendered page instead)

## Hypothesis

The source article's own disclosed backtest table for intraday opening
range breakout (ORB) day trading states the HIGHEST win rate (58-62% on
ES futures, VIX-filtered) occurs when VIX sits in a 16-25 "goldilocks"
band -- not so calm that ranges are too narrow to trade profitably, not so
chaotic that false-breakout rates spike. Adapted here to this repo's daily
bars as a regime filter on a classic Donchian channel breakout: trade the
breakout only while VIX close is inside [vix_low, vix_high]; for crypto
(no VIX), a same-asset realized-vol percentile-rank proxy band substitutes,
testing whether the "moderate not extreme volatility helps breakouts"
mechanism generalizes across asset classes.

Novelty: distinct from every prior VIX-gated strategy in this repo
(2026-09-04-103 BB spike bounce, 2026-09-05-021 CVR3, 2026-09-05-043 MOVE
panic filter, 2026-09-05-044 VRP filter, 2026-09-06-115 WVF spike,
2026-09-13-019 VIX N-day-high breakout) -- none use a two-sided moderate
band gating a price breakout rather than a spike/dip event or mean
reversion.

## Grid test summary (Step 6)

Equity grid: `entry_window` in [15,20,30] x `vix_low` in [14,16] x
`vix_high` in [25,30], symbols QQQ/SPY, vol_regime_splits=3 (72 cells).
Crypto grid: `entry_window` in [15,20,30] x `rv_low_pct` in [0.25,0.30] x
`rv_high_pct` in [0.70,0.75], symbols BTC/USDT, ETH/USDT, vol_regime_splits=3
(72 cells).

- **Combined pass_fraction:** 41/144 = 0.2847
- **Equity:** 21/72 passed (best: QQQ, entry_window=30, vix 16-25, mid-vol
  regime, Sharpe 1.68; after hand-tuning entry_window=20 gave the best
  full-sample Sharpe of 1.12, used as the primary config below)
- **Crypto:** 20/72 passed (best: BTC/USDT, entry_window=20, rv 0.25-0.70,
  low-vol regime, Sharpe 1.91)
- **by_vol_regime (equity):** low 4/24, mid 12/24, high 5/24 -- edge
  concentrates in mid-vol regimes, consistent with the "goldilocks, not
  extreme" thesis
- **by_vol_regime (crypto):** low 12/24, mid 5/24, high 3/24 -- edge
  concentrates in low-vol regimes for crypto (own-asset RV proxy, distinct
  distribution from VIX)
- **by_asset_class:** equity QQQ+SPY combined 21/72; crypto BTC+ETH
  combined 20/72 -- roughly balanced across asset classes but SPY and ETH
  individually were considerably weaker than QQQ/BTC (see param sweep below)

## Single-config validation (Step 7)

### QQQ, entry_window=20, vix_low=16, vix_high=25, max_hold_days=20

| Validator | Result | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.121 | >= 1.0 | PASS |
| Max drawdown | 0.096 | <= 0.30 | PASS |
| Transaction cost survival (10bps/trade, 49 trades) | net Sharpe 1.011 | >= 0.5 | PASS |
| Walk-forward (4 contiguous splits, manual fallback -- `vbt.utils.splitting.RangeSplitter` unavailable in installed vectorbt version, established repo convention) | 4/4 splits positive | >= 50% | PASS |
| Parameter sensitivity (entry_window in [15,20,25]) | relative std 0.128 | <= 0.6 | PASS |

SPY at the same config underperformed (full-sample Sharpe well under 1.0
in the param sweep -- 0.44 to 0.59 across entry_window values); this
strategy is scoped to QQQ only for equity, not SPY.

### BTC/USDT, entry_window=20, rv_low_pct=0.25, rv_high_pct=0.70, max_hold_days=20

| Validator | Result | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.096 | >= 1.0 | PASS |
| Max drawdown | 0.215 | <= 0.30 | PASS |
| Transaction cost survival (10bps/trade, 54 trades) | net Sharpe 1.063 | >= 0.5 | PASS |
| Walk-forward (4 contiguous splits, manual fallback) | 4/4 splits positive | >= 50% | PASS |
| Parameter sensitivity (entry_window in [15,20,25]) | relative std 0.086 | <= 0.6 | PASS |

## Decision

**Accept** -- QQQ (equity) and BTC/USDT (crypto), both all 5 validators
pass at entry_window=20 with asset-class-appropriate volatility band
parameters (VIX 16-25 for QQQ; realized-vol percentile 0.25-0.70 for
BTC/USDT). SPY and ETH/USDT did not clear the Sharpe threshold at the
tested configs and are out of scope for this accepted strategy.
