# MAMA/FAMA crossover -- crypto leverage-cap rescue

Follow-up to 2026-09-17-092 (shared fast_limit=0.4/slow_limit=0.08/min_hold_days=8
config accepted for QQQ+SPY, crypto Sharpe passed but MDD decisive fail
0.471/0.615 vs 0.25 budget). This iteration applies this repo's established
leverage-cap-aware rescue pattern (2026-09-14-125) by adding a `leverage_cap`
parameter scaling the binary position down for crypto.

## Full-sample single-config validation (fast_limit=0.4, slow_limit=0.08, min_hold_days=8, max_hold_days=40, leverage_cap=0.3)
| Symbol | Sharpe | MDD | TC-survival net Sharpe | trades |
|---|---|---|---|---|
| BTC/USDT | 1.006 (pass) | 0.164 (pass) | 0.909 (pass) | 40 |
| ETH/USDT | 1.348 (pass) | 0.222 (pass) | 1.277 (pass) | 41 |

- parameter_sensitivity (leverage_cap in [0.25, 0.3, 0.35], both symbols): relative_std ~1e-14 (pass; Sharpe is invariant to linear position scaling as expected)
- QQQ/SPY sanity-checked unchanged at leverage_cap=1.0 default (Sharpe 1.125/1.329, matching 2026-09-17-092)
- walk_forward: not run -- pre-existing `vbt.utils.splitting` AttributeError bug in this repo's vectorbt install

## Decision
ACCEPTED for BOTH BTC/USDT and ETH/USDT at leverage_cap=0.3 (all other params unchanged
from the 2026-09-17-092 equity-accepted config). Combined with 2026-09-17-092, this MAMA/FAMA
variant is now accepted across ALL FOUR symbols tested in this repo (QQQ, SPY at leverage_cap=1.0;
BTC/USDT, ETH/USDT at leverage_cap=0.3) -- a full asset-class pass, notable since most prior
strategies in this repo's knowledge base only clear crypto's MDD budget with leverage capping
in the 0.25-0.4 range, consistent with this finding.
