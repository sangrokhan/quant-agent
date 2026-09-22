# Double Death Cross — Triple-SMA (50/100/200) Confirmation Filter (QQQ/SPY)

**Date:** 2026-09-23
**Source:** https://www.quantifiedstrategies.com/death-cross-in-trading/
**Strategy file:** `strategies/2026-09-23_double_death_cross_triple_sma.py`

## Hypothesis
Source discloses an enhancement to the classic 50/200-day SMA Death
Cross/Golden Cross: add a 100-day SMA as a third confirmation layer,
requiring the 50-day SMA to be below BOTH the 100-day AND 200-day SMA
(not just 200-day alone) to trigger exit -- explicitly framed as a
false-signal filter (e.g. avoiding whipsaws like the March 2020 COVID
Death Cross that triggered near the exact bottom). We hold prior position
state whenever the two slower MAs disagree (ambiguous zone).

## Grid test summary (sma_mid in {75, 100}, QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- **24 total cells, 6 passed (pass_fraction = 0.25)**
- By asset class: equity 6/12 passed, **crypto 0/12 passed**
- By vol regime: low 4/8, mid 2/8, high 0/8
- Best cell: sma_mid=75, SPY, low-vol, Sharpe 2.32

## Single-config validators (sma_fast=50, sma_mid=100, sma_slow=200 — source's own values)

| Validator | SPY | QQQ |
|---|---|---|
| Sharpe ratio (>=1.0) | 0.634 — **FAIL** | 1.006 — pass (barely) |
| Max drawdown (<=25%) | 34.1% — **FAIL** | 28.6% — **FAIL** |
| Transaction cost survival (net Sharpe >=0.5 @ 10bps) | 0.626 — pass | 0.999 — pass |
| Walk-forward (4-split, >=75% positive-Sharpe splits) | 100% — pass | 100% — pass |
| Parameter sensitivity (relative std <=0.5) | 0.0 — pass | 0.001 — pass |

Only 9 trades over 8.5 years on each symbol -- the triple-confirmation
filter is very effective at reducing turnover/false-signal whipsaws (as
the source claims), but the max drawdown clears our 25% threshold on both
symbols regardless, because this is still fundamentally a slow trend
filter that gets fully exposed during the initial leg of any large
drawdown before the MAs catch up.

## Decision: REJECTED

Max drawdown fails decisively on both QQQ (28.6%) and SPY (34.1%), and
Sharpe also fails on SPY (0.634); QQQ Sharpe barely clears the 1.0
threshold (1.006) but its MDD failure alone is sufficient to reject.
Consistent with the source's own framing that this is primarily a
risk-management/drawdown-smoothing tool relative to buy-and-hold, not an
alpha-generating strategy in its own right -- and even that smoothing
claim doesn't clear this repo's fixed 25% MDD bar on either symbol.
