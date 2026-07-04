"""Tests for Lord Omega founding pillars embedded in BlackHornet."""

from __future__ import annotations

import os
import sys
import tempfile
from unittest.mock import patch

import pytest

from src.omega.constitution import Constitution
from src.omega.scs import SelfConfidenceSystem
from src.omega.council import Council
from src.omega.predictor import PredictiveSuperconsciousness
from src.omega.brain import SecondBrain
from src.omega.genome import GenomeEngine
from src.omega.score import ProjectScorer
from src.omega.sync import EcosystemSync


class TestConstitution:
    def test_validate_returns_dict(self):
        c = Constitution()
        result = c.validate()
        assert "constitution_score" in result
        assert "root_docs" in result
        assert "core_docs" in result

    def test_check_doc(self):
        c = Constitution()
        check = c.check_doc("README.md")
        assert check.name == "README.md"

    def test_root_docs_list(self):
        assert len(Constitution.REQUIRED_ROOT) == 7
        assert "CLAUDE.md" in Constitution.REQUIRED_ROOT
        assert "MASTER_SYSTEM_PROMPT.md" in Constitution.REQUIRED_ROOT

    def test_core_docs_list(self):
        assert len(Constitution.REQUIRED_CORE_DOCS) == 22
        assert "VISION" in Constitution.REQUIRED_CORE_DOCS
        assert "ARCHITECTURE" in Constitution.REQUIRED_CORE_DOCS


class TestSCS:
    def test_record_action(self):
        scs = SelfConfidenceSystem()
        entry = scs.record_action("test action", 0.85, 3)
        assert entry.confidence == 0.85
        assert entry.evidence_sources == 3
        assert entry.outcome is None

    def test_record_outcome(self):
        scs = SelfConfidenceSystem()
        entry = scs.record_action("test outcome", 0.9, 2)
        scs.record_outcome(entry, True)
        assert entry.outcome is True
        assert entry.calibrated is True

    def test_calculate_score_returns_dict(self):
        scs = SelfConfidenceSystem()
        score = scs.calculate_score()
        assert "scs" in score
        assert "prediction_accuracy" in score

    def test_check_overclaim(self):
        scs = SelfConfidenceSystem()
        warning = scs.check_overclaim(0.95, 1)
        assert warning is not None
        assert "OVERCLAIM" in warning
        assert scs.check_overclaim(0.7, 3) is None

    def test_action_confidence_below_threshold(self):
        scs = SelfConfidenceSystem()
        result = scs.action_confidence("risky action", complexity="high")
        assert "verdict" in result
        assert "action_confidence" in result

    def test_status_returns_dict(self):
        scs = SelfConfidenceSystem()
        status = scs.status()
        assert "scs" in status
        assert "message" in status

    def test_prediction_lifecycle(self):
        scs = SelfConfidenceSystem()
        pred = scs.record_prediction("will work", 0.8, "past data supports")
        assert pred.confidence == 0.8
        scs.resolve_prediction(pred, True)
        assert pred.outcome is True


class TestCouncil:
    def test_convene_default_all_personas(self):
        council = Council()
        result = council.convene("Test decision")
        assert len(result.votes) == 15
        assert result.timestamp > 0

    def test_convene_subset(self):
        council = Council()
        result = council.convene("Filtered", personas=["CTO", "CEO", "Skeptic"])
        assert len(result.votes) == 3

    def test_convene_returns_synthesis(self):
        council = Council()
        result = council.convene("Important decision")
        assert result.synthesis
        assert "Council synthesis" in result.synthesis

    def test_consensus_check(self):
        council = Council()
        result = council.convene("Consensus test")
        assert isinstance(result.consensus, bool)

    def test_recommended_action(self):
        council = Council()
        result = council.convene("Recommendation test")
        assert result.recommended_action
        assert "Recommended by" in result.recommended_action

    def test_history(self):
        council = Council()
        council.convene("First")
        council.convene("Second")
        assert len(council.history()) == 2

    def test_minority_report(self):
        council = Council()
        result = council.convene("Minority test")
        assert isinstance(result.minority_report, str)

    def test_persona_list(self):
        assert len(Council.PERSONAS) == 15
        assert "The Void" in Council.PERSONAS
        assert Council.PERSONAS["Mulky"].weight == 1.0
        assert Council.PERSONAS["Quality Dictator"].weight == 1.15


class TestPredictor:
    def test_branch_returns_prediction(self):
        p = PredictiveSuperconsciousness()
        pred = p.branch("Test action")
        assert len(pred.branches) >= 3
        assert pred.optimal_path
        assert pred.timestamp > 0

    def test_calibrate(self):
        p = PredictiveSuperconsciousness()
        pred = p.branch("Calibrate test")
        p.calibrate(pred, True)
        assert pred.outcome is True

    def test_calibration_report(self):
        p = PredictiveSuperconsciousness()
        result = p.calibration_report()
        assert "total_predictions" in result
        assert "accuracy" in result

    def test_predict_returns_dict(self):
        p = PredictiveSuperconsciousness()
        result = p.predict("Should we proceed?")
        assert "branches" in result
        assert "optimal_path" in result
        assert "confidence" in result


class TestSecondBrain:
    def test_auto_capture(self):
        brain = SecondBrain()
        entry = brain.auto_capture("code", "def test(): pass", project="test")
        assert entry.entry_type == "code"
        assert entry.project == "test"

    def test_recall_recent(self):
        brain = SecondBrain()
        brain.auto_capture("insight", "test insight")
        results = brain.recall_recent(limit=5)
        assert len(results) >= 1
        assert any(r["type"] == "insight" for r in results)

    def test_recall_search(self):
        brain = SecondBrain()
        brain.auto_capture("warning", "specific search term xyz123")
        results = brain.recall_search("xyz123")
        assert len(results) >= 1

    def test_scan_ecosystem(self):
        brain = SecondBrain()
        result = brain.scan_ecosystem()
        assert "entries_count" in result
        assert "types" in result
        assert "projects" in result

    def test_wake_up(self):
        brain = SecondBrain()
        result = brain.wake_up()
        assert "timestamp" in result
        assert "total_entries" in result

    def test_log_session(self):
        brain = SecondBrain()
        brain.log_session("test session", files_changed=["a.py"], decisions=["use X"])
        assert True


class TestGenome:
    def test_initial_genome(self):
        g = GenomeEngine()
        assert g.genome.fitness >= 0
        assert g.genome.version

    def test_evaluate_fitness(self):
        g = GenomeEngine()
        fitness = g.evaluate_fitness(0.85, 0.75, 80)
        assert 0 <= fitness <= 1

    def test_mutate_not_needed(self):
        g = GenomeEngine()
        g.genome.fitness = 0.95
        result = g.mutate()
        assert result is None

    def test_status(self):
        g = GenomeEngine()
        status = g.status()
        assert "version" in status
        assert "fitness" in status
        assert "needs_mutation" in status


class TestScorer:
    def test_score_project(self):
        s = ProjectScorer()
        p = s.score("test-project", constitution=20, quality=40, operations=20)
        assert p.total == 80
        assert p.constitution == 20

    def test_priority_queue(self):
        s = ProjectScorer()
        s.score("project-a", constitution=10, quality=20, operations=10)
        s.score("project-b", constitution=25, quality=50, operations=25)
        queue = s.priority_queue()
        assert len(queue) >= 1

    def test_current(self):
        s = ProjectScorer()
        current = s.current()
        assert "project_count" in current
        assert "scores" in current

    def test_average(self):
        s = ProjectScorer()
        avg = s.average()
        assert isinstance(avg, float)

    def test_get_project(self):
        s = ProjectScorer()
        s.score("test-get", constitution=10, quality=10, operations=10)
        p = s.get("test-get")
        assert p is not None
        assert p.total == 30


class TestSync:
    def test_status(self):
        sync = EcosystemSync()
        status = sync.status()
        assert "last_sync" in status
        assert "hermes_nous_dir_exists" in status


class TestOmegaEngine:
    def test_boot(self):
        from src.omega import OmegaEngine
        engine = OmegaEngine()
        report = engine.boot()
        assert "constitution" in report
        assert "brain_recall" in report
        assert "scores" in report

    def test_stats(self):
        from src.omega import OmegaEngine
        engine = OmegaEngine()
        stats = engine.stats()
        assert "booted" in stats
        assert "running" in stats
