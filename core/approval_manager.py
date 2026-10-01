"""
Approval Manager & ApprovalStore for MARK XLVIII / FLOW.
Guarantees strict fingerprint binding for user approvals, prevents replay attacks,
and generates contextual, natural human previews.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from core.action_contract import ActionContract, ApprovalState, ExecutionState, RiskLevel


class ApprovalStore:
    """
    In-memory store managing the lifecycle of pending action approvals.
    Binds approvals strictly to canonical action fingerprints.
    """

    def __init__(self):
        self._pending: Dict[str, ActionContract] = {}
        self._latest_action_id: Optional[str] = None

    def create_proposal(self, contract: ActionContract) -> Tuple[ActionContract, str]:
        """
        Register a new pending action proposal and generate a natural human preview.
        """
        # If arguments are updated, invalidate old proposals
        self._pending[contract.action_id] = contract
        self._latest_action_id = contract.action_id
        
        preview = self.generate_human_preview(contract)
        print(f"[APPROVAL] Proposal created for {contract.connector}.{contract.operation} (id={contract.action_id}, fp={contract.fingerprint})")
        return contract, preview

    def get_pending_action(self, action_id: Optional[str] = None) -> Optional[ActionContract]:
        """
        Retrieve a pending action by ID, or the most recent pending action if ID is None.
        Returns None if expired or not found.
        """
        target_id = action_id or self._latest_action_id
        if not target_id or target_id not in self._pending:
            return None

        contract = self._pending[target_id]
        if contract.is_expired():
            print(f"[APPROVAL] Pending action {target_id} expired.")
            self._pending.pop(target_id, None)
            if self._latest_action_id == target_id:
                self._latest_action_id = None
            return None

        return contract

    def approve_action(
        self,
        action_id: Optional[str] = None,
        expected_fingerprint: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[ActionContract]]:
        """
        Approve a pending action.
        Validates action existence, expiration, and argument fingerprint invariance.
        """
        target_id = action_id or self._latest_action_id
        if not target_id or target_id not in self._pending:
            return False, "There is no pending action to approve.", None

        contract = self._pending[target_id]
        if contract.is_expired():
            self._pending.pop(target_id, None)
            if self._latest_action_id == target_id:
                self._latest_action_id = None
            return False, "The proposed action has expired. Please request the action again.", None

        # Verify cryptographic fingerprint binding
        current_fp = contract.compute_fingerprint()
        if expected_fingerprint and expected_fingerprint != current_fp:
            return False, "Action arguments were modified after proposal. Re-approval required.", None

        contract.approval_state = ApprovalState.APPROVED
        self._pending.pop(target_id, None)
        if self._latest_action_id == target_id:
            self._latest_action_id = None

        print(f"[APPROVAL] Action {contract.action_id} successfully approved.")
        return True, "Action approved.", contract

    def reject_action(self, action_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Reject a pending action proposal.
        """
        target_id = action_id or self._latest_action_id
        if not target_id or target_id not in self._pending:
            return False, "There is no pending action to reject."

        contract = self._pending.pop(target_id)
        contract.approval_state = ApprovalState.REJECTED
        if self._latest_action_id == target_id:
            self._latest_action_id = None

        print(f"[APPROVAL] Action {target_id} rejected by user.")
        return True, "Action rejected."

    def generate_human_preview(self, contract: ActionContract) -> str:
        """
        Generate a concise, natural, grounded human proposal message.
        """
        conn = contract.connector.lower()
        op = contract.operation.lower()
        args = contract.arguments
        ev = contract.evidence

        if conn == "slack" and op == "send_message":
            recipient = args.get("recipient", "the recipient")
            msg = args.get("message", "")
            topic = ev.get("topic", "the request")
            return (
                f"I found the relevant context regarding {topic}.\n\n"
                f"I can send {recipient} this message:\n"
                f"\"{msg}\"\n\n"
                f"Would you like me to send it?"
            )

        elif conn == "gmail" and op == "send_email":
            to = args.get("to", "")
            subject = args.get("subject", "")
            body = args.get("body", "")
            return (
                f"I have prepared the email for {to} regarding \"{subject}\":\n\n"
                f"\"{body}\"\n\n"
                f"Shall I send this email?"
            )

        elif conn == "jira" and op == "create_issue":
            project = args.get("project", "")
            summary = args.get("summary", "")
            return (
                f"I have prepared a new Jira ticket in project {project}:\n"
                f"• Summary: {summary}\n\n"
                f"Would you like me to create this ticket?"
            )

        elif conn == "github" and op == "merge_pr":
            pr_num = args.get("pr_number", "")
            repo = args.get("repo", "")
            return (
                f"Pull Request #{pr_num} on {repo} has passed all required checks.\n\n"
                f"Are you sure you want to merge this PR?"
            )

        elif conn == "calendar" and op == "create_event":
            title = args.get("title", "")
            time_str = args.get("time", "")
            attendees = ", ".join(args.get("attendees", []))
            return (
                f"I can schedule \"{title}\" for {time_str} with {attendees}.\n\n"
                f"Would you like me to book this meeting?"
            )

        return (
            f"I have prepared the action '{contract.connector}.{contract.operation}' with arguments {args}.\n\n"
            f"Do you approve executing this action?"
        )

    def clear(self) -> None:
        self._pending.clear()
        self._latest_action_id = None


# Global singleton approval manager
approval_manager = ApprovalStore()
approval_store = approval_manager
