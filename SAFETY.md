# SAFETY.md — Hard Safety Boundary for quant-agent

## The single hard rule

**This codebase does not, and must never, contain any function that submits
a real order to a real broker, exchange, or any live-money trading API.**

There is no `place_order`, `submit_order`, `execute_trade`,
`broker.buy(...)`, exchange-authenticated trading client instantiation, or
any equivalent anywhere in this repository. This is a design invariant, not
an accident of the current scaffold — it must remain true as the system
grows.

## Why this matters

The Research Agent role in this project is an LLM (a Hermes cronjob turn)
that autonomously writes and runs strategy code every loop, with no human
approving each iteration in real time. An autonomous agent that can also
place live orders is an unacceptable risk: a bug, a misread signal, or a
subtly wrong backtest-to-live translation could lose real money with no
human in the loop to catch it before execution.

Decoupling "the agent can research and simulate" from "the agent can trade
with real money" is the whole point of this architecture.

## What is safe by construction today

- `data/loaders.py` and `src/quant_agent/data/*` only ever **read** market
  data (yfinance / ccxt "public"/market-data endpoints). ccxt is used here
  strictly as a **read-only market data source**, never with authenticated
  trading credentials.
- `paper_trading/simulator.py` is a pure local, in-process fill simulator.
  It has no network calls, no broker SDK, no API key handling of any kind.
  "Fills" are just arithmetic against historical/streamed prices, persisted
  to a local JSON ledger file.
- `validation/validators.py` only computes metrics (Sharpe, MDD, cost drag,
  walk-forward, parameter sensitivity) over already-fetched data — it cannot
  place trades either.
- `.env.example` / `.gitignore` do not reference any brokerage API key
  variables. If a future task adds a real ccxt authenticated client for
  reading private account data (e.g. balances), that is a distinct,
  explicitly-scoped change and still must not add order placement.

## Principle for any future change

If a future task ever proposes adding real-money order execution
(brokerage API keys, `ccxt` authenticated `create_order` calls, IBKR/Alpaca/
any other live trading SDK, etc.), the following must ALL be true before
that code is merged, regardless of how well-tested paper trading has been:

1. **Explicit, separate human approval** — not implied by "the backtest
   looked good" or "paper trading has been profitable for N days." A human
   must consciously review and approve the specific change that adds live
   order capability.
2. **A hard, human-controlled kill switch** that the Research Agent LLM
   itself cannot disable (e.g. a config flag or credential that only a human
   can set/rotate, not something the agent can write to from within its own
   loop).
3. **A human-in-the-loop gate on individual live orders**, at least during
   an initial period — e.g. orders are queued for human confirmation rather
   than auto-submitted, even after the "auto-approve" infrastructure above
   exists.
4. **Position/size limits enforced outside of the agent's own code path**
   (e.g. broker-side account limits), so a runaway loop cannot scale up
   exposure unilaterally.

Until all of the above exist and have been explicitly approved by a human,
**no code in this repository may call any live order-placement API**, and
any pull request/commit that does so should be treated as a critical safety
violation and reverted.
