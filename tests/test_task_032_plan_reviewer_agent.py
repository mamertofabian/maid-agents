"""Behavioral tests for Task-032: Plan Reviewer Agent."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from maid_agents.agents.plan_reviewer import PlanReviewer
from maid_agents.claude.cli_wrapper import ClaudeWrapper
from maid_agents.core.orchestrator import MAIDOrchestrator


def test_plan_reviewer_instantiation():
    """Test PlanReviewer can be instantiated."""
    claude = ClaudeWrapper(mock_mode=True)
    reviewer = PlanReviewer(claude)
    assert reviewer is not None
    assert isinstance(reviewer, PlanReviewer)


def test_plan_reviewer_with_dry_run():
    """Test PlanReviewer can be instantiated with dry_run flag."""
    claude = ClaudeWrapper(mock_mode=True)
    reviewer = PlanReviewer(claude, dry_run=True)
    assert reviewer is not None
    assert isinstance(reviewer, PlanReviewer)


def test_review_plan_method_signature():
    """Test review_plan method exists with correct signature."""
    claude = ClaudeWrapper(mock_mode=True)
    reviewer = PlanReviewer(claude)

    result = reviewer.review_plan(
        manifest_path="manifests/task-001-orchestrator-skeleton.manifest.json",
        review_feedback="",
        instructions="",
    )

    assert isinstance(result, dict)
    assert "success" in result or "issues_found" in result


def test_review_plan_returns_expected_structure():
    """Test review_plan returns dict with expected fields."""
    claude = ClaudeWrapper(mock_mode=True)
    reviewer = PlanReviewer(claude)

    result = reviewer.review_plan(
        manifest_path="manifests/task-001-orchestrator-skeleton.manifest.json",
        review_feedback="",
        instructions="",
    )

    # Verify response has expected structure
    assert "success" in result
    assert "issues_found" in result or "error" in result
    assert "improvements" in result or "error" in result
    assert "manifest_data" in result or "error" in result
    assert "test_code" in result or "error" in result


def test_review_plan_handles_nonexistent_manifest():
    """Test review_plan handles missing manifest file gracefully."""
    claude = ClaudeWrapper(mock_mode=True)
    reviewer = PlanReviewer(claude)

    result = reviewer.review_plan(
        manifest_path="nonexistent/manifest.json",
        review_feedback="",
        instructions="",
    )

    assert isinstance(result, dict)
    assert result["success"] is False
    assert "error" in result
    assert result["error"] is not None


def test_review_plan_with_review_feedback():
    """Test review_plan accepts review_feedback parameter."""
    claude = ClaudeWrapper(mock_mode=True)
    reviewer = PlanReviewer(claude)

    result = reviewer.review_plan(
        manifest_path="manifests/task-005-base-agent.manifest.json",
        review_feedback="Goal is too vague",
        instructions="",
    )

    assert isinstance(result, dict)
    assert "success" in result


def test_review_plan_with_instructions():
    """Test review_plan accepts instructions parameter."""
    claude = ClaudeWrapper(mock_mode=True)
    reviewer = PlanReviewer(claude)

    result = reviewer.review_plan(
        manifest_path="manifests/task-005-base-agent.manifest.json",
        review_feedback="",
        instructions="Focus on test coverage",
    )

    assert isinstance(result, dict)
    assert "success" in result


def test_review_plan_with_both_feedback_and_instructions():
    """Test review_plan accepts both review_feedback and instructions."""
    claude = ClaudeWrapper(mock_mode=True)
    reviewer = PlanReviewer(claude)

    result = reviewer.review_plan(
        manifest_path="manifests/task-001-orchestrator-skeleton.manifest.json",
        review_feedback="Tests don't cover edge cases",
        instructions="Ensure comprehensive test coverage",
    )

    assert isinstance(result, dict)
    assert "success" in result


def test_execute_method_inherited_from_base():
    """Test execute method is available from BaseAgent."""
    claude = ClaudeWrapper(mock_mode=True)
    reviewer = PlanReviewer(claude)

    result = reviewer.execute()

    assert isinstance(result, dict)
    assert "status" in result or "agent" in result


def test_orchestrator_run_plan_review_loop_exists():
    """Test run_plan_review_loop method exists in MAIDOrchestrator."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    result = orchestrator.run_plan_review_loop(
        manifest_path="manifests/task-001-orchestrator-skeleton.manifest.json",
        instructions="",
        max_iterations=2,
    )

    assert isinstance(result, dict)
    assert "success" in result or "iterations" in result


def test_orchestrator_run_plan_review_loop_returns_structure():
    """Test run_plan_review_loop returns expected structure."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    result = orchestrator.run_plan_review_loop(
        manifest_path="manifests/task-005-base-agent.manifest.json",
        instructions="Check architectural quality",
        max_iterations=3,
    )

    assert isinstance(result, dict)
    assert "success" in result
    assert "iterations" in result or "error" in result
    assert "issues_found" in result or "error" in result
    assert "improvements" in result or "error" in result


def test_orchestrator_run_plan_review_loop_with_different_iterations():
    """Test run_plan_review_loop accepts different max_iterations values."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    result1 = orchestrator.run_plan_review_loop(
        manifest_path="manifests/task-001-orchestrator-skeleton.manifest.json",
        instructions="Quick review",
        max_iterations=1,
    )

    result2 = orchestrator.run_plan_review_loop(
        manifest_path="manifests/task-001-orchestrator-skeleton.manifest.json",
        instructions="Thorough review",
        max_iterations=5,
    )

    assert isinstance(result1, dict)
    assert isinstance(result2, dict)


def test_orchestrator_run_plan_review_loop_without_instructions():
    """Test run_plan_review_loop works without instructions parameter."""
    orchestrator = MAIDOrchestrator(dry_run=True)

    result = orchestrator.run_plan_review_loop(
        manifest_path="manifests/task-001-orchestrator-skeleton.manifest.json",
        max_iterations=2,
    )

    assert isinstance(result, dict)
    assert "success" in result


def test_plan_reviewer_issues_extraction():
    """Test that review_plan can identify and return issues."""
    claude = ClaudeWrapper(mock_mode=True)
    reviewer = PlanReviewer(claude)

    result = reviewer.review_plan(
        manifest_path="manifests/task-001-orchestrator-skeleton.manifest.json",
        review_feedback="",
        instructions="",
    )

    # Even in mock mode, structure should be present
    assert isinstance(result, dict)
    if result.get("success"):
        assert isinstance(result.get("issues_found", []), list)


def test_plan_reviewer_improvements_extraction():
    """Test that review_plan can identify and return improvements."""
    claude = ClaudeWrapper(mock_mode=True)
    reviewer = PlanReviewer(claude)

    result = reviewer.review_plan(
        manifest_path="manifests/task-001-orchestrator-skeleton.manifest.json",
        review_feedback="",
        instructions="",
    )

    # Even in mock mode, structure should be present
    assert isinstance(result, dict)
    if result.get("success"):
        assert isinstance(result.get("improvements", []), list)


def test_cli_review_plan_command_integration():
    """Test that CLI can invoke the plan review command (integration test)."""
    # This test verifies the CLI command exists and can be called
    # We test this through the orchestrator which the CLI uses
    orchestrator = MAIDOrchestrator(dry_run=True)

    result = orchestrator.run_plan_review_loop(
        manifest_path="manifests/task-001-orchestrator-skeleton.manifest.json",
        instructions="CLI integration test",
        max_iterations=1,
    )

    assert isinstance(result, dict)
    assert "success" in result
