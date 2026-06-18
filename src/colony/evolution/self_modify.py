"""SelfModifyEngine — proposes codebase changes based on patterns with safety gating."""

import difflib
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


CHANGE_TYPE_REFACTOR = "refactor"
CHANGE_TYPE_OPTIMIZE = "optimize"
CHANGE_TYPE_FIX = "fix"
CHANGE_TYPE_FEATURE = "feature"


@dataclass
class ChangeProposal:
    id: str
    change_type: str
    file_path: str
    description: str
    diff: str
    original_snippet: str
    proposed_snippet: str
    confidence: float
    rationale: str
    proposed_by: str
    proposed_at: float
    status: str  # "pending", "approved", "rejected", "applied"
    safety_flags: list[str] = field(default_factory=list)
    applied_at: Optional[float] = None


@dataclass
class ApplyResult:
    success: bool
    proposal_id: str
    file_path: str
    error: Optional[str] = None
    backup_path: Optional[str] = None


class SelfModifyEngine:
    def __init__(
        self,
        codebase_root: str = ".",
        max_proposals: int = 100,
        min_confidence: float = 0.6,
        require_approval: bool = True,
        backup_enabled: bool = True,
        allowed_paths: Optional[list[str]] = None,
    ):
        self._codebase_root = os.path.abspath(codebase_root)
        self._proposals: dict[str, ChangeProposal] = {}
        self._max_proposals = max_proposals
        self._min_confidence = min_confidence
        self._require_approval = require_approval
        self._backup_enabled = backup_enabled
        self._allowed_paths = allowed_paths or ["src"]
        self._total_proposed = 0
        self._total_applied = 0
        self._total_rejected = 0

    def _is_path_allowed(self, file_path: str) -> bool:
        abs_path = os.path.abspath(file_path)
        try:
            rel = os.path.relpath(abs_path, self._codebase_root)
        except ValueError:
            return False
        return any(rel.startswith(p) for p in self._allowed_paths)

    def _create_backup(self, file_path: str) -> Optional[str]:
        if not self._backup_enabled:
            return None
        if not os.path.exists(file_path):
            return None
        try:
            backup_dir = os.path.join(self._codebase_root, ".evolution_backups")
            os.makedirs(backup_dir, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            fname = os.path.basename(file_path)
            backup = os.path.join(backup_dir, f"{fname}.{ts}.bak")
            with open(file_path) as f:
                content = f.read()
            with open(backup, "w") as f:
                f.write(content)
            return backup
        except Exception:
            return None

    def propose_change(
        self,
        change_type: str,
        file_path: str,
        description: str,
        original_snippet: str,
        proposed_snippet: str,
        rationale: str,
        proposed_by: str = "evolution",
        confidence: float = 0.7,
    ) -> ChangeProposal:
        if not self._is_path_allowed(file_path):
            raise ValueError(f"Path not allowed: {file_path}")
        if change_type not in (CHANGE_TYPE_REFACTOR, CHANGE_TYPE_OPTIMIZE, CHANGE_TYPE_FIX, CHANGE_TYPE_FEATURE):
            change_type = CHANGE_TYPE_REFACTOR
        confidence = max(0.0, min(1.0, confidence))
        diff = self._generate_diff(file_path, original_snippet, proposed_snippet)
        safety_flags = self._check_safety(original_snippet, proposed_snippet, change_type)
        proposal = ChangeProposal(
            id=str(uuid.uuid4()),
            change_type=change_type,
            file_path=os.path.abspath(file_path),
            description=description,
            diff=diff,
            original_snippet=original_snippet,
            proposed_snippet=proposed_snippet,
            confidence=confidence,
            rationale=rationale,
            proposed_by=proposed_by,
            proposed_at=time.time(),
            status="pending",
            safety_flags=safety_flags,
        )
        self._proposals[proposal.id] = proposal
        self._total_proposed += 1
        if len(self._proposals) > self._max_proposals:
            oldest = min(self._proposals.keys(), key=lambda k: self._proposals[k].proposed_at)
            del self._proposals[oldest]
        return proposal

    def _generate_diff(self, file_path: str, original: str, proposed: str) -> str:
        orig_lines = original.splitlines(keepends=True)
        prop_lines = proposed.splitlines(keepends=True)
        diff = difflib.unified_diff(
            orig_lines,
            prop_lines,
            fromfile=f"a/{os.path.basename(file_path)}",
            tofile=f"b/{os.path.basename(file_path)}",
        )
        return "".join(diff)

    def _check_safety(self, original: str, proposed: str, change_type: str) -> list[str]:
        flags: list[str] = []
        if len(proposed) > len(original) * 3:
            flags.append("large_growth")
        if proposed.count("import ") > original.count("import ") + 3:
            flags.append("new_imports")
        if "delete" in change_type or "remove" in change_type:
            flags.append("destructive_change")
        return flags

    def approve(self, proposal_id: str) -> bool:
        if proposal_id not in self._proposals:
            return False
        if self._proposals[proposal_id].status != "pending":
            return False
        self._proposals[proposal_id].status = "approved"
        return True

    def reject(self, proposal_id: str) -> bool:
        if proposal_id not in self._proposals:
            return False
        self._proposals[proposal_id].status = "rejected"
        self._total_rejected += 1
        return True

    def apply(self, proposal_id: str) -> ApplyResult:
        if proposal_id not in self._proposals:
            return ApplyResult(
                success=False,
                proposal_id=proposal_id,
                file_path="",
                error="Proposal not found",
            )
        prop = self._proposals[proposal_id]
        if prop.status == "applied":
            return ApplyResult(
                success=False,
                proposal_id=proposal_id,
                file_path=prop.file_path,
                error="Already applied",
            )
        if self._require_approval and prop.status != "approved":
            return ApplyResult(
                success=False,
                proposal_id=proposal_id,
                file_path=prop.file_path,
                error="Not approved",
            )
        if prop.confidence < self._min_confidence:
            return ApplyResult(
                success=False,
                proposal_id=proposal_id,
                file_path=prop.file_path,
                error=f"Confidence {prop.confidence} below minimum {self._min_confidence}",
            )
        if not os.path.exists(prop.file_path):
            return ApplyResult(
                success=False,
                proposal_id=proposal_id,
                file_path=prop.file_path,
                error="File does not exist",
            )
        try:
            with open(prop.file_path) as f:
                content = f.read()
        except Exception as e:
            return ApplyResult(
                success=False,
                proposal_id=proposal_id,
                file_path=prop.file_path,
                error=f"Cannot read file: {e}",
            )
        if prop.original_snippet not in content:
            return ApplyResult(
                success=False,
                proposal_id=proposal_id,
                file_path=prop.file_path,
                error="Original snippet not found in file (file may have changed)",
            )
        backup = self._create_backup(prop.file_path)
        try:
            new_content = content.replace(prop.original_snippet, prop.proposed_snippet, 1)
            with open(prop.file_path, "w") as f:
                f.write(new_content)
            prop.status = "applied"
            prop.applied_at = time.time()
            self._total_applied += 1
            return ApplyResult(
                success=True,
                proposal_id=proposal_id,
                file_path=prop.file_path,
                backup_path=backup,
            )
        except Exception as e:
            return ApplyResult(
                success=False,
                proposal_id=proposal_id,
                file_path=prop.file_path,
                error=f"Apply failed: {e}",
            )

    def get_proposal(self, proposal_id: str) -> Optional[ChangeProposal]:
        return self._proposals.get(proposal_id)

    def get_proposals(
        self,
        status: Optional[str] = None,
        change_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[ChangeProposal]:
        props = list(self._proposals.values())
        if status:
            props = [p for p in props if p.status == status]
        if change_type:
            props = [p for p in props if p.change_type == change_type]
        props.sort(key=lambda p: p.proposed_at, reverse=True)
        return props[:limit]

    def get_stats(self) -> dict[str, Any]:
        statuses: dict[str, int] = {}
        types: dict[str, int] = {}
        for p in self._proposals.values():
            statuses[p.status] = statuses.get(p.status, 0) + 1
            types[p.change_type] = types.get(p.change_type, 0) + 1
        return {
            "total_proposed": self._total_proposed,
            "total_applied": self._total_applied,
            "total_rejected": self._total_rejected,
            "pending_proposals": statuses.get("pending", 0),
            "approved_proposals": statuses.get("approved", 0),
            "change_types": types,
            "min_confidence": self._min_confidence,
            "require_approval": self._require_approval,
            "backup_enabled": self._backup_enabled,
            "codebase_root": self._codebase_root,
        }
