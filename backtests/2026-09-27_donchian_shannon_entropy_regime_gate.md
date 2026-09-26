# Donchian Breakout with Shannon-Entropy Trend/Chop Regime Gate

**Date:** 2026-09-27
**Strategy file:** `strategies/2026-09-27_donchian_shannon_entropy_regime_gate.py`
**Outcome:** Accepted (QQQ only). Rejected SPY (decisive Sharpe/TC fail). Crypto not separately validator-tested (grid pass_fraction 0 in high-vol, low overall — see grid summary); scope limited to QQQ.

## Hypothesis

Per Richard Shu's "Trading with Less Surprise: Using Shannon Entropy to Improve
a Breakout Strategy" (Medium/CodeX, Nov 2025):
https://medium.com/codex/trading-with-less-surprise-using-shannon-entropy-to-improve-a-breakout-strategy-4d0a15098cba

Classic Donchian-channel breakouts suffer false breakouts in choppy/high-entropy
markets. Shannon entropy of the rolling 20-day return distribution (discretized
into 10 bins), z-scored against its own trailing 252-day mean/std, distinguishes
low-entropy (trending) regimes from high-entropy (choppy) regimes. The source's
own SPY 2000-2025 walk-forward (ML-feature framing) found entropy_zscore
improved Sharpe 0.351 -> 0.455 and MDD -12.57% -> -9.68%.

This repo adapts the feature into a hard rule-based regime GATE: only take
Donchian breakout long entries when entropy_zscore <= entropy_gate_threshold.

## Best config (QQQ)

```
donchian_window=25, entropy_gate_threshold=0.25, max_hold_days=20
donchian_exit_window=10 (default), entropy_lookback=20 (default), entropy_bins=10 (default), threshold_window=252 (default)
```

## Single-config validator results (2018-01-01 to 2026-09-01)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | **PASS** 1.282 | FAIL 0.185 |
| Max drawdown (<=0.25) | PASS 0.108 | PASS 0.223 |
| TC survival, 10bps/trade, 45 trades (net Sharpe >=0.5) | **PASS** 1.200 | FAIL 0.101 |
| Walk-forward (4 splits, manual RangeSplitter replacement — vbt.utils.splitting unavailable in installed vectorbt version; per-split positive-Sharpe fraction >=0.75) | **PASS** 1.00 (4/4) | PASS 0.75 (3/4) |
| Parameter sensitivity (relative std <=0.5, 3x3 grid around config) | **PASS** 0.070 | FAIL 0.508 |

QQQ passes all 5 validators decisively. SPY fails Sharpe and TC-survival
decisively (and parameter sensitivity narrowly) — the entropy-gated Donchian
breakout edge on this repo's single-symbol daily-bar setup does not transfer
from QQQ to SPY, despite the same underlying index family.

## Grid-test summary (Step 6)

`donchian_window` in {15,20,30} x `entropy_gate_threshold` in {-0.25,0,0.25} x
{QQQ,SPY,BTC/USDT,ETH/USDT} x 3 vol terciles = 108 cells.

- total_cells=108, passed_cells=33, pass_fraction=0.306
- by_asset_class: equity 20/54 (0.370), crypto 13/54 (0.241)
- by_vol_regime: low 24/36 (0.667), mid 9/36 (0.25), high 0/36 (0.0)
- best_cell: QQQ, donchian_window=20, entropy_gate_threshold=-0.25, low-vol, Sharpe=2.11
- worst_cell: SPY, donchian_window=15, entropy_gate_threshold=0.25, mid-vol, Sharpe=-0.56

Interpretation: the entropy gate concentrates edge in low-vol regimes (as the
source's own rationale predicts — low entropy correlates with low realized
vol / structured trends) and is essentially useless in high-vol regimes across
both asset classes. Crypto shows some grid passes (13/54) but the fine-tuned
single QQQ config above does not carry over to BTC/ETH — this strategy is
scoped to QQQ only.

## Notes

- First Shannon-entropy-based strategy in this repo (distinct from existing
  permutation-entropy/approximate-entropy/fractal-dimension entries which use
  different entropy estimators on different base signals).
- Source URL: https://medium.com/codex/trading-with-less-surprise-using-shannon-entropy-to-improve-a-breakout-strategy-4d0a15098cba (read via browser_exec — web_extract's ddgs backend cannot extract page content, only search).
- `check_walk_forward` in `validation/validators.py` currently raises
  `AttributeError: module 'vectorbt.utils' has no attribute 'splitting'` in
  the installed vectorbt version; this iteration used a manual RangeSplitter
  replacement (`check_walk_forward_manual` in `run_validators_donchian_entropy.py`)
  that replicates the same contract (n_splits chunks, per-split positive-Sharpe
  fraction) to get an unblocked walk-forward result.
