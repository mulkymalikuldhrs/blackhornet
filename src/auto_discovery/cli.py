"""Auto-Discovery Engine CLI — sub-agent 1.8.

Command-line interface for interacting with all Auto-Discovery modules.
Provides commands for scanning, routing, testing, configuration management,
health checks, and usage statistics.

Usage:
    bh discovery scan [--providers] [--data]
    bh discovery status
    bh discovery route <prompt>
    bh discovery test <provider>
    bh discovery config [show|edit]
    bh discovery health
    bh discovery stats
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from typing import Any

import logging

from src.auto_discovery.llm_scanner import LLMScanner
from src.auto_discovery.data_scanner import DataScanner
from src.auto_discovery.router import LLMRouter, RouterConfig
from src.auto_discovery.fallback import FallbackChain
from src.auto_discovery.health import HealthChecker
from src.auto_discovery.config_manager import ConfigManager
from src.auto_discovery.cost_tracker import CostTracker

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.expanduser("~/.bh/data")
_BOX_WIDTH = 58


class AutoDiscoveryCLI:
    """CLI interface for the Auto-Discovery Engine.

    Wires together all sub-modules (LLM scanner, data scanner, router,
    fallback, health checker, config manager, cost tracker) and exposes
    them through an argparse-based command-line interface.

    Usage:
        bh discovery scan [--providers] [--data]
        bh discovery status
        bh discovery route <prompt>
        bh discovery test <provider>
        bh discovery config [show|edit]
        bh discovery health
        bh discovery stats
    """

    def __init__(self) -> None:
        """Initialize all Auto-Discovery sub-modules with default paths."""
        self._data_dir = _DATA_DIR
        os.makedirs(self._data_dir, exist_ok=True)

        self._llm_scanner = LLMScanner(data_dir=self._data_dir)
        self._data_scanner = DataScanner(data_dir=self._data_dir)

        providers_path = os.path.join(self._data_dir, "providers_llm.json")
        self._router = LLMRouter(
            providers_file=providers_path,
            config=RouterConfig(),
        )

        self._fallback = FallbackChain(router=self._router)

        self._health_checker = HealthChecker(
            state_file=os.path.join(self._data_dir, "provider_health.json"),
            providers_file=providers_path,
        )

        self._config_manager = ConfigManager()

        self._cost_tracker = CostTracker(
            state_file=os.path.join(self._data_dir, "cost_tracker.json"),
        )

    # ── Main entry ─────────────────────────────────────────────────────────

    def run(self, args: list[str]) -> None:
        """Parse arguments and dispatch to the appropriate command.

        Args:
            args: Command-line argument list (excluding the program name).
        """
        parser = argparse.ArgumentParser(
            prog="bh discovery",
            description="BlackHornet Auto-Discovery Engine",
        )
        sub = parser.add_subparsers(dest="command", required=True)

        # scan
        scan_parser = sub.add_parser("scan", help="Run discovery scans")
        scan_parser.add_argument(
            "--providers",
            action="store_true",
            help="Scan only LLM providers",
        )
        scan_parser.add_argument(
            "--data",
            action="store_true",
            help="Scan only data sources",
        )

        # status
        sub.add_parser("status", help="Show provider health from saved scans")

        # route
        route_parser = sub.add_parser("route", help="Test routing for a prompt")
        route_parser.add_argument("prompt", type=str, help="Prompt text to classify and route")

        # test
        test_parser = sub.add_parser("test", help="Test a specific provider")
        test_parser.add_argument("provider", type=str, help="Provider name to test")

        # config
        config_parser = sub.add_parser("config", help="Manage configuration")
        config_parser.add_argument(
            "action",
            nargs="?",
            choices=["show", "edit"],
            default="show",
            help="Config action (default: show)",
        )

        # health
        sub.add_parser("health", help="Show health check results")

        # stats
        sub.add_parser("stats", help="Show usage statistics")

        parsed = parser.parse_args(args)

        command_map: dict[str, Any] = {
            "scan": self.cmd_scan,
            "status": self.cmd_status,
            "route": self.cmd_route,
            "test": self.cmd_test,
            "config": self.cmd_config,
            "health": self.cmd_health,
            "stats": self.cmd_stats,
        }

        handler = command_map.get(parsed.command)
        if handler is not None:
            try:
                handler(parsed)
            except KeyboardInterrupt:
                self._print_box_line()
                print("║  Interrupted by user.                              ║")
                self._print_footer()
                sys.exit(130)
            except Exception as exc:
                logger.error("cli_command_failed", command=parsed.command, error=str(exc))
                self._print_box_line()
                print(f"║  Error: {str(exc):<48} ║")
                self._print_footer()
                sys.exit(1)

    # ── Scan commands ──────────────────────────────────────────────────────

    def cmd_scan(self, args: argparse.Namespace) -> None:
        """Run LLM and/or data source scanners.

        When neither ``--providers`` nor ``--data`` is given, both
        scanners are run.

        Args:
            args: Parsed command arguments.
        """
        run_providers = args.providers or (not args.providers and not args.data)
        run_data = args.data or (not args.providers and not args.data)

        if run_providers:
            asyncio.run(self.cmd_scan_providers())
        if run_data:
            asyncio.run(self.cmd_scan_data())

    async def cmd_scan_providers(self) -> None:
        """Scan all known LLM providers and save results."""
        self._print_header("LLM Provider Scan")
        results = await self._llm_scanner.discover_all()
        self._llm_scanner.save(results)

        for p in results:
            if p.is_available:
                self._print_status_line(
                    "\u2705",
                    p.name,
                    f"{p.latency_ms:.0f}ms  {self._truncate(p.models[0] if p.models else '', 32)}",
                )
            else:
                detail = p.error if p.error else "unknown"
                self._print_status_line("\u274c", p.name, detail)
        self._print_footer()

    async def cmd_scan_data(self) -> None:
        """Scan all known data sources and save results."""
        self._print_header("Data Source Scan")
        results = await self._data_scanner.discover_all()
        self._data_scanner.save(results)

        for ds in results:
            if ds.is_available:
                self._print_status_line(
                    "\u2705",
                    ds.name,
                    f"{ds.latency_ms:.0f}ms",
                )
            else:
                detail = ds.error if ds.error else "unknown"
                self._print_status_line("\u274c", ds.name, detail)
        self._print_footer()

    # ── Status command ─────────────────────────────────────────────────────

    def cmd_status(self, args: argparse.Namespace) -> None:
        """Display provider status from previously saved scan results.

        Args:
            args: Parsed command arguments (unused).
        """
        providers = self._llm_scanner.load()
        sources = self._data_scanner.load()

        self._print_header("Provider Status")

        print("║  LLM Providers:                                     ║")
        if not providers:
            print("║  (no scan data — run 'bh discovery scan' first)     ║")
        else:
            for p in providers:
                if p.is_available:
                    self._print_status_line(
                        "\u2705",
                        p.name,
                        f"{p.latency_ms:.0f}ms  {self._truncate(p.models[0] if p.models else '', 30)}",
                    )
                else:
                    detail = p.error if p.error else "unreachable"
                    self._print_status_line("\u274c", p.name, detail)

        print("║  Data Sources:                                       ║")
        if not sources:
            print("║  (no scan data — run 'bh discovery scan' first)     ║")
        else:
            for ds in sources:
                if ds.is_available:
                    self._print_status_line("\u2705", ds.name, f"{ds.latency_ms:.0f}ms")
                else:
                    detail = ds.error if ds.error else "unreachable"
                    self._print_status_line("\u274c", ds.name, detail)

        self._print_footer()

    # ── Route command ─────────────────────────────────────────────────────

    def cmd_route(self, args: argparse.Namespace) -> None:
        """Classify and route a prompt, displaying the routing decision.

        Args:
            args: Parsed command arguments with ``prompt``.
        """
        prompt = args.prompt
        complexity = self._router.classify_complexity(prompt)
        route = self._router.route(prompt)

        self._print_header("Routing Decision")
        print(f"║  Complexity:  {complexity.value:<42} ║")
        print(f"║  Provider:    {route.provider:<42} ║")
        print(f"║  Model:       {self._truncate(route.model, 40):<42} ║")
        print(f"║  Endpoint:    {self._truncate(route.endpoint, 40):<42} ║")
        print(f"║  Est. Cost:   ${route.estimated_cost:.6f}                        ║")
        self._print_footer()

    # ── Test command ──────────────────────────────────────────────────────

    @staticmethod
    def _provider_definitions() -> list[dict[str, Any]]:
        """Return the known LLM provider definitions.

        Mirrors the internal list in :class:`LLMScanner` to avoid tight
        coupling to private module state.

        Returns:
            List of provider definition dicts.
        """
        return [
            {
                "name": "opencode_zen",
                "display": "OpenCode Zen",
                "url": "https://opencode.ai/zen/v1",
                "env": "OPENCODE_ZEN_API_KEY",
                "models": [
                    "mimo-v2.5-free",
                    "deepseek-v4-flash-free",
                    "qwen3.6-plus-free",
                    "minimax-m3-free",
                    "nemotron-3-ultra-free",
                    "north-mini-code-free",
                ],
            },
            {
                "name": "nvidia",
                "display": "NVIDIA NIM",
                "url": "https://integrate.api.nvidia.com/v1",
                "env": "NVIDIA_API_KEY",
                "models": ["meta/llama-3.1-nemotron-70b-instruct", "mistralai/mistral-7b-instruct-v0.3"],
            },
            {
                "name": "groq",
                "display": "Groq",
                "url": "https://api.groq.com/openai/v1",
                "env": "GROQ_API_KEY",
                "models": ["llama-3.1-8b-instant", "mixtral-8x7b-32768"],
            },
            {
                "name": "openrouter",
                "display": "OpenRouter",
                "url": "https://openrouter.ai/api/v1",
                "env": "OPENROUTER_API_KEY",
                "models": ["meta-llama/llama-3.1-8b-instruct"],
            },
            {
                "name": "ollama_cloud",
                "display": "Ollama Cloud",
                "url": "https://ollama.com/v1",
                "env": "OLLAMA_API_KEY",
                "models": ["llama3.1"],
            },
            {
                "name": "glm",
                "display": "GLM (z.ai)",
                "url": "https://api.z.ai/api/paas/v4",
                "env": "GLM_API_KEY",
                "models": ["glm-4"],
            },
        ]

    def cmd_test(self, args: argparse.Namespace) -> None:
        """Test a specific provider by name.

        Runs a scan probe against the named provider.

        Args:
            args: Parsed command arguments with ``provider``.
        """
        name = args.provider
        self._print_header(f"Testing Provider: {name}")

        provider_defs = self._provider_definitions()
        match = next((d for d in provider_defs if d["name"] == name), None)

        if match is None:
            known = ", ".join(d["name"] for d in provider_defs)
            print(f"║  Unknown provider '{name}'. Known: {self._truncate(known, 36)} ║")
            self._print_footer()
            sys.exit(1)

        async def _run_test() -> None:
            self._print_box_line()
            print(f"║  Probing {match['display']}...{' ' * (42 - len(match['display']))} ║")
            results = await self._llm_scanner.discover_all()
            found = next((p for p in results if p.name == name), None)
            if found is None:
                print(f"║  No result returned for '{name}'.{' ' * 32} ║")
                self._print_footer()
                return
            if found.is_available:
                self._print_status_line(
                    "\u2705",
                    found.name,
                    f"{found.latency_ms:.0f}ms  {found.models[0] if found.models else ''}",
                )
            else:
                detail = found.error if found.error else "unreachable"
                self._print_status_line("\u274c", found.name, detail)
            self._print_footer()

        asyncio.run(_run_test())

    # ── Config commands ───────────────────────────────────────────────────

    def cmd_config(self, args: argparse.Namespace) -> None:
        """Manage configuration: show or edit.

        Args:
            args: Parsed command arguments with ``action``.
        """
        if args.action == "edit":
            self.cmd_config_edit()
        else:
            self.cmd_config_show()

    def cmd_config_show(self) -> None:
        """Display the current configuration."""
        config = self._config_manager.load()

        self._print_header("Configuration")

        print(f"║  Data dir:  {self._truncate(config.data_dir, 44):<44} ║")
        print(f"║  Health check interval: {config.health_check_interval_hours}h{' ' * 25} ║")
        print(f"║  LLM Providers ({len(config.llm_providers)}):{' ' * 38} ║")
        for p in config.llm_providers:
            status = "\u2705" if p.enabled else "\u274c"
            models = ", ".join(p.models) if p.models else "none"
            line = f"  {status} {p.name} (priority {p.priority}) [{models}]"
            print(f"║  {self._truncate(line, 52):<52} ║")
        print(f"║  Routing rules ({len(config.routing)}):{' ' * 37} ║")
        for r in config.routing:
            pref = ", ".join(r.preferred_providers) if r.preferred_providers else "none"
            fall = ", ".join(r.fallback_providers) if r.fallback_providers else "none"
            line = f"  {r.complexity}: preferred=[{pref}] fallback=[{fall}]"
            print(f"║  {self._truncate(line, 52):<52} ║")

        config_path = os.path.expanduser(self._config_manager._config_path)
        print(f"║  Config file: {self._truncate(config_path, 42):<42} ║")
        self._print_footer()

    def cmd_config_edit(self) -> None:
        """Open the configuration file in the system editor."""
        config = self._config_manager.load()
        config_dir = os.path.dirname(
            os.path.expanduser(self._config_manager._config_path),
        )
        os.makedirs(config_dir, exist_ok=True)
        self._config_manager.save(config)

        config_path = os.path.expanduser(self._config_manager._config_path)

        editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "nano"))
        try:
            subprocess.check_call([editor, config_path])
            print(f"Configuration saved to: {config_path}")
        except FileNotFoundError:
            print(f"Editor '{editor}' not found. Config file at: {config_path}")
        except subprocess.CalledProcessError as exc:
            print(f"Editor exited with code {exc.returncode}. Config file at: {config_path}")

    # ── Health command ────────────────────────────────────────────────────

    def cmd_health(self, args: argparse.Namespace) -> None:
        """Run health checks on all providers and display results.

        Args:
            args: Parsed command arguments (unused).
        """
        results = self._health_checker.check_all()

        self._print_header("Health Check Results")
        if not results:
            print("║  No providers configured for health checks.          ║")
            self._print_footer()
            return

        for name, hs in results.items():
            if hs.status == "ok":
                icon = "\u2705"
            elif hs.status == "degraded":
                icon = "\u26a0\ufe0f"
            else:
                icon = "\u274c"
            detail = f"{hs.status}  {hs.latency_ms:.0f}ms  {hs.model}"
            self._print_status_line(icon, name, detail)

        self._print_footer()

    # ── Stats command ─────────────────────────────────────────────────────

    def cmd_stats(self, args: argparse.Namespace) -> None:
        """Display usage statistics from the cost tracker.

        Args:
            args: Parsed command arguments (unused).
        """
        all_stats = self._cost_tracker.get_all_stats()
        total_tokens = self._cost_tracker.get_total_tokens()
        total_cost = self._cost_tracker.get_total_estimated_cost()

        self._print_header("Usage Statistics")
        print(f"║  Total tokens:    {total_tokens:<10}                            ║")
        print(f"║  Total est. cost: ${total_cost:<8.6f}                        ║")
        print(f"║  Providers:                                                      ║")

        if not all_stats:
            print("║  (no usage recorded yet)                              ║")
        else:
            for name, s in all_stats.items():
                line = (
                    f"{name}: {s.total_requests} req, "
                    f"{s.total_tokens} tok, "
                    f"{s.average_latency_ms:.0f}ms avg"
                )
                print(f"║  {self._truncate(line, 52):<52} ║")

        self._print_footer()

    # ── Display helpers ───────────────────────────────────────────────────

    @staticmethod
    def _print_header(title: str) -> None:
        """Print the box header with a title line.

        Args:
            title: Title text to display in the header area.
        """
        pad = _BOX_WIDTH - len(title) - 4
        print(f"\n\u2554{'=' * _BOX_WIDTH}\u2557")
        print(f"\u2551  \033[1m{title}\033[0m{' ' * pad}  \u2551")
        print(f"\u2560{'=' * _BOX_WIDTH}\u2563")

    @staticmethod
    def _print_box_line() -> None:
        """Print a separator line within the box."""
        print(f"\u2560{'=' * _BOX_WIDTH}\u2563")

    @staticmethod
    def _print_status_line(icon: str, name: str, detail: str) -> None:
        """Print a single status line within the box.

        Args:
            icon: Status icon (e.g. checkmark, cross).
            name: Item name.
            detail: Additional detail string (includes parenthesised
                latency and model where applicable).
        """
        content = f"{icon} {name}  {detail}"
        padding = _BOX_WIDTH - len(content) - 2
        if padding < 1:
            content = AutoDiscoveryCLI._truncate(content, _BOX_WIDTH - 3)
            padding = 1
        print(f"\u2551  {content}{' ' * padding} \u2551")

    @staticmethod
    def _print_footer() -> None:
        """Print the box footer."""
        print(f"\u255a{'=' * _BOX_WIDTH}\u255d\n")

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        """Truncate text with an ellipsis if it exceeds max_len.

        Args:
            text: String to truncate.
            max_len: Maximum length before truncation (must be >= 4).

        Returns:
            Truncated string with ``...`` appended if necessary.
        """
        if len(text) <= max_len:
            return text
        if max_len < 4:
            return text[:max_len]
        return text[: max_len - 3] + "..."


def main() -> None:
    """Entry point for the Auto-Discovery CLI.

    Creates an :class:`AutoDiscoveryCLI` instance and runs it with
    ``sys.argv[1:]``.
    """
    cli = AutoDiscoveryCLI()
    cli.run(sys.argv[1:])


if __name__ == "__main__":
    main()
