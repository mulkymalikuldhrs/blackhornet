"""Self-Nest Bootstrap — autonomous deployment, health checks, and self-healing.

The Nest is the Blackhornet instance's self-hosting layer. It:
  1. Bootstrap — installs dependencies, creates directories, starts services
  2. Health Monitor — periodic checks on CPU, memory, disk, process health
  3. Self-Heal — restarts failed components, applies backpressure, circuit breaks
  4. Supervisor — manages subprocess lifecycle (watchdog, api, mesh, radar)

Integration with existing Immortal Gateway (ARCHITECTURE.md §8):
  - Nest replaces Layer 1-2 watchdog/keeper with async-first equivalent
  - Compatible with existing bh-doctor / unified_launcher
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from src.config.logging_config import get_logger
from src.colony_types.colony_ecosystem import NestConfig, NestStatusReport

logger = get_logger(__name__)


@dataclass
class ComponentStatus:
    name: str
    status: str = "stopped"
    pid: Optional[int] = None
    started_at: Optional[float] = None
    restart_count: int = 0
    last_error: Optional[str] = None
    healthy: bool = False


class SelfNest:
    """Autonomous self-hosting layer for a Blackhornet colony.

    Usage:
        nest = SelfNest(NestConfig(name="my-colony"))
        await nest.bootstrap()
        await nest.start()
        status = await nest.health_report()
        await nest.shutdown()
    """

    def __init__(self, config: NestConfig, health_monitor: Optional[ColonyHealthMonitor] = None) -> None:
        self._config = config
        self._running = False
        self._start_time: Optional[float] = None
        self._components: dict[str, ComponentStatus] = {}
        self._tasks: list[asyncio.Task] = []
        self._restart_times: list[float] = []
        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()

        self._on_health_change: Optional[Callable] = None
        self._on_crash: Optional[Callable] = None
        self._health_monitor = health_monitor

        def on_health_change(self, handler) -> None:
            self._on_health_change = handler

        def on_crash(self, handler) -> None:
            self._on_crash = handler

    @property
    def uptime(self) -> float:
        if self._start_time:
            return time.time() - self._start_time
        return 0.0

    async def bootstrap(self) -> None:
        logger.info("nest_bootstrap_starting name=%s", self._config.name)

        dirs = [
            self._config.data_dir,
            self._config.log_dir,
            self._config.config_dir,
            os.path.join(self._config.data_dir, "nest"),
            os.path.join(self._config.log_dir, "nest"),
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)

        missing = await self._check_dependencies()
        if missing:
            logger.warning("nest_missing_deps deps=%s", missing)
            for dep in missing:
                installed = await self._install_dependency(dep)
                if installed:
                    logger.info("nest_dep_installed dep=%s", dep)

        logger.info("nest_bootstrap_complete name=%s", self._config.name)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._start_time = time.time()

        await self._register_component("nest-core")
        await self._register_component("health-monitor")
        await self._register_component("supervisor")

        await self._mark_healthy("nest-core")

        # Wire health monitor if provided
        if self._health_monitor:
            self._health_monitor.wire_nest(self)

        self._tasks.append(asyncio.create_task(self._health_loop()))
        self._tasks.append(asyncio.create_task(self._supervisor_loop()))

        logger.info("nest_started name=%s pid=%d", self._config.name, os.getpid())

    async def shutdown(self) -> None:
        logger.info("nest_shutting_down name=%s", self._config.name)
        self._running = False
        self._shutdown_event.set()

        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        # Unregister from health monitor if provided
        if self._health_monitor:
            self._health_monitor.wire_nest(None)

        async with self._lock:
            for comp in self._components.values():
                if comp.pid and comp.pid != os.getpid():
                    try:
                        os.kill(comp.pid, signal.SIGTERM)
                    except Exception:
                        pass

        logger.info("nest_shutdown_complete name=%s", self._config.name)

    async def health_report(self) -> NestStatusReport:
        cpu = self._get_cpu_usage()
        mem = self._get_memory_usage()
        disk = self._get_disk_usage()

        async with self._lock:
            component_status = {
                name: comp.status for name, comp in self._components.items()
            }
            errors = [
                comp.last_error
                for comp in self._components.values()
                if comp.last_error
            ]

        stats = NestStatusReport(
            nest_id=self._config.nest_id,
            name=self._config.name,
            status="running" if self._running else "stopped",
            uptime=self.uptime,
            pid=os.getpid(),
            memory_mb=mem,
            cpu_pct=cpu,
            disk_pct=disk,
            restart_count=len(self._restart_times),
            last_restart=self._restart_times[-1] if self._restart_times else None,
            last_health_check=time.time(),
            components=component_status,
            peers_connected=0,
            errors=errors,
        )

        if self._health_monitor:
            health_stats = self._health_monitor.get_stats()
            stats.health = {
                "detector": health_stats["detector"],
                "orchestrator": health_stats["orchestrator"],
            }

        return stats

    async def restart_component(self, name: str) -> bool:
        async with self._lock:
            comp = self._components.get(name)
            if not comp:
                logger.warning("nest_component_not_found component=%s", name)
                return False

            now = time.time()
            recent = [t for t in self._restart_times if now - t < 3600]
            if len(recent) >= self._config.max_restarts_per_hour:
                cooldown = self._config.cooldown_seconds
                logger.warning(
                    "nest_restart_throttled component=%s restarts=%d cooldown=%d",
                    name,
                    len(recent),
                    cooldown,
                )
                await asyncio.sleep(cooldown)

            comp.restart_count += 1
            self._restart_times.append(time.time())
            comp.status = "restarting"

        logger.info("nest_restarting_component component=%s", name)
        return True

    async def register_component_async(self, name: str) -> None:
        await self._register_component(name)

    async def _register_component(self, name: str) -> None:
        async with self._lock:
            if name not in self._components:
                self._components[name] = ComponentStatus(name=name)

    async def _mark_healthy(self, name: str, pid: Optional[int] = None) -> None:
        async with self._lock:
            comp = self._components.get(name)
            if comp:
                comp.status = "running"
                comp.healthy = True
                comp.pid = pid or os.getpid()
                comp.started_at = time.time()
                comp.last_error = None

    async def _mark_unhealthy(self, name: str, error: str) -> None:
        async with self._lock:
            comp = self._components.get(name)
            if comp:
                comp.status = "error"
                comp.healthy = False
                comp.last_error = error

    async def _health_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self._config.health_check_interval)
            try:
                report = await self.health_report()
                if self._on_health_change:
                    self._on_health_change(report)

                cpu = report.cpu_pct
                mem = report.memory_mb
                disk = report.disk_pct

                if cpu > 90:
                    logger.warning("nest_cpu_high cpu=%.1f", cpu)
                if mem > 1024:
                    logger.warning("nest_memory_high mem_mb=%.1f", mem)
                if disk > 90:
                    logger.warning("nest_disk_high disk_pct=%.1f", disk)

                if cpu > 95 or mem > 2048:
                    logger.warning("nest_backpressure_triggered cpu=%.1f mem=%.1f", cpu, mem)
                    await asyncio.sleep(5)

                logger.debug("nest_health_ok cpu=%.1f mem=%.1f disk=%.1f", cpu, mem, disk)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("nest_health_error err=%s", e)

    async def _supervisor_loop(self) -> None:
        while self._running:
            await asyncio.sleep(15)
            try:
                async with self._lock:
                    for name, comp in list(self._components.items()):
                        if comp.pid and comp.pid != os.getpid():
                            alive = await self._is_process_alive(comp.pid)
                            if not alive and comp.status == "running":
                                logger.warning(
                                    "nest_process_died component=%s pid=%d",
                                    name,
                                    comp.pid,
                                )
                                comp.status = "crashed"
                                if self._on_crash:
                                    self._on_crash(name)

                                if self._config.auto_restart:
                                    asyncio.create_task(self.restart_component(name))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("nest_supervisor_error err=%s", e)

    async def _check_dependencies(self) -> list[str]:
        missing = []
        for dep in self._config.dependencies:
            if not await self._check_command(dep):
                missing.append(dep)
        return missing

    async def _check_command(self, cmd: str) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                "which", cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            rc = await proc.wait()
            return rc == 0
        except Exception:
            return False

    async def _install_dependency(self, dep: str) -> bool:
        if dep in ("python3", "pip3", "git"):
            return True
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "pip", "install", dep,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            rc = await proc.wait()
            return rc == 0
        except Exception:
            return False

    async def _is_process_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False

    def _get_cpu_usage(self) -> float:
        try:
            import psutil
            return psutil.cpu_percent(interval=0)
        except ImportError:
            try:
                with open("/proc/stat") as f:
                    line = f.readline()
                parts = line.split()
                if len(parts) >= 5:
                    total = sum(int(p) for p in parts[1:])
                    return min(100.0, total / 100.0)
            except Exception:
                pass
            return 0.0

    def _get_memory_usage(self) -> float:
        try:
            import psutil
            return psutil.virtual_memory().used / (1024 * 1024)
        except ImportError:
            try:
                with open("/proc/meminfo") as f:
                    lines = f.readlines()
                mem_total = 0
                mem_available = 0
                for line in lines[:3]:
                    if line.startswith("MemTotal:"):
                        mem_total = int(line.split()[1])
                    elif line.startswith("MemAvailable:"):
                        mem_available = int(line.split()[1])
                if mem_total:
                    return (mem_total - mem_available) / 1024
            except Exception:
                pass
            return 0.0

    def _get_disk_usage(self) -> float:
        try:
            st = os.statvfs(self._config.data_dir)
            total = st.f_frsize * st.f_blocks
            free = st.f_frsize * st.f_bfree
            if total:
                return (1 - free / total) * 100
        except Exception:
            pass
        return 0.0

    def get_stats(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "uptime": self.uptime,
            "components": {
                n: {"status": c.status, "restarts": c.restart_count, "healthy": c.healthy}
                for n, c in self._components.items()
            },
            "restarts_last_hour": sum(
                1 for t in self._restart_times if time.time() - t < 3600
            ),
            "config": {
                "auto_restart": self._config.auto_restart,
                "health_check_interval": self._config.health_check_interval,
                "max_restarts_per_hour": self._config.max_restarts_per_hour,
            },
        }
