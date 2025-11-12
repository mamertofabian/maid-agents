"""Behavioral tests for Task-018: Refactoring and Refinement Loops."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from maid_agents.core.orchestrator import MAIDOrchestrator


def test_orchestrator_run_refactoring_loop_exists():
    """Test run_refactoring_loop method exists in MAIDOrchestrator."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    result = orchestrator.run_refactoring_loop(
        manifest_path="maid_agents/manifests/task-001-orchestrator-skeleton.manifest.json",
        max_iterations=2,
    )

    assert isinstance(result, dict)
    assert "success" in result or "iterations" in result


def test_orchestrator_run_refactoring_loop_returns_structure():
    """Test run_refactoring_loop returns expected structure."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    result = orchestrator.run_refactoring_loop(
        manifest_path="maid_agents/manifests/task-005-base-agent.manifest.json",
        max_iterations=3,
    )

    assert isinstance(result, dict)
    assert "success" in result
    assert "error" in result or "iterations" in result


def test_orchestrator_run_refactoring_loop_with_different_iterations():
    """Test run_refactoring_loop accepts different max_iterations values."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    result1 = orchestrator.run_refactoring_loop(
        manifest_path="maid_agents/manifests/task-001-orchestrator-skeleton.manifest.json",
        max_iterations=1,
    )

    result2 = orchestrator.run_refactoring_loop(
        manifest_path="maid_agents/manifests/task-001-orchestrator-skeleton.manifest.json",
        max_iterations=5,
    )

    assert isinstance(result1, dict)
    assert isinstance(result2, dict)


def test_orchestrator_run_refinement_loop_exists():
    """Test run_refinement_loop method exists in MAIDOrchestrator."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    result = orchestrator.run_refinement_loop(
        manifest_path="maid_agents/manifests/task-001-orchestrator-skeleton.manifest.json",
        refinement_goal="Add more comprehensive tests",
        max_iterations=2,
    )

    assert isinstance(result, dict)
    assert "success" in result or "iterations" in result


def test_orchestrator_run_refinement_loop_returns_structure():
    """Test run_refinement_loop returns expected structure."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    result = orchestrator.run_refinement_loop(
        manifest_path="maid_agents/manifests/task-005-base-agent.manifest.json",
        refinement_goal="Improve test quality",
        max_iterations=3,
    )

    assert isinstance(result, dict)
    assert "success" in result
    assert "error" in result or "iterations" in result


def test_orchestrator_run_refinement_loop_with_different_iterations():
    """Test run_refinement_loop accepts different max_iterations values."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    result1 = orchestrator.run_refinement_loop(
        manifest_path="maid_agents/manifests/task-001-orchestrator-skeleton.manifest.json",
        refinement_goal="Test goal 1",
        max_iterations=1,
    )

    result2 = orchestrator.run_refinement_loop(
        manifest_path="maid_agents/manifests/task-001-orchestrator-skeleton.manifest.json",
        refinement_goal="Test goal 2",
        max_iterations=5,
    )

    assert isinstance(result1, dict)
    assert isinstance(result2, dict)


def test_orchestrator_run_refactoring_loop_handles_nonexistent_manifest():
    """Test run_refactoring_loop handles missing manifest file gracefully."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    result = orchestrator.run_refactoring_loop(
        manifest_path="nonexistent/manifest.json",
        max_iterations=2,
    )

    assert isinstance(result, dict)
    assert "success" in result or "error" in result


def test_orchestrator_run_refinement_loop_handles_nonexistent_manifest():
    """Test run_refinement_loop handles missing manifest file gracefully."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    result = orchestrator.run_refinement_loop(
        manifest_path="nonexistent/manifest.json",
        refinement_goal="Test goal",
        max_iterations=2,
    )

    assert isinstance(result, dict)
    assert "success" in result or "error" in result
