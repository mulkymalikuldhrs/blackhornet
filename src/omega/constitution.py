"""AI-Engineering-OS Constitution — base law of BlackHornet."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConstitutionCheck:
    name: str
    present: bool
    valid: bool = False
    path: Optional[str] = None


class Constitution:
    """Validate and enforce the AI-Engineering-OS Constitution."""

    REQUIRED_ROOT = [
        "README.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md",
        "COPILOT.md", "CURSOR.md", "MASTER_SYSTEM_PROMPT.md",
    ]

    REQUIRED_CORE_DOCS = [
        "VISION", "PRD", "ARCHITECTURE", "SPEC", "API", "SDK",
        "RUNTIME", "SECURITY", "STYLEGUIDE", "TESTING", "ROADMAP",
        "ADR", "TASKS", "CHANGELOG", "PROJECT_RULES", "PROJECT_CONTEXT",
        "AI_MEMORY", "GLOSSARY", "DOMAIN_MODEL", "RISK_REGISTER",
        "RELEASE_PLAN", "CONTRIBUTING",
    ]

    def __init__(self, root: Optional[str] = None) -> None:
        self.root = root or self._detect_root()
        self.checks: list[ConstitutionCheck] = []

    def _detect_root(self) -> str:
        for p in [os.environ.get("DHAHERLABS", "/sdcard/dhaherlabs"), os.getcwd()]:
            bh = os.path.join(p, "blackhornet-worktree")
            if os.path.isdir(bh):
                return bh
        return os.getcwd()

    def validate(self) -> dict:
        self.checks = []
        for doc in self.REQUIRED_ROOT:
            path = os.path.join(self.root, doc)
            exists = os.path.isfile(path)
            valid = exists and os.path.getsize(path) > 50
            self.checks.append(ConstitutionCheck(name=doc, present=exists, valid=valid, path=path if exists else None))

        docs_dir = os.path.join(self.root, "docs")
        if os.path.isdir(docs_dir):
            for doc in self.REQUIRED_CORE_DOCS:
                path = os.path.join(docs_dir, doc)
                path_md = os.path.join(docs_dir, f"{doc}.md")
                exists = os.path.isfile(path) or os.path.isfile(path_md)
                valid = exists and ((os.path.isfile(path) and os.path.getsize(path) > 50) or (os.path.isfile(path_md) and os.path.getsize(path_md) > 50))
                self.checks.append(ConstitutionCheck(name=doc, present=exists, valid=valid, path=path if exists else None))

        root_score = self._score_list(self.REQUIRED_ROOT)
        core_score = self._score_list(self.REQUIRED_CORE_DOCS)
        return {
            "constitution_score": root_score["score"] + core_score["score"],
            "max_score": 25,
            "root_docs": root_score,
            "core_docs": core_score,
            "checks": [{"name": c.name, "present": c.present, "valid": c.valid} for c in self.checks],
        }

    def _score_list(self, names: list[str]) -> dict:
        present = sum(1 for c in self.checks if c.name in names and c.present)
        valid = sum(1 for c in self.checks if c.name in names and c.valid)
        return {"present": present, "valid": valid, "total": len(names), "score": int((valid / len(names)) * 25) if names else 0}

    def check_doc(self, name: str) -> ConstitutionCheck:
        self.validate()
        for c in self.checks:
            if c.name == name:
                return c
        return ConstitutionCheck(name=name, present=False)
