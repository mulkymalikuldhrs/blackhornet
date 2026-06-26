"""DeerFlow-inspired skill extension system for agents."""
from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SkillExecutionMode(Enum):
    SYNC = "sync"
    ASYNC = "async"
    DEFERRED = "deferred"


@dataclass
class SkillExtension:
    name: str
    module_path: str
    function_name: str
    mode: SkillExecutionMode = SkillExecutionMode.SYNC
    description: str = ""
    enabled: bool = True


class SkillExtensionSystem:
    """Dynamic skill loading and execution system for agents."""

    def __init__(self) -> None:
        self.extensions: Dict[str, SkillExtension] = {}
        self._loaded: Dict[str, Callable] = {}

    def register_extension(self, ext: SkillExtension) -> None:
        self.extensions[ext.name] = ext
        logger.info(f"Registered skill extension: {ext.name}")

    def load_extension(self, name: str) -> Optional[Callable]:
        ext = self.extensions.get(name)
        if not ext:
            logger.warning(f"Extension {name} not found")
            return None

        try:
            module = importlib.import_module(ext.module_path)
            func = getattr(module, ext.function_name)
            self._loaded[name] = func
            logger.info(
                f"Loaded extension {name} from {ext.module_path}.{ext.function_name}"
            )
            return func
        except Exception as e:
            logger.error(f"Failed to load extension {name}: {e}")
            return None

    def execute(self, name: str, *args: Any, **kwargs: Any) -> Any:
        func = self._loaded.get(name)
        if not func:
            func = self.load_extension(name)
        if not func:
            raise RuntimeError(f"Cannot execute extension {name}: not loaded")
        return func(*args, **kwargs)

    def list_loaded(self) -> List[str]:
        return list(self._loaded.keys())

    def list_registered(self) -> List[SkillExtension]:
        return list(self.extensions.values())
