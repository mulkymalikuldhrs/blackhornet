"""AutoDiscoveryEnhancer — runtime tool/skill/capability discovery."""

import importlib
import inspect
import json
import os
import pkgutil
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Optional


@dataclass
class DiscoveredCapability:
    id: str
    name: str
    module: str
    description: str
    capability_type: str  # "tool", "skill", "handler", "provider"
    source: str
    discovered_at: float
    last_seen: float
    health: str  # "unknown", "healthy", "unhealthy"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveryResult:
    success: bool
    capabilities: list[DiscoveredCapability]
    source: str
    error: Optional[str] = None
    duration_ms: float = 0.0


class AutoDiscoveryEnhancer:
    def __init__(
        self,
        scan_paths: Optional[list[str]] = None,
        persist_path: Optional[str] = None,
        scan_interval: int = 300,
        auto_persist: bool = True,
    ):
        self._capabilities: dict[str, DiscoveredCapability] = {}
        self._scan_paths = scan_paths or []
        self._persist_path = persist_path
        self._scan_interval = scan_interval
        self._auto_persist = auto_persist
        self._last_scan_time: float = 0.0
        self._total_scans = 0
        self._radar: Any = None
        self._load()

    def _load(self) -> None:
        if not self._persist_path or not os.path.exists(self._persist_path):
            return
        try:
            with open(self._persist_path) as f:
                data = json.load(f)
            for item in data.get("capabilities", []):
                cap = DiscoveredCapability(**item)
                self._capabilities[cap.id] = cap
            self._total_scans = data.get("total_scans", 0)
        except Exception:
            pass

    def _save(self) -> None:
        if not self._persist_path or not self._auto_persist:
            return
        try:
            os.makedirs(os.path.dirname(self._persist_path), exist_ok=True)
            with open(self._persist_path, "w") as f:
                json.dump(
                    {
                        "capabilities": [asdict(c) for c in self._capabilities.values()],
                        "total_scans": self._total_scans,
                    },
                    f,
                    indent=2,
                )
        except Exception:
            pass

    def wire_radar(self, radar: Any) -> None:
        self._radar = radar

    async def scan_modules(self, package_prefix: str = "src") -> DiscoveryResult:
        start = time.time()
        discovered: list[DiscoveredCapability] = []
        try:
            package = importlib.import_module(package_prefix)
            path = getattr(package, "__path__", None)
            if not path:
                return DiscoveryResult(
                    success=False,
                    capabilities=[],
                    source="module_scan",
                    error=f"No __path__ for {package_prefix}",
                )
            for importer, modname, is_pkg in pkgutil.walk_packages(
                path, prefix=f"{package_prefix}.",
                onerror=lambda _: None,
            ):
                for cap in self._scan_module(modname):
                    discovered.append(cap)
        except Exception as e:
            return DiscoveryResult(
                success=False,
                capabilities=[],
                source="module_scan",
                error=str(e),
            )
        for cap in discovered:
            self._capabilities[cap.id] = cap
        self._total_scans += 1
        self._last_scan_time = time.time()
        if self._auto_persist:
            self._save()
        return DiscoveryResult(
            success=True,
            capabilities=discovered,
            source="module_scan",
            duration_ms=(time.time() - start) * 1000,
        )

    def _scan_module(self, modname: str) -> list[DiscoveredCapability]:
        caps: list[DiscoveredCapability] = []
        try:
            mod = importlib.import_module(modname)
            for name, obj in inspect.getmembers(mod):
                if inspect.isfunction(obj) and hasattr(obj, "_evolution_capability"):
                    meta = getattr(obj, "_evolution_capability", {})
                    caps.append(DiscoveredCapability(
                        id=str(uuid.uuid4()),
                        name=name,
                        module=modname,
                        description=meta.get("description", name),
                        capability_type=meta.get("type", "tool"),
                        source="decorator",
                        discovered_at=time.time(),
                        last_seen=time.time(),
                        health="unknown",
                        metadata=meta,
                    ))
        except Exception:
            pass
        return caps

    async def scan_directory(self, path: str) -> DiscoveryResult:
        start = time.time()
        discovered: list[DiscoveredCapability] = []
        if not os.path.isdir(path):
            return DiscoveryResult(
                success=False,
                capabilities=[],
                source="directory_scan",
                error=f"Directory not found: {path}",
            )
        try:
            for fname in os.listdir(path):
                if fname.endswith(".py") and not fname.startswith("_"):
                    modname = fname[:-3]
                    try:
                        spec = importlib.util.spec_from_file_location(
                            modname, os.path.join(path, fname)
                        )
                        if spec and spec.loader:
                            mod = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(mod)
                            for name, obj in inspect.getmembers(mod):
                                if callable(obj) and not name.startswith("_"):
                                    doc = (obj.__doc__ or "").strip()
                                    discovered.append(DiscoveredCapability(
                                        id=str(uuid.uuid4()),
                                        name=name,
                                        module=f"{path}.{modname}",
                                        description=doc[:200] if doc else name,
                                        capability_type="tool",
                                        source=f"file:{fname}",
                                        discovered_at=time.time(),
                                        last_seen=time.time(),
                                        health="unknown",
                                    ))
                    except Exception:
                        pass
        except Exception as e:
            return DiscoveryResult(
                success=False,
                capabilities=[],
                source="directory_scan",
                error=str(e),
            )
        for cap in discovered:
            self._capabilities[cap.id] = cap
        self._total_scans += 1
        self._last_scan_time = time.time()
        if self._auto_persist:
            self._save()
        return DiscoveryResult(
            success=True,
            capabilities=discovered,
            source="directory_scan",
            duration_ms=(time.time() - start) * 1000,
        )

    def discover_peer_capabilities(self, peer_identity: Any) -> list[DiscoveredCapability]:
        caps: list[DiscoveredCapability] = []
        capabilities = []
        if hasattr(peer_identity, "capabilities"):
            capabilities = peer_identity.capabilities
        elif isinstance(peer_identity, dict):
            capabilities = peer_identity.get("capabilities", [])
        for cap_name in capabilities:
            cid = str(uuid.uuid4())
            colony_id = (
                peer_identity.colony_id
                if hasattr(peer_identity, "colony_id")
                else peer_identity.get("colony_id", "unknown")
            )
            caps.append(DiscoveredCapability(
                id=cid,
                name=cap_name,
                module=f"peer:{colony_id}",
                description=f"Peer capability: {cap_name}",
                capability_type="skill",
                source="peer",
                discovered_at=time.time(),
                last_seen=time.time(),
                health="healthy",
            ))
        for cap in caps:
            self._capabilities[cap.id] = cap
        if self._auto_persist:
            self._save()
        return caps

    def get_capabilities(
        self, capability_type: Optional[str] = None, source: Optional[str] = None
    ) -> list[DiscoveredCapability]:
        caps = list(self._capabilities.values())
        if capability_type:
            caps = [c for c in caps if c.capability_type == capability_type]
        if source:
            caps = [c for c in caps if c.source == source]
        return caps

    def get_stats(self) -> dict[str, Any]:
        types: dict[str, int] = {}
        sources: dict[str, int] = {}
        for c in self._capabilities.values():
            types[c.capability_type] = types.get(c.capability_type, 0) + 1
            sources[c.source] = sources.get(c.source, 0) + 1
        return {
            "total_capabilities": len(self._capabilities),
            "total_scans": self._total_scans,
            "last_scan_time": self._last_scan_time,
            "types": types,
            "sources": sources,
            "radar_wired": self._radar is not None,
            "persist_path": self._persist_path,
        }

    def clear(self) -> None:
        self._capabilities.clear()
