"""AI Analyst helpers package — unified imports for all helper modules.

Subpackages:
    validation/  — 4-layer validation framework + confidence scoring
    utils/       — File I/O, date helpers, common utilities

Modules:
    analytics_helpers  — RFM, concentration, control charts, scoring
    chart_helpers      — SWD-based chart builders (15 chart types)
    chart_palette      — WCAG-compliant color palette utilities
    deep_profiler      — Distribution, temporal, correlation, anomaly profiling
    pipeline_state     — State management, checkpoints, atomic I/O
    stats_helpers      — Statistical tests, power analysis, effect sizes
"""

from ai_analyst.helpers.analytics_helpers import (
    rfm_analysis,
    concentration_analysis,
    compare_segments,
    control_chart,
    score_findings,
    synthesize_insights,
)
from ai_analyst.helpers.chart_helpers import (
    swd_style,
    highlight_bar,
    highlight_line,
    waterfall,
    heatmap,
    funnel,
    scatter,
    box,
    stacked_bar,
    slope,
    diverging_bar,
    donut,
    area,
    grouped_bar,
    bullet,
    gauge,
    action_title,
    annotate_point,
    save_chart,
)
from ai_analyst.helpers.chart_palette import (
    apply_theme_colors,
    highlight_palette,
    categorical_colors,
    ensure_contrast,
    palette_for_n,
    format_hex,
)
from ai_analyst.helpers.deep_profiler import (
    profile_distributions,
    profile_temporal_patterns,
    profile_correlations,
    profile_completeness,
    profile_anomalies,
)
from ai_analyst.helpers.pipeline_state import (
    create_initial_state,
    update_agent_status,
    get_next_agent,
    is_pipeline_complete,
    save_state,
    load_state,
    create_checkpoint,
    resume_from_checkpoint,
)
from ai_analyst.helpers.stats_helpers import (
    two_sample_proportion_test,
    two_sample_mean_test,
    mann_whitney_test,
    confidence_interval,
    chi_squared_test,
    bootstrap_ci,
    adjust_pvalues,
    characterize_distribution,
    rank_dimensions,
    sample_size_proportion,
    sample_size_mean,
    detectable_effect,
)

__all__: list[str] = [
    # analytics_helpers
    "rfm_analysis",
    "concentration_analysis",
    "compare_segments",
    "control_chart",
    "score_findings",
    "synthesize_insights",
    # chart_helpers
    "swd_style",
    "highlight_bar",
    "highlight_line",
    "waterfall",
    "heatmap",
    "funnel",
    "scatter",
    "box",
    "stacked_bar",
    "slope",
    "diverging_bar",
    "donut",
    "area",
    "grouped_bar",
    "bullet",
    "gauge",
    "action_title",
    "annotate_point",
    "save_chart",
    # chart_palette
    "apply_theme_colors",
    "highlight_palette",
    "categorical_colors",
    "ensure_contrast",
    "palette_for_n",
    "format_hex",
    # deep_profiler
    "profile_distributions",
    "profile_temporal_patterns",
    "profile_correlations",
    "profile_completeness",
    "profile_anomalies",
    # pipeline_state
    "create_initial_state",
    "update_agent_status",
    "get_next_agent",
    "is_pipeline_complete",
    "save_state",
    "load_state",
    "create_checkpoint",
    "resume_from_checkpoint",
    # stats_helpers
    "two_sample_proportion_test",
    "two_sample_mean_test",
    "mann_whitney_test",
    "confidence_interval",
    "chi_squared_test",
    "bootstrap_ci",
    "adjust_pvalues",
    "characterize_distribution",
    "rank_dimensions",
    "sample_size_proportion",
    "sample_size_mean",
    "detectable_effect",
]
