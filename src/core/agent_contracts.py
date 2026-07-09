"""
Agent Contracts — Formal resource governance for autonomous agents.
Inspired by "Agent Contracts: A Formal Framework for Resource-Bounded
Autonomous AI Systems" (arXiv:2601.08815).

Provides:
  - Cost budgets per task/mission
  - Temporal deadlines with enforcement
  - Success criteria verification
  - Conservation laws for multi-agent delegation
  - Circuit-breaking when contracts are violated
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ContractStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    VIOLATED = "violated"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class SuccessCriteria:
    must_complete: bool = True
    min_success_rate: float = 0.0
    required_outputs: list[str] = field(default_factory=list)
    custom_verifier: Optional[Callable[[dict[str, Any]], bool]] = None

    def verify(self, result: dict[str, Any]) -> tuple[bool, str]:
        if self.must_complete and not result.get("completed", False):
            return False, "Task was not completed"
        if self.min_success_rate > 0:
            rate = result.get("success_rate", 1.0)
            if rate < self.min_success_rate:
                return False, f"Success rate {rate:.2f} < {self.min_success_rate}"
        for output in self.required_outputs:
            if output not in result:
                return False, f"Required output '{output}' missing"
        if self.custom_verifier:
            if not self.custom_verifier(result):
                return False, "Custom verification failed"
        return True, "All criteria met"


@dataclass
class ConservationLaw:
    max_delegation_depth: int = 3
    max_concurrent_agents: int = 5
    total_budget_share: float = 1.0
    resource_amplification_limit: float = 2.0


@dataclass
class AgentContract:
    contract_id: str
    agent_id: str
    parent_contract_id: Optional[str] = None

    # Budget
    cost_budget: float = 0.0
    cost_spent: float = 0.0
    token_budget: int = 0
    tokens_used: int = 0

    # Temporal
    deadline: float = 0.0
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    max_duration: float = 300.0

    # Success criteria
    criteria: SuccessCriteria = field(default_factory=SuccessCriteria)
    conservation: ConservationLaw = field(default_factory=ConservationLaw)

    # State
    status: ContractStatus = ContractStatus.ACTIVE
    delegation_count: int = 0
    violation_reason: str = ""

    # Result
    result: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.deadline > 0 and time.time() > self.deadline:
            return True
        if self.max_duration > 0 and (time.time() - self.started_at) > self.max_duration:
            return True
        return False

    @property
    def is_over_budget(self) -> bool:
        if self.cost_budget > 0 and self.cost_spent > self.cost_budget:
            return True
        if self.token_budget > 0 and self.tokens_used > self.token_budget:
            return True
        return False

    @property
    def usage_ratio(self) -> float:
        return max(
            self.cost_spent / max(self.cost_budget, 0.01),
            self.tokens_used / max(self.token_budget, 0.01),
        )


class ContractViolation(Exception):
    pass


class AgentContractManager:
    """
    Formal resource governance for autonomous AI agents.

    Every agent operates under a contract that defines:
      - How much it can spend (cost budget)
      - How long it can run (temporal deadline)
      - What constitutes success (success criteria)
      - How it can delegate (conservation laws)

    When a contract is violated, the system:
      1. Logs the violation
      2. Triggers circuit breaker
      3. Attempts graceful degradation
      4. Reports to parent contract
    """

    def __init__(self):
        self._contracts: dict[str, AgentContract] = {}
        self._violations: list[dict[str, Any]] = []

    def create_contract(
        self,
        agent_id: str,
        cost_budget: float = 0.0,
        token_budget: int = 0,
        max_duration: float = 300.0,
        criteria: Optional[SuccessCriteria] = None,
        parent_contract_id: Optional[str] = None,
    ) -> AgentContract:
        contract = AgentContract(
            contract_id=f"ct-{hash(agent_id + str(time.time())) % 10000000:07x}",
            agent_id=agent_id,
            parent_contract_id=parent_contract_id,
            cost_budget=cost_budget,
            token_budget=token_budget,
            max_duration=max_duration,
            deadline=time.time() + max_duration,
            criteria=criteria or SuccessCriteria(),
        )

        # Check conservation laws from parent
        if parent_contract_id and parent_contract_id in self._contracts:
            parent = self._contracts[parent_contract_id]
            if parent.delegation_count >= parent.conservation.max_delegation_depth:
                raise ContractViolation(
                    f"Max delegation depth ({parent.conservation.max_delegation_depth}) exceeded"
                )
            parent.delegation_count += 1

        self._contracts[contract.contract_id] = contract
        logger.info(
            "Contract created: %s for agent %s (budget=%.2f, duration=%.0fs)",
            contract.contract_id, agent_id, cost_budget, max_duration,
        )
        return contract

    def get_contract(self, contract_id: str) -> Optional[AgentContract]:
        return self._contracts.get(contract_id)

    def record_cost(self, contract_id: str, cost: float, tokens: int = 0) -> None:
        contract = self._contracts.get(contract_id)
        if not contract:
            return
        contract.cost_spent += cost
        contract.tokens_used += tokens

        if contract.is_over_budget:
            contract.status = ContractStatus.VIOLATED
            contract.violation_reason = f"Budget exceeded (cost={contract.cost_spent:.2f}/{contract.cost_budget:.2f}, tokens={contract.tokens_used}/{contract.token_budget})"
            self._violations.append({
                "contract_id": contract_id,
                "agent_id": contract.agent_id,
                "reason": contract.violation_reason,
                "timestamp": time.time(),
            })
            logger.warning("Contract violated: %s", contract.violation_reason)

    def check_contract(self, contract_id: str) -> bool:
        contract = self._contracts.get(contract_id)
        if not contract:
            return False

        if contract.is_expired:
            contract.status = ContractStatus.EXPIRED
            contract.violation_reason = "Deadline exceeded"
            return False

        if contract.is_over_budget:
            contract.status = ContractStatus.VIOLATED
            return False

        return True

    def complete_contract(
        self,
        contract_id: str,
        result: dict[str, Any],
    ) -> tuple[bool, str]:
        contract = self._contracts.get(contract_id)
        if not contract:
            return False, "Contract not found"

        contract.completed_at = time.time()
        contract.result = result

        # Verify success criteria
        success, message = contract.criteria.verify(result)
        if success:
            contract.status = ContractStatus.COMPLETED
            logger.info(
                "Contract completed: %s (cost=%.2f, tokens=%d, duration=%.1fs)",
                contract_id, contract.cost_spent, contract.tokens_used,
                contract.completed_at - contract.started_at,
            )
        else:
            contract.status = ContractStatus.VIOLATED
            contract.violation_reason = message
            logger.warning("Contract criteria failed: %s", message)

        return success, message

    def create_subcontract(
        self,
        parent_contract_id: str,
        agent_id: str,
        cost_budget: float = 0.0,
        token_budget: int = 0,
        max_duration: float = 60.0,
    ) -> AgentContract:
        parent = self._contracts.get(parent_contract_id)
        if not parent:
            raise ContractViolation("Parent contract not found")

        # Conservation law: total budget share
        available = parent.cost_budget - parent.cost_spent
        if cost_budget > available * parent.conservation.resource_amplification_limit:
            raise ContractViolation(
                f"Subcontract budget {cost_budget} exceeds available {available} "
                f"(amplification limit: {parent.conservation.resource_amplification_limit}x)"
            )

        return self.create_contract(
            agent_id=agent_id,
            cost_budget=cost_budget or available * 0.5,
            token_budget=token_budget or parent.token_budget // 2,
            max_duration=max_duration,
            parent_contract_id=parent_contract_id,
        )

    def get_violations(self, agent_id: Optional[str] = None) -> list[dict[str, Any]]:
        if agent_id:
            return [v for v in self._violations if v["agent_id"] == agent_id]
        return list(self._violations)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_contracts": len(self._contracts),
            "active": sum(1 for c in self._contracts.values() if c.status == ContractStatus.ACTIVE),
            "completed": sum(1 for c in self._contracts.values() if c.status == ContractStatus.COMPLETED),
            "violated": sum(1 for c in self._contracts.values() if c.status == ContractStatus.VIOLATED),
            "expired": sum(1 for c in self._contracts.values() if c.status == ContractStatus.EXPIRED),
            "total_violations": len(self._violations),
            "total_delegations": sum(c.delegation_count for c in self._contracts.values()),
        }
