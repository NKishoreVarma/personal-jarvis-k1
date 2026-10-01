"""
Completion Response Cache for MARK XLVIII / JARVIS.
Provides turn-isolated, TTL-bounded caching for prepared ResponseContracts.
"""

from __future__ import annotations

import time
from typing import Dict, Optional

from core.response_contract import ResponseContract, ResponseStage


class CompletionResponseCache:
    """
    In-memory bounded cache for prepared response contracts.
    """

    def __init__(self, max_entries: int = 50):
        self.max_entries = max_entries
        self._contracts_by_turn: Dict[str, ResponseContract] = {}
        self._contracts_by_id: Dict[str, ResponseContract] = {}

    def store_contract(self, contract: ResponseContract) -> None:
        """Stores a prepared response contract under its turn_id and contract_id."""
        self.cleanup_expired()
        self._contracts_by_turn[contract.turn_id] = contract
        self._contracts_by_id[contract.contract_id] = contract

    def get_contract(self, turn_id: str) -> Optional[ResponseContract]:
        """Retrieves active unexpired contract for a turn."""
        contract = self._contracts_by_turn.get(turn_id)
        if contract and not contract.is_expired() and contract.stage != ResponseStage.INVALIDATED:
            return contract
        return None

    def get_by_id(self, contract_id: str) -> Optional[ResponseContract]:
        """Retrieves active contract by contract_id."""
        contract = self._contracts_by_id.get(contract_id)
        if contract and not contract.is_expired() and contract.stage != ResponseStage.INVALIDATED:
            return contract
        return None

    def invalidate_turn(self, turn_id: str) -> None:
        """Invalidates and removes contracts associated with a turn."""
        contract = self._contracts_by_turn.pop(turn_id, None)
        if contract:
            contract.stage = ResponseStage.INVALIDATED
            self._contracts_by_id.pop(contract.contract_id, None)

    def cleanup_expired(self) -> None:
        """Purges expired contracts."""
        now = time.monotonic()
        for t_id, c in list(self._contracts_by_turn.items()):
            if c.is_expired() or c.stage == ResponseStage.INVALIDATED:
                self._contracts_by_turn.pop(t_id, None)
                self._contracts_by_id.pop(c.contract_id, None)


# Global singleton instance
completion_response_cache = CompletionResponseCache()
