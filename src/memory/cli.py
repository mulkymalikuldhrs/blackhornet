"""Memory System CLI — sub-agent 2.7.

Usage:
    bh memory add <key> <content> [--tags=tag1,tag2]
    bh memory get <key>
    bh memory search <query>
    bh memory list [--recent|--important] [--limit=N]
    bh memory stats
    bh memory consolidate
    bh memory forget
    bh memory archive list
    bh memory archive restore <date>
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

logger = logging.getLogger(__name__)


class MemoryCLI:
    """CLI interface for the BlackHornet Memory System."""

    def __init__(self, data_dir: str = "~/.bh/memory"):
        self._data_dir = os.path.expanduser(data_dir)
        os.makedirs(self._data_dir, exist_ok=True)

        from src.memory.short_term import ShortTermMemory
        from src.memory.long_term import LongTermMemory
        from src.memory.semantic import SemanticMemory
        from src.memory.episodic import EpisodicMemory
        from src.memory.consolidation import MemoryConsolidator
        from src.memory.forgetting import ForgettingMechanism

        self.stm = ShortTermMemory()
        self.ltm = LongTermMemory(db_path=os.path.join(self._data_dir, "long_term.db"))
        self.sem = SemanticMemory(db_path=os.path.join(self._data_dir, "semantic.db"))
        self.epi = EpisodicMemory(db_path=os.path.join(self._data_dir, "episodic.db"))
        self.consolidator = MemoryConsolidator(self.stm, self.ltm, self.sem, self.epi)
        self.forgetting = ForgettingMechanism(
            self.ltm, self.sem, self.epi,
            archive_dir=os.path.join(self._data_dir, "archive"),
        )

    def run(self, args: list[str]) -> None:
        parser = argparse.ArgumentParser(description="BlackHornet Memory CLI")
        sub = parser.add_subparsers(dest="command")

        p_add = sub.add_parser("add", help="Add entry to long-term memory")
        p_add.add_argument("key")
        p_add.add_argument("content")
        p_add.add_argument("--tags", default="")
        p_add.add_argument("--importance", type=float, default=0.5)

        p_get = sub.add_parser("get", help="Get entry by key")
        p_get.add_argument("key")

        p_search = sub.add_parser("search", help="Search memory")
        p_search.add_argument("query")
        p_search.add_argument("--limit", type=int, default=20)
        p_search.add_argument("--tier", choices=["stm", "ltm", "sem", "epi", "all"], default="all")

        p_list = sub.add_parser("list", help="List entries")
        p_list.add_argument("--recent", action="store_true")
        p_list.add_argument("--important", action="store_true")
        p_list.add_argument("--limit", type=int, default=20)

        sub.add_parser("stats", help="Show memory statistics")

        sub.add_parser("consolidate", help="Run memory consolidation")

        p_forget = sub.add_parser("forget", help="Run forgetting cycle")

        p_archive = sub.add_parser("archive", help="Archive operations")
        p_archive.add_argument("action", choices=["list", "restore"])
        p_archive.add_argument("date", nargs="?", default="")

        parsed = parser.parse_args(args)

        if not parsed.command:
            parser.print_help()
            return

        handlers = {
            "add": self._cmd_add,
            "get": self._cmd_get,
            "search": self._cmd_search,
            "list": self._cmd_list,
            "stats": self._cmd_stats,
            "consolidate": self._cmd_consolidate,
            "forget": self._cmd_forget,
            "archive": self._cmd_archive,
        }

        handler = handlers.get(parsed.command)
        if handler:
            handler(parsed)

    def _cmd_add(self, args) -> None:
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        entry_id = self.ltm.add(args.key, args.content, tags=tags, importance=args.importance)
        print(f"✅ Added to LTM: id={entry_id}, key='{args.key}'")

    def _cmd_get(self, args) -> None:
        entry = self.ltm.get(args.key)
        if entry:
            print(f"Key:       {entry.key}")
            print(f"Content:   {entry.content[:200]}..." if len(entry.content) > 200 else f"Content:   {entry.content}")
            print(f"Tags:      {', '.join(entry.tags)}")
            print(f"Importance: {entry.importance}")
            print(f"Accessed:  {entry.access_count} times")
        else:
            # Try STM
            stm_entry = self.stm.get(args.key)
            if stm_entry:
                print(f"[STM] {stm_entry.content[:200]}")
            else:
                print(f"❌ Key '{args.key}' not found")

    def _cmd_search(self, args) -> None:
        results = []
        if args.tier in ("all", "ltm"):
            results.extend(self.ltm.search(args.query, limit=args.limit))
        if args.tier in ("all", "sem"):
            results.extend(self.sem.search(args.query, limit=args.limit))

        if results:
            print(f"Found {len(results)} results for '{args.query}':")
            for i, r in enumerate(results[:args.limit], 1):
                content = r.content[:120] if hasattr(r, 'content') else str(r)[:120]
                print(f"  {i}. {content}...")
        else:
            print(f"No results for '{args.query}'")

    def _cmd_list(self, args) -> None:
        if args.recent:
            entries = self.ltm.list_recent(limit=args.limit)
            print(f"Recent LTM entries ({len(entries)}):")
            for e in entries:
                print(f"  [{e.key}] {e.content[:80]}... (imp={e.importance})")
        elif args.important:
            entries = self.ltm.list_by_importance(min_importance=0.7, limit=args.limit)
            print(f"Important LTM entries ({len(entries)}):")
            for e in entries:
                print(f"  [{e.key}] {e.content[:80]}... (imp={e.importance})")
        else:
            entries = self.ltm.list_recent(limit=args.limit)
            print(f"LTM entries ({len(entries)}):")
            for e in entries:
                print(f"  [{e.key}] {e.content[:80]}...")

    def _cmd_stats(self, args) -> None:
        stm_stats = self.stm.stats()
        ltm_stats = self.ltm.stats()
        sem_stats = self.sem.stats()
        epi_stats = self.epi.stats()

        box_width = 50
        print("╔" + "═" * (box_width - 2) + "╗")
        print("║  BlackHornet Memory System Stats" + " " * 15 + "║")
        print("╠" + "═" * (box_width - 2) + "╣")
        print(f"║  STM:       {stm_stats.get('entry_count', 0):>5} entries, TTL={stm_stats.get('default_ttl', 3600)}s")
        print(f"║  LTM:       {ltm_stats.get('total_entries', 0):>5} entries, FTS5 ready")
        print(f"║  Semantic:  {sem_stats.get('total_entries', 0):>5} entries, n-gram ready")
        print(f"║  Episodic:  {epi_stats.get('total_entries', 0):>5} episodes")
        print("╚" + "═" * (box_width - 2) + "╝")

    def _cmd_consolidate(self, args) -> None:
        print("Running consolidation...")
        report = self.consolidator.run_consolidation()
        print(f"✅ Consolidation complete:")
        print(f"   STM→LTM:     {report.stm_to_ltm}")
        print(f"   LTM→Sem:     {report.ltm_to_semantic}")
        print(f"   Dedup:       {report.deduplicated}")
        print(f"   Archived:    {report.archived}")
        print(f"   Duration:    {report.duration_ms:.1f}ms")

    def _cmd_forget(self, args) -> None:
        print("Running forgetting cycle...")
        report = self.forgetting.run_forgetting()
        print(f"✅ Forgetting complete:")
        print(f"   Archived:    {report.archived}")
        print(f"   Deleted:     {report.deleted}")
        print(f"   Duration:    {report.duration_ms:.1f}ms")

    def _cmd_archive(self, args) -> None:
        if args.action == "list":
            archives = self.forgetting.list_archives()
            if archives:
                print(f"Available archives ({len(archives)}):")
                for a in archives:
                    print(f"  - {a}")
            else:
                print("No archives found")
        elif args.action == "restore":
            if not args.date:
                print("❌ Usage: archive restore <date>")
                return
            count = self.forgetting.restore_archive(args.date)
            print(f"✅ Restored {count} entries from archive '{args.date}'")


def main() -> None:
    cli = MemoryCLI()
    cli.run(sys.argv[1:])
    sys.exit(0)
