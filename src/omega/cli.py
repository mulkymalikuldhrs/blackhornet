"""BlackHornet CLI — start, stop, status, loop, score, sync."""

from __future__ import annotations

import argparse
import sys
import time


def cmd_start(args: argparse.Namespace) -> None:
    from src.omega import OmegaEngine

    engine = OmegaEngine()
    report = engine.boot()
    engine.start()
    print(f"OmegaEngine booted. SCS: {report.get('scs', {}).get('scs', 'N/A')}")
    if args.loop:
        for i in range(args.loop):
            rep = engine.main_loop()
            print(f"Loop #{rep['loop']}: {len(rep.get('agent_cycle', {}).get('tasks', []))} tasks planned")
            time.sleep(0.1)
    engine.stop()


def cmd_loop(args: argparse.Namespace) -> None:
    from src.omega import OmegaEngine

    engine = OmegaEngine()
    engine.boot()
    report = engine.main_loop()
    print(f"Loop #{report['loop']} completed")
    ac = report.get("agent_cycle", {})
    if ac:
        print(f"  Objective: {ac.get('objective', 'N/A')}")
        print(f"  Tasks planned: {ac.get('tasks_planned', 0)}")
        print(f"  Results: {len(ac.get('execution_results', []))} executions")
    print(f"  Priority queue: {len(report.get('priority', []))} items")


def cmd_status(args: argparse.Namespace) -> None:
    from src.omega import OmegaEngine
    from src.omega.scs import SelfConfidenceSystem
    from src.omega.score import ProjectScorer
    from src.omega.council import Council

    engine = OmegaEngine()
    engine.start()
    stats = engine.stats()
    scs = SelfConfidenceSystem().status()
    scorer = ProjectScorer()
    council = Council()

    print(f"OmegaEngine v5.0")
    print(f"  Running: {stats['running']}")
    print(f"  Loops: {stats['loop_count']}")
    print(f"  Uptime: {stats['uptime_seconds']:.0f}s")
    print(f"SCS: {scs['scs']}% — {scs['message']}")
    print(f"Projects scored: {scorer.current().get('project_count', 0)}")
    print(f"Council sessions: {len(council.history())}")
    engine.stop()


def cmd_score(args: argparse.Namespace) -> None:
    from src.omega.score import ProjectScorer

    scorer = ProjectScorer()
    info = scorer.current()
    print(f"Projects: {info['project_count']}")
    for name, s in info.get("scores", {}).items():
        print(f"  {name}: {s['total']}/100 (C:{s['constitution']} Q:{s['quality']} O:{s['operations']})")
    pq = info.get("worst", [])
    if pq:
        print("Priority queue (worst first):")
        for p in pq[:5]:
            print(f"  {p['name']}: priority {p['priority']}, gaps C:{p['gap_constitution']} Q:{p['gap_quality']} O:{p['gap_operations']}")


def cmd_sync(args: argparse.Namespace) -> None:
    from src.omega.sync import EcosystemSync

    sync = EcosystemSync()
    result = sync.run()
    print(f"Sync at {result['timestamp']}")
    for action in result.get("actions", []):
        if "error" in action:
            print(f"  {action['type']}: ERROR — {action['error']}")
        else:
            print(f"  {action['type']}: OK")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bh", description="BlackHornet Ω — Autonomous AGI Engine")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="Boot and start the OmegaEngine")
    p_start.add_argument("--loop", type=int, default=0, help="Run N main loop iterations after boot")

    sub.add_parser("loop", help="Run a single main loop iteration")
    sub.add_parser("status", help="Show engine status")
    sub.add_parser("score", help="Show project scores")
    sub.add_parser("sync", help="Run ecosystem sync pipeline")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    commands = {
        "start": cmd_start,
        "loop": cmd_loop,
        "status": cmd_status,
        "score": cmd_score,
        "sync": cmd_sync,
    }

    commands[args.command](args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
