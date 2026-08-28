"""Parallel skill execution engine for AI Analyst.

Runs multiple model training skills concurrently using ThreadPoolExecutor.
Used by the predictive-orchestrator agent to train models in parallel
(e.g., seasonal_naive, prophet, sarima, lgbm_ts simultaneously).

Public API:
    run_parallel()       - Execute multiple skill calls in parallel
    run_parallel_funcs() - Execute arbitrary callables in parallel
    format_results()     - Format parallel execution results for reporting

Usage:
    results, errors = run_parallel(SKILL_CALLS, max_workers=3)
    print(format_results(results, errors))
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Skill call definitions (example — override at runtime)
# ---------------------------------------------------------------------------

DEFAULT_SKILL_CALLS: dict[str, dict[str, str]] = {
    "seasonal_naive": {"skill": "forecast-train", "model_type": "seasonal_naive"},
    "prophet": {"skill": "forecast-train", "model_type": "prophet"},
    "sarima": {"skill": "forecast-train", "model_type": "sarima"},
    "lgbm_ts": {"skill": "forecast-train", "model_type": "lgbm_ts"},
}


# ---------------------------------------------------------------------------
# Core parallel execution
# ---------------------------------------------------------------------------

def _invoke_skill(skill: str, params: dict[str, Any], timeout: float = 600.0) -> dict[str, Any]:
    """Invoke a Claude Code skill via subprocess.

    Parameters
    ----------
    skill : str
        Skill name (e.g., ``"forecast-train"``).
    params : dict
        Parameters to pass to the skill.
    timeout : float
        Per-subprocess timeout in seconds. Defaults to 600. Override via
        ``PIPELINE_SKILL_TIMEOUT`` env var or ``run_parallel(timeout=...)``.

    Returns
    -------
    dict
        Result dictionary with ``status``, ``output``, and ``elapsed``.
    """
    timeout = float(os.environ.get("PIPELINE_SKILL_TIMEOUT", timeout))

    cmd = [
        sys.executable, "-m", "claude_code",
        "--skill", skill,
    ]
    for key, value in params.items():
        cmd.extend([f"--{key}", str(value)])

    start = time.time()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    elapsed = time.time() - start

    return {
        "status": "ok" if result.returncode == 0 else "error",
        "output": result.stdout,
        "stderr": result.stderr if result.returncode != 0 else "",
        "elapsed": round(elapsed, 2),
        "returncode": result.returncode,
    }


def run_parallel(
    skill_calls: dict[str, dict[str, str]] | None = None,
    *,
    max_workers: int = 3,
    timeout: float = 600.0,
) -> tuple[dict[str, dict], dict[str, str]]:
    """Execute multiple skill calls in parallel using ThreadPoolExecutor.

    Parameters
    ----------
    skill_calls : dict or None
        Mapping of ``{name: {"skill": ..., "model_type": ...}}``.
        If ``None``, uses ``DEFAULT_SKILL_CALLS``.
    max_workers : int
        Maximum concurrent threads (default 3).
    timeout : float
        Per-skill timeout in seconds (default 600).

    Returns
    -------
    tuple[dict, dict]
        ``(results, errors)`` where:
        - ``results``: ``{name: {"status": "ok", "elapsed": ..., "output": ...}}``
        - ``errors``: ``{name: error_message}``

    Examples
    --------
    >>> results, errors = run_parallel(max_workers=3)
    >>> print(f"Success: {len(results)}/{len(results) + len(errors)}")
    """
    if skill_calls is None:
        skill_calls = DEFAULT_SKILL_CALLS

    results: dict[str, dict] = {}
    errors: dict[str, str] = {}

    def _run_one(name: str, config: dict[str, str]) -> tuple[str, dict]:
        """Run a single skill and return (name, result)."""
        skill = config["skill"]
        params = {k: v for k, v in config.items() if k != "skill"}
        result = _invoke_skill(skill, params, timeout=timeout)
        return name, result

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_run_one, name, config): name
            for name, config in skill_calls.items()
        }

        for future in as_completed(futures, timeout=timeout):
            name = futures[future]
            try:
                task_name, result = future.result()
                if result["status"] == "ok":
                    results[task_name] = result
                else:
                    errors[task_name] = result.get("stderr", "Unknown error")
            except Exception as exc:
                errors[name] = str(exc)

    return results, errors


# ---------------------------------------------------------------------------
# Generic parallel function execution
# ---------------------------------------------------------------------------

def run_parallel_funcs(
    funcs: dict[str, Callable[[], Any]],
    *,
    max_workers: int = 3,
    timeout: float = 600.0,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Execute arbitrary callables in parallel.

    Parameters
    ----------
    funcs : dict
        Mapping of ``{name: callable}``. Each callable takes no arguments.
    max_workers : int
        Maximum concurrent threads.
    timeout : float
        Overall timeout in seconds.

    Returns
    -------
    tuple[dict, dict]
        ``(results, errors)`` where:
        - ``results``: ``{name: return_value}``
        - ``errors``: ``{name: error_message}``

    Examples
    --------
    >>> import pandas as pd
    >>> funcs = {
    ...     "load_a": lambda: pd.read_csv("a.csv"),
    ...     "load_b": lambda: pd.read_csv("b.csv"),
    ... }
    >>> results, errors = run_parallel_funcs(funcs)
    """
    results: dict[str, Any] = {}
    errors: dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(func): name
            for name, func in funcs.items()
        }

        for future in as_completed(futures, timeout=timeout):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as exc:
                errors[name] = str(exc)

    return results, errors


# ---------------------------------------------------------------------------
# Result formatting
# ---------------------------------------------------------------------------

def format_results(
    results: dict[str, dict],
    errors: dict[str, str],
) -> str:
    """Format parallel execution results into a human-readable summary.

    Parameters
    ----------
    results : dict
        Successful results from :func:`run_parallel`.
    errors : dict
        Error results from :func:`run_parallel`.

    Returns
    -------
    str
        Formatted summary string.
    """
    total = len(results) + len(errors)
    lines: list[str] = [
        f"Parallel Execution Summary: {len(results)}/{total} succeeded",
        "=" * 50,
    ]

    if results:
        lines.append("\nSucceeded:")
        for name, result in sorted(results.items()):
            elapsed = result.get("elapsed", "?")
            lines.append(f"  + {name} ({elapsed}s)")

    if errors:
        lines.append("\nFailed:")
        for name, error in sorted(errors.items()):
            short_err = error[:100] if len(error) > 100 else error
            lines.append(f"  - {name}: {short_err}")

    total_time = sum(r.get("elapsed", 0) for r in results.values())
    lines.append(f"\nTotal execution time: {total_time:.1f}s")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run model training skills in parallel",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=3,
        help="Maximum parallel workers (default: 3)",
    )
    parser.add_argument(
        "--models",
        nargs="*",
        default=None,
        help="Specific models to run (default: all)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("PIPELINE_SKILL_TIMEOUT", 600)),
        help="Per-skill subprocess timeout in seconds (default: 600, or PIPELINE_SKILL_TIMEOUT env var)",
    )
    args = parser.parse_args()

    calls = DEFAULT_SKILL_CALLS
    if args.models:
        calls = {k: v for k, v in calls.items() if k in args.models}

    print(f"Running {len(calls)} models with {args.max_workers} workers (timeout={args.timeout}s)...")
    results, errors = run_parallel(calls, max_workers=args.max_workers, timeout=args.timeout)
    print(format_results(results, errors))
