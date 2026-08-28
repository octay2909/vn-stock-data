"""File utility helpers — atomic writes, YAML/JSON I/O, hashing, directory management.

Provides safe, atomic file operations that create parent directories automatically
and handle common failure modes (missing files, parse errors, encoding issues).

Public API:
    atomic_write()          - Atomic string write via temp + replace
    atomic_write_yaml()     - Atomic YAML dict write
    safe_read_yaml()        - Read YAML, return None on failure
    safe_write_yaml()       - Write YAML (non-atomic, simpler)
    safe_read_json()        - Read JSON, return None on failure
    safe_write_json()       - Write JSON with pretty-print
    content_hash()          - SHA-256 content fingerprint
    has_content_changed()   - Check if file content differs
    ensure_directory()      - mkdir -p equivalent
    list_yaml_files()       - List .yaml/.yml in a directory
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------

def atomic_write(path: str | Path, content: str) -> None:
    """Write content to a file atomically via temp file + os.replace.

    Creates parent directories if they don't exist.
    Cleans up temp file on error.

    Parameters
    ----------
    path : str or Path
        Destination file path.
    content : str
        Text content to write.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_yaml(path: str | Path, data: dict) -> None:
    """Write a dict to a YAML file atomically.

    Parameters
    ----------
    path : str or Path
        Destination YAML file path.
    data : dict
        Data to serialize.
    """
    content = yaml.dump(
        data,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    atomic_write(path, content)


# ---------------------------------------------------------------------------
# Safe read/write — YAML
# ---------------------------------------------------------------------------

def safe_read_yaml(path: str | Path) -> dict | None:
    """Read a YAML file, returning ``None`` if it doesn't exist or fails to parse.

    Parameters
    ----------
    path : str or Path
        Path to the YAML file.

    Returns
    -------
    dict or None
        Parsed YAML content, or ``None`` on any error.
    """
    path = Path(path)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError):
        return None


def safe_write_yaml(path: str | Path, data: dict) -> bool:
    """Write a dict to a YAML file with parent directory creation.

    Parameters
    ----------
    path : str or Path
        Destination YAML file path.
    data : dict
        Data to serialize.

    Returns
    -------
    bool
        ``True`` if write succeeded, ``False`` on error.
    """
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
        return True
    except (OSError, yaml.YAMLError):
        return False


# ---------------------------------------------------------------------------
# Safe read/write — JSON
# ---------------------------------------------------------------------------

def safe_read_json(path: str | Path) -> dict | list | None:
    """Read a JSON file, returning ``None`` if it doesn't exist or fails to parse.

    Parameters
    ----------
    path : str or Path
        Path to the JSON file.

    Returns
    -------
    dict, list, or None
        Parsed JSON content, or ``None`` on any error.
    """
    path = Path(path)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def safe_write_json(path: str | Path, data: Any, indent: int = 2) -> bool:
    """Write data to a JSON file with pretty-print and parent directory creation.

    Parameters
    ----------
    path : str or Path
        Destination JSON file path.
    data : Any
        JSON-serializable data.
    indent : int
        Indentation level (default 2).

    Returns
    -------
    bool
        ``True`` if write succeeded, ``False`` on error.
    """
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False, default=str)
        return True
    except (TypeError, OSError):
        return False


# ---------------------------------------------------------------------------
# Content hashing & change detection
# ---------------------------------------------------------------------------

def content_hash(content: str) -> str:
    """Return SHA-256 hash of content (first 16 hex chars).

    Parameters
    ----------
    content : str
        Text content to hash.

    Returns
    -------
    str
        16-character hex digest.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def has_content_changed(path: str | Path, new_content: str) -> bool:
    """Check if new content differs from the existing file.

    Returns ``True`` if the file doesn't exist or content has changed.

    Parameters
    ----------
    path : str or Path
        Path to the existing file.
    new_content : str
        Content to compare against.

    Returns
    -------
    bool
        ``True`` if content is different or file doesn't exist.
    """
    path = Path(path)
    if not path.exists():
        return True
    try:
        existing = path.read_text(encoding="utf-8")
        return content_hash(existing) != content_hash(new_content)
    except (OSError, UnicodeDecodeError):
        return True


# ---------------------------------------------------------------------------
# Directory utilities
# ---------------------------------------------------------------------------

def ensure_directory(path: str | Path) -> Path:
    """Create directory and all parents if they don't exist.

    Parameters
    ----------
    path : str or Path
        Directory path to create.

    Returns
    -------
    Path
        The resolved directory path.
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_yaml_files(directory: str | Path) -> list[Path]:
    """List all ``.yaml`` and ``.yml`` files in a directory (non-recursive).

    Parameters
    ----------
    directory : str or Path
        Directory to scan.

    Returns
    -------
    list[Path]
        Sorted list of YAML file paths.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return []
    return sorted(
        [f for f in directory.iterdir() if f.suffix in (".yaml", ".yml")],
        key=lambda p: p.name,
    )
