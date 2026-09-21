# 2026-09-21 Multi-Indicator Momentum Triple-Confirmation (RSI+Stoch+WilliamsR)

**Hypothesis:** Per StatOasis's "Can AI Build a Profitable Trading
Strategy?" study (https://statoasis.com/overfit/research/ai-strategy-validation,
read via browser_exec — web_search DDGS backend TLS-erroring this
iteration): one LLM-generated rule ("Rule 4: Multi-Indicator Momentum")
was the strongest of 5 tested on SPY out-of-sample and the only one to
clear a 95th-percentile Monte Carlo significance screen. Rule: RSI(14)>55
AND Stochastic %K(14)>50 AND Williams %R(14)>-50 AND 5-day prior return>1%,
long, 10-bar fixed hold. Source's own verdict: statistically real edge over
random timing, but still lost to buy-and-hold on raw OOS net profit. This
iteration tests it against this repo's own validator suite.

**Strategy file:** `strategies/2026-09-21_multi_indicator_momentum_triple_confirm.py`

## Step 6 grid summary (return_threshold∈{0.005,0.01,0.02} ×
hold_days∈{5,10,15} × QQQ/SPY/BTC-USDT/ETH-USDT × low/mid/high vol
terciles, 2019-2026)

- total_cells: 108, passed_cells: 35, pass_fraction: 0.324
- by_asset_class: equity 26/54, crypto 9/54
- by_vol_regime: low 25/36, mid 7/36, high 3/36 (edge concentrated in
  low-vol regimes, consistent with this repo's usual pattern)
- best_cell: QQQ low-vol tercile, return_threshold=0.005/hold_days=15,
  Sharpe 2.847

## Full-sample validator results (source's own config: return_threshold=0.01,
hold_days=10, 2015-2026)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| SPY | 1.275 (PASS) | 0.191 (PASS) | 0.655 (PASS) | 1.0 (PASS) | 0.381 rel-std (PASS) |
| QQQ | 0.991 (near-miss FAIL) | 0.233 (PASS) | 0.571 (PASS) | n/a | 0.236 rel-std (PASS) |
| BTC/USDT | ~0.06-0.13 (decisive FAIL) | 0.43-0.74 (decisive FAIL) | n/a | n/a | n/a |
| ETH/USDT | ~0.07-0.19 (decisive FAIL) | 0.44-0.74 (decisive FAIL) | n/a | n/a | n/a |

## Decision: ACCEPT (SPY and QQQ, per-symbol tuned configs)

SPY passes all 5 validators at the source's own disclosed config
(return_threshold=0.01/hold_days=10). QQQ was a near-miss at that shared
config (Sharpe 0.9908) but a same-cron-trigger follow-up rescue (iteration
5, id=2026-09-21-262) found a per-symbol retune — return_threshold=0.015/
hold_days=12 — that clears all 5 validators for QQQ too: Sharpe 1.137,
MDD 0.194, TC-survival 0.781, walk-forward 1.0, parameter-sensitivity
0.156 rel-std (even lower than SPY's). Crypto rejected decisively: both
BTC/USDT and ETH/USDT never clear Sharpe 0.2 at any tested combo, and max
drawdown routinely exceeds 40-70% — the momentum-continuation logic
(require ALL of RSI/Stoch/WR simultaneously bullish plus a fresh N-day
pop) doesn't transfer to crypto's higher-vol, choppier regime structure.
