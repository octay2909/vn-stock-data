"""Pipeline state management with atomic writes and checkpoint/resume.

Handles V1 (step-number keyed) to V2 (agent-name keyed) state migration,
plus new state management utilities for the ai_analyst package.

All migration functions are pure (no file I/O) for testability.
"""

from __future__ import annotations

import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Schema version detection & migration
# ---------------------------------------------------------------------------

def detect_schema_version(state: dict) -> int:
    """Return the schema version of a pipeline state dict.

    Returns 2 if the state has ``schema_version >= 2``, otherwise 1.

    Args:
        state: Pipeline state dictionary.

    Returns:
        int: Schema version number (1 or 2).
    """
    version = state.get("schema_version")
    if isinstance(version, int) and version >= 2:
        return 2
    return 1


def is_v1_state(state: dict) -> bool:
    """Return True if *state* uses the V1 (step-number keyed) format.

    Args:
        state: Pipeline state dictionary.

    Returns:
        bool: True if V1 format.
    """
    return detect_schema_version(state) < 2


def migrate_v1_to_v2(state: dict, dataset: str = "unknown") -> dict:
    """Migrate a V1 pipeline state dict to V2 format.

    This is a pure function — it does not perform any file I/O.

    Args:
        state: A V1 pipeline state dict (step-number keyed).
        dataset: Active dataset name. Falls back to "unknown".

    Returns:
        dict: A V2 pipeline state dict (agent-name keyed).
    """
    if not is_v1_state(state):
        return state

    pipeline_id = state.get("pipeline_id", "")
    question = state.get("question", "")
    v1_steps: dict = state.get("steps", {})

    agents: Dict[str, dict] = {}
    for _step_num, step_data in v1_steps.items():
        agent_name = step_data.get("agent")
        if not agent_name:
            continue

        agent_entry: dict = {}

        if "status" in step_data:
            agent_entry["status"] = step_data["status"]
        if "started_at" in step_data:
            agent_entry["started_at"] = step_data["started_at"]
        if "completed_at" in step_data:
            agent_entry["completed_at"] = step_data["completed_at"]

        output_files = step_data.get("output_files")
        if isinstance(output_files, list) and output_files:
            agent_entry["output_file"] = output_files[0]
        elif isinstance(output_files, str):
            agent_entry["output_file"] = output_files

        if "error" in step_data:
            agent_entry["error"] = step_data["error"]

        agents[agent_name] = agent_entry

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "schema_version": 2,
        "run_id": _build_run_id(pipeline_id, dataset, question),
        "dataset": dataset,
        "question": question,
        "started_at": pipeline_id if pipeline_id else now_iso,
        "updated_at": now_iso,
        "status": _derive_pipeline_status(v1_steps),
        "agents": agents,
    }


# ---------------------------------------------------------------------------
# State management (new)
# ---------------------------------------------------------------------------

def create_initial_state(
    question: str,
    dataset: str,
    agents: List[str],
) -> dict:
    """Create a fresh V2 pipeline state for a new run.

    Args:
        question: The business question being analyzed.
        dataset: Active dataset name.
        agents: Ordered list of agent names in the pipeline.

    Returns:
        dict: A V2 pipeline state dict with all agents set to "pending".
    """
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id = _build_run_id(now_iso, dataset, question)

    agent_entries: Dict[str, dict] = {}
    for agent_name in agents:
        agent_entries[agent_name] = {"status": "pending"}

    return {
        "schema_version": 2,
        "run_id": run_id,
        "dataset": dataset,
        "question": question,
        "started_at": now_iso,
        "updated_at": now_iso,
        "status": "running",
        "agents": agent_entries,
    }


def update_agent_status(
    state: dict,
    agent_name: str,
    status: str,
    output_file: Optional[str] = None,
    error: Optional[str] = None,
) -> dict:
    """Update the status of an agent in the pipeline state.

    Args:
        state: Current pipeline state dict.
        agent_name: Name of the agent to update.
        status: New status ("running", "complete", "failed", "skipped").
        output_file: Optional path to the agent's output file.
        error: Optional error message if status is "failed".

    Returns:
        dict: Updated pipeline state (mutated in place and returned).
    """
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if agent_name not in state.get("agents", {}):
        state.setdefault("agents", {})[agent_name] = {}

    agent = state["agents"][agent_name]
    agent["status"] = status

    if status == "running":
        agent["started_at"] = now_iso
    elif status in ("complete", "failed", "skipped"):
        agent["completed_at"] = now_iso

    if output_file is not None:
        agent["output_file"] = output_file
    if error is not None:
        agent["error"] = error

    state["updated_at"] = now_iso
    state["status"] = _derive_pipeline_status(state.get("agents", {}))

    return state


def get_next_agent(state: dict) -> Optional[str]:
    """Return the name of the next pending agent, or None if all done.

    Args:
        state: Current pipeline state dict.

    Returns:
        str or None: Name of the next agent to run, or None.
    """
    for agent_name, agent_data in state.get("agents", {}).items():
        if agent_data.get("status") == "pending":
            return agent_name
    return None


def is_pipeline_complete(state: dict) -> bool:
    """Check if all agents have finished (complete, failed, or skipped).

    Args:
        state: Current pipeline state dict.

    Returns:
        bool: True if the pipeline has no more work to do.
    """
    terminal = {"complete", "failed", "skipped", "degraded"}
    agents = state.get("agents", {})
    if not agents:
        return True
    return all(
        a.get("status", "pending") in terminal for a in agents.values()
    )


# ---------------------------------------------------------------------------
# Atomic file I/O
# ---------------------------------------------------------------------------

def save_state(state: dict, path: str) -> None:
    """Atomically write the pipeline state to a JSON file.

    Uses write-to-temp + rename to avoid partial writes on crash.

    Args:
        state: Pipeline state dict.
        path: Destination file path.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=str(target.parent), suffix=".tmp", prefix=".state_"
    )
    try:
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False, default=str)
        Path(tmp_path).replace(target)
    except Exception:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
        raise


def load_state(path: str) -> Optional[dict]:
    """Load a pipeline state from a JSON file.

    Args:
        path: File path to load.

    Returns:
        dict or None: Parsed state dict, or None if file doesn't exist.
    """
    target = Path(path)
    if not target.is_file():
        return None

    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Checkpoint / resume
# ---------------------------------------------------------------------------

def create_checkpoint(state: dict, checkpoint_dir: str) -> str:
    """Save a timestamped checkpoint of the current state.

    Args:
        state: Current pipeline state dict.
        checkpoint_dir: Directory to store checkpoints.

    Returns:
        str: Path to the created checkpoint file.
    """
    cp_dir = Path(checkpoint_dir)
    cp_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_id = state.get("run_id", "unknown")
    filename = f"checkpoint_{run_id}_{ts}.json"
    cp_path = cp_dir / filename

    save_state(state, str(cp_path))
    return str(cp_path)


def resume_from_checkpoint(checkpoint_path: str) -> Optional[dict]:
    """Load a pipeline state from a checkpoint file.

    Resets any "running" agents back to "pending" so they can be re-run.

    Args:
        checkpoint_path: Path to a checkpoint JSON file.

    Returns:
        dict or None: The resumed state, or None if file doesn't exist.
    """
    state = load_state(checkpoint_path)
    if state is None:
        return None

    for agent_data in state.get("agents", {}).values():
        if agent_data.get("status") in ("running", "in_progress"):
            agent_data["status"] = "pending"
            agent_data.pop("started_at", None)

    state["updated_at"] = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    state["status"] = _derive_pipeline_status(state.get("agents", {}))

    return state


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Convert a human-readable string to a URL-friendly slug.

    Args:
        text: Input text.

    Returns:
        str: Slugified string, max 60 chars.
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:60]


def _extract_date(pipeline_id: str) -> str:
    """Extract a YYYY-MM-DD date from an ISO datetime string.

    Falls back to today's date if parsing fails.
    """
    try:
        dt = datetime.fromisoformat(pipeline_id.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _build_run_id(pipeline_id: str, dataset: str, question: str) -> str:
    """Build a V2 run_id from V1 fields.

    Format: {date}_{dataset}_{question_slug}
    """
    date_str = _extract_date(pipeline_id)
    slug = _slugify(question) if question else "unknown-question"
    return f"{date_str}_{dataset}_{slug}"


def _derive_pipeline_status(agents: dict) -> str:
    """Derive overall pipeline status from agent statuses.

    - If any agent is "failed" -> "failed"
    - If any agent is "running"/"in_progress" -> "paused"
    - If all agents are terminal -> "completed"
    - Otherwise -> "running"
    """
    statuses = set()
    for agent_data in agents.values():
        if isinstance(agent_data, dict):
            statuses.add(agent_data.get("status", "pending"))
        else:
            statuses.add(str(agent_data))

    if "failed" in statuses:
        return "failed"
    if "running" in statuses or "in_progress" in statuses:
        return "paused"

    terminal = {"complete", "skipped", "degraded"}
    if statuses and statuses <= terminal:
        return "completed"

    return "running"
