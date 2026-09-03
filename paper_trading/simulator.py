"""Purely local paper-trading simulator stub.

HARD SAFETY NOTE: this module contains NO code path to any real broker,
exchange trading API, or order-submission endpoint. It only simulates fills
against historical/streamed price data in-memory / to a local JSON ledger
file. See SAFETY.md for the project-wide hard rule this file exists under.

This is intentionally minimal: a strategy module produces target
positions/signals, and this simulator marks them to market using OHLCV data
already available via ``data/loaders.py``. No real capital, no API keys, no
network calls to any brokerage are used or referenced anywhere here.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

DEFAULT_LEDGER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paper_ledger.json")


@dataclass
class PaperFill:
    timestamp: str
    symbol: str
    side: str  # "buy" | "sell"
    quantity: float
    price: float
    note: Optional[str] = None


@dataclass
class PaperPosition:
    symbol: str
    quantity: float = 0.0
    avg_price: float = 0.0


class PaperTradingSimulator:
    """Pure local, in-memory (optionally JSON-persisted) fill simulator.

    No broker/exchange connectivity of any kind. `mark_fill` just records a
    hypothetical fill at a given price (e.g. the close of the bar a strategy
    signal fired on) and updates a local position/PnL ledger.
    """

    def __init__(self, ledger_path: str = DEFAULT_LEDGER_PATH, starting_cash: float = 100_000.0):
        self.ledger_path = ledger_path
        self.cash = starting_cash
        self.positions: Dict[str, PaperPosition] = {}
        self.fills: List[PaperFill] = []

    def mark_fill(self, symbol: str, side: str, quantity: float, price: float, note: Optional[str] = None) -> PaperFill:
        if side not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")

        fill = PaperFill(
            timestamp=datetime.utcnow().isoformat() + "Z",
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            note=note,
        )
        self.fills.append(fill)

        pos = self.positions.setdefault(symbol, PaperPosition(symbol=symbol))
        signed_qty = quantity if side == "buy" else -quantity
        new_qty = pos.quantity + signed_qty

        if side == "buy":
            self.cash -= quantity * price
            if new_qty != 0:
                pos.avg_price = ((pos.quantity * pos.avg_price) + (quantity * price)) / new_qty
        else:
            self.cash += quantity * price

        pos.quantity = new_qty
        return fill

    def mark_to_market(self, prices: Dict[str, float]) -> float:
        """Return total equity (cash + position value) given current prices."""
        equity = self.cash
        for symbol, pos in self.positions.items():
            if symbol in prices:
                equity += pos.quantity * prices[symbol]
        return equity

    def save(self, path: Optional[str] = None) -> None:
        path = path or self.ledger_path
        state = {
            "cash": self.cash,
            "positions": {k: asdict(v) for k, v in self.positions.items()},
            "fills": [asdict(f) for f in self.fills],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    @classmethod
    def load(cls, path: str = DEFAULT_LEDGER_PATH) -> "PaperTradingSimulator":
        sim = cls(ledger_path=path)
        if not os.path.exists(path):
            return sim
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        sim.cash = state.get("cash", sim.cash)
        sim.positions = {
            k: PaperPosition(**v) for k, v in state.get("positions", {}).items()
        }
        sim.fills = [PaperFill(**f) for f in state.get("fills", [])]
        return sim
