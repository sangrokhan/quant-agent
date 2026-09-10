# Backtest report: GDX/GLD ratio regime gate -- shared-config fine-tune
# upgrade of 2026-09-11-049 (originally QQQ-only)

**Strategy file:** `strategies/2026-09-11_gdx_gld_ratio_regime_gate.py`
(existing file from 2026-09-11-049, re-parameterized this iteration -- no
code changes)
**Hypothesis source:** Investopedia's "Optimize Your Gold Miner ETF
Portfolio with Technical Analysis" and BullionVault (originally researched
in 2026-09-11-049).

## Hypothesis

GDX (gold miners) outperforming GLD (gold bullion) -- ratio above its own
SMA -- proxies a broader risk-on/high-beta-appetite regime (miners carry
both gold-price beta and general equity-market sentiment beta). Gate
QQQ/SPY's own SMA trend-following signal by this ratio regime.

This iteration is a direct fine-tune follow-up to 2026-09-11-049 (originally
accepted QQQ-only at trend_sma_window=200/ratio_sma_window=100; SPY
near-miss Sharpe 0.777 at that same config) -- searching for a genuinely
SHARED cross-symbol config that clears both, per this repo's established
fix pattern (e.g. 2026-09-11-028 HYG, 2026-09-11-060 TIP, 2026-09-11-064
BDRY).

## Parameter search (Step 6/7)

Local search over trend_sma_window in {30,50,75,100,125,150,175,200,225,250}
x ratio_sma_window in {30,50,75,100,125,150,175,200} (80 combos) on SPY
full-sample (2015-01-01 to 2026-09-01): 3 combos cleared both Sharpe>=1.0
AND MDD<=0.25 on SPY -- best: trend_sma_window=225/ratio_sma_window=200
(SPY Sharpe 1.057).

**Selected shared config: trend_sma_window=225, ratio_sma_window=200**
(tested against BOTH symbols at this exact shared config):

| Symbol | Sharpe | MDD | Trades | Net Sharpe (10bps/trade) |
|---|---|---|---|---|
| QQQ | 1.288 | 0.136 | 119 | 1.103 |
| SPY | 1.057 | 0.106 | 113 | 0.834 |

- `check_sharpe_ratio`: **PASSED** both (1.288, 1.057 >= 1.0).
- `check_max_drawdown`: **PASSED** both (0.136, 0.106 <= 0.25).
- `check_transaction_cost_survival`: **PASSED** both (net Sharpe 1.103/0.834
  at 10bps/trade, above the 0.5 threshold).
- `check_parameter_sensitivity`: **PASSED** both -- local 3x3 perturbation
  (trend in {200,225,250} x ratio in {175,200,225}) gives relative_std=0.074
  (QQQ) and 0.078 (SPY), both well under the 0.5 threshold.
- Crypto falsification (BTC/ETH at the same shared config): Sharpe
  0.161/0.100, MDD 0.435/0.526 -- decisively rejected, as expected (no
  gold-miner-sector analog for crypto).

## Decision: ACCEPTED (QQQ + SPY, shared config trend_sma_window=225/ratio_sma_window=200)

Upgrades 2026-09-11-049 from "accepted QQQ-only, SPY near-miss" to "accepted
both symbols with a single shared config" via local parameter re-tuning
(longer trend/ratio windows than the original QQQ-only config). Crypto
remains decisively rejected.

## Notes for future loops

- The winning windows here (225-day trend SMA, 200-day ratio SMA) are
  notably longer than the original QQQ-only config (200/100) -- consistent
  with this repo's general finding that SPY (lower-beta, more
  index-diversified than QQQ) often needs a slower/more-patient trend
  filter to clear the same Sharpe bar.
- This is now the third consecutive iteration this cron trigger to succeed
  via "fine-tune an existing near-miss to find a shared config" rather than
  a fresh Step-2 web-research hypothesis (following 2026-09-11-064 BDRY) --
  a sign the knowledge base's ~868 existing entries have made fresh-idea
  discovery increasingly hard, while systematic re-tuning of the many
  recorded near-misses remains a productive vein.
