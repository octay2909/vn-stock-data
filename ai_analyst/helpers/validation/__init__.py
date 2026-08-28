"""
Validation framework for the AI Data Analyst.

4-layer validation + confidence scoring:
    Layer 1: Structural validation (schema, PK, completeness, date range)
    Layer 2: Logical validation (aggregation, trends, ratios, monotonicity)
    Layer 3: Business rules (ranges, relationships, temporal, segments)
    Layer 4: Simpson's paradox detection (single + multi-segment scan)
    Synthesis: Confidence scoring (7-factor, 0-100, A-F grades)
"""

from ai_analyst.helpers.validation.structural_validator import (
    validate_schema,
    validate_primary_key,
    validate_completeness,
    validate_date_range,
    validate_referential_integrity,
    validate_value_domain,
    validate_row_count,
    run_structural_checks,
)

from ai_analyst.helpers.validation.logical_validator import (
    validate_aggregation_consistency,
    validate_percentages_sum,
    validate_monotonic,
    validate_trend_consistency,
    validate_ratio_bounds,
    validate_group_balance,
    validate_no_future_dates,
    run_logical_checks,
    validate_trend_continuity,
    validate_segment_exhaustiveness,
    validate_temporal_consistency,
)

from ai_analyst.helpers.validation.business_rules import (
    validate_ranges,
    validate_metric_relationships,
    validate_temporal_consistency as validate_business_temporal,
    validate_segment_coverage,
    validate_no_negative,
    validate_cardinality,
    validate_business_rules,
    get_default_rules,
    validate_rates,
    validate_yoy_change,
)

from ai_analyst.helpers.validation.simpsons_paradox import (
    check_simpsons_paradox,
    check_simpsons_multi_segment,
    weighted_vs_unweighted,
    generate_paradox_report,
    suggest_segments_to_check,
    scan_dimensions,
)

from ai_analyst.helpers.validation.confidence_scoring import (
    score_confidence,
    format_confidence_badge,
    merge_confidence_scores,
)

__all__ = [
    # Layer 1
    "validate_schema", "validate_primary_key", "validate_completeness",
    "validate_date_range", "validate_referential_integrity",
    "validate_value_domain", "validate_row_count", "run_structural_checks",
    # Layer 2
    "validate_aggregation_consistency", "validate_percentages_sum",
    "validate_monotonic", "validate_trend_consistency",
    "validate_ratio_bounds", "validate_group_balance",
    "validate_no_future_dates", "run_logical_checks",
    "validate_trend_continuity", "validate_segment_exhaustiveness",
    "validate_temporal_consistency",
    # Layer 3
    "validate_ranges", "validate_metric_relationships",
    "validate_business_temporal", "validate_segment_coverage",
    "validate_no_negative", "validate_cardinality",
    "validate_business_rules", "get_default_rules",
    "validate_rates", "validate_yoy_change",
    # Layer 4
    "check_simpsons_paradox", "check_simpsons_multi_segment",
    "weighted_vs_unweighted", "generate_paradox_report",
    "suggest_segments_to_check", "scan_dimensions",
    # Confidence
    "score_confidence", "format_confidence_badge", "merge_confidence_scores",
]
