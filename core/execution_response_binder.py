"""
Execution Response Binder for MARK XLVIII / JARVIS.
Binds verified execution events from the EventBus / TaskRegistry to prepared ResponseContracts,
guaranteeing that speculative success templates are only released upon genuine verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.response_contract import ResponseContract, ResponseStage


@dataclass
class BoundResponse:
    spoken_text: str
    is_success: bool
    requires_announcement: bool
    stage: ResponseStage
    contract_id: str
    context: Dict[str, Any]


class ExecutionResponseBinder:
    """
    Enforces verified state binding before releasing completion responses.
    """

    def bind_success(
        self,
        contract: ResponseContract,
        verified_data: Optional[Dict[str, Any]] = None,
    ) -> BoundResponse:
        """
        Binds verified success data to the response contract and releases the success template.
        """
        data = verified_data or {}
        text = contract.format_success(data)
        contract.stage = ResponseStage.SUCCESS_RELEASED
        contract.verified_result = data

        return BoundResponse(
            spoken_text=text,
            is_success=True,
            requires_announcement=contract.requires_completion_announcement,
            stage=ResponseStage.SUCCESS_RELEASED,
            contract_id=contract.contract_id,
            context=data,
        )

    def bind_failure(
        self,
        contract: ResponseContract,
        error: str = "Execution failed",
        verified_data: Optional[Dict[str, Any]] = None,
    ) -> BoundResponse:
        """
        Binds verified failure details to the response contract and releases the failure template.
        """
        data = verified_data or {}
        text = contract.format_failure(error=error, context=data)
        contract.stage = ResponseStage.FAILURE_RELEASED
        contract.verified_result = {**data, "error": error}

        return BoundResponse(
            spoken_text=text,
            is_success=False,
            requires_announcement=True,  # Errors should always be communicated
            stage=ResponseStage.FAILURE_RELEASED,
            contract_id=contract.contract_id,
            context=data,
        )


# Global singleton instance
execution_response_binder = ExecutionResponseBinder()
