"""
Agent Communication Bus for Multi-Agent Collaboration in MARK XLVIII / JARVIS.
Provides non-blocking pub/sub message routing between specialized agents.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from core.agent_message_contract import AgentMessageContract, AgentMessageType


class AgentCommunicationBus:
    """
    Message bus routing messages between orchestrator, observer, diagnostic, executor, and verifier agents.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[AgentMessageContract], None]]] = {}
        self._message_history: List[AgentMessageContract] = []

    def subscribe(self, recipient_id: str, callback: Callable[[AgentMessageContract], None]) -> None:
        self._subscribers.setdefault(recipient_id, []).append(callback)

    def publish(self, message: AgentMessageContract) -> None:
        self._message_history.append(message)

        # 1. Deliver to specific recipient
        if message.recipient_id in self._subscribers:
            for cb in self._subscribers[message.recipient_id]:
                try:
                    cb(message)
                except Exception as e:
                    print(f"[COMM_BUS] Error in subscriber callback for {message.recipient_id}: {e}")

        # 2. Deliver broadcast
        if message.recipient_id == "BROADCAST":
            for r_id, cbs in self._subscribers.items():
                for cb in cbs:
                    try:
                        cb(message)
                    except Exception:
                        pass

    def get_messages_for_goal(self, goal_id: str) -> List[AgentMessageContract]:
        return [m for m in self._message_history if m.goal_id == goal_id]

    def clear(self) -> None:
        self._subscribers.clear()
        self._message_history.clear()


# Global singleton instance
agent_communication_bus = AgentCommunicationBus()
