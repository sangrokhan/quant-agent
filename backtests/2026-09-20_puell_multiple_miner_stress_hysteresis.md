# Backtest Report: Puell Multiple Miner-Stress Hysteresis Gate (BTC)

**Strategy file:** `strategies/2026-09-20_puell_multiple_miner_stress_hysteresis.py`
**Date:** 2026-09-20
**Hypothesis:** Puell Multiple = daily USD value of new BTC issuance / 365-day
moving average of that value (Glassnode/Bitbo/Samara Asset Group/MacroMicro,
all read via Google SERP this iteration). Neutral zone 0.5-4.0 per Samara
Asset Group. Long/flat hysteresis: go long when Puell <= enter_level (miner
stress/accumulation), flip flat when Puell >= exit_level (miner
windfall/overheated), hold state in between.

Sources: https://www.samara-ag.com/bitcoin-puell-multiple ,
https://docs.glassnode.com/coin-issuance/puell-multiple ,
https://bitbo.io/glossary/puell-multiple ,
https://en.macromicro.me/charts/bitcoin-puell-multiple (all via Google SERP
snippets, browser_exec fallback since web_search DDGS backend returned no
results for the query).

## Grid test summary (Step 6)

`enter_level in [0.4, 0.5, 0.6] x exit_level in [3.0, 4.0, 5.0]`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
vol_regime_splits=3, 2019-01-01 to 2026-09-01.

- total_cells: 108, passed_cells: 18, pass_fraction: 0.167
- by_asset_class: equity 18/54 passed, **crypto 0/54 passed**
- by_vol_regime: low 9/36, mid 3/36, high 6/36
- best_cell: equity/SPY/low-vol, params enter=0.5/exit=3.0, Sharpe 2.53
- worst_cell: crypto/ETH-USDT/mid-vol, Sharpe -0.137

The strategy's own hypothesis is specifically about BTC miner economics --
the metric is meaningless on equities (numerator/denominator degenerate to
a pure block-subsidy halving calendar, no real economic signal), so the
equity grid passes are not evidence for the hypothesis. Crypto (the actual
target asset class) has a **0% grid pass rate**.

## Single-config validators (Step 7)

Full-sample BTC/USDT (2019-01-01 to 2026-09-01), interval=1d:

| enter_level | exit_level | Sharpe | Sharpe pass (>=1.0) | MDD | MDD pass (<=0.25) |
|---|---|---|---|---|---|
| 0.4 | 3.0 | inf (degenerate: never enters, 0 trades) | True (spurious) | 0.0 | True (spurious) |
| 0.5 | 4.0 | 0.813 | **False** | 0.766 | **False** |
| 0.6 | 5.0 | 0.942 | **False** | 0.766 | **False** |

Full-sample SPY (best equity config, enter=0.5/exit=3.0):
Sharpe 1.091 (pass), MDD 0.254 (**fail**, exceeds 0.25 threshold).

The `enter_level=0.4` cell is a degenerate all-zero-position case (Puell
Multiple on this repo's ~2019-2026 sample window rarely/never falls to
<=0.4 given the halving-adjusted issuance schedule), producing spurious
inf-Sharpe/zero-MDD "passes" that are not real signal -- excluded from the
accept judgment.

## Decision: REJECT

- Crypto (the hypothesis's actual target asset class): 0/54 grid pass, and
  the two non-degenerate full-sample BTC configs both fail Sharpe (0.81,
  0.94, both < 1.0 threshold) and fail MDD (0.77 >> 0.25).
- Equity (out-of-scope sanity check only): best full-sample config narrowly
  fails MDD (0.254 vs 0.25 threshold) despite passing Sharpe.
- No config passes the full validator suite on the metric's actual target
  asset (BTC). Rejected.

This is architecturally distinct from the prior MVRV/NUPL/SOPR "on-chain
data infeasible" dead ends in this repo's knowledge base -- the Puell
Multiple IS computable from price + the public halving schedule alone, so
this iteration is a genuine (if negative) test, not another feasibility
block.
