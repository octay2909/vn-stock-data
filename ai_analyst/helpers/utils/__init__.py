"""Utility subpackage — file I/O, date helpers, and common utilities."""

from ai_analyst.helpers.utils.file_helpers import (
    atomic_write,
    atomic_write_yaml,
    content_hash,
    ensure_directory,
    has_content_changed,
    list_yaml_files,
    safe_read_json,
    safe_read_yaml,
    safe_write_json,
    safe_write_yaml,
)
from ai_analyst.helpers.utils.date_helpers import (
    detect_date_column,
    detect_grain,
    parse_dates,
    date_range_summary,
    fill_date_gaps,
    fiscal_quarter,
    fiscal_year,
    relative_period_label,
)

__all__: list[str] = [
    # file_helpers
    "atomic_write",
    "atomic_write_yaml",
    "content_hash",
    "ensure_directory",
    "has_content_changed",
    "list_yaml_files",
    "safe_read_json",
    "safe_read_yaml",
    "safe_write_json",
    "safe_write_yaml",
    # date_helpers
    "detect_date_column",
    "detect_grain",
    "parse_dates",
    "date_range_summary",
    "fill_date_gaps",
    "fiscal_quarter",
    "fiscal_year",
    "relative_period_label",
]
