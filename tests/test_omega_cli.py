"""Tests for BlackHornet CLI."""

from __future__ import annotations

from src.omega.cli import build_parser


class TestCLIParser:
    def test_start_command(self):
        parser = build_parser()
        args = parser.parse_args(["start"])
        assert args.command == "start"

    def test_start_with_loop(self):
        parser = build_parser()
        args = parser.parse_args(["start", "--loop", "3"])
        assert args.command == "start"
        assert args.loop == 3

    def test_loop_command(self):
        parser = build_parser()
        args = parser.parse_args(["loop"])
        assert args.command == "loop"

    def test_status_command(self):
        parser = build_parser()
        args = parser.parse_args(["status"])
        assert args.command == "status"

    def test_score_command(self):
        parser = build_parser()
        args = parser.parse_args(["score"])
        assert args.command == "score"

    def test_sync_command(self):
        parser = build_parser()
        args = parser.parse_args(["sync"])
        assert args.command == "sync"
