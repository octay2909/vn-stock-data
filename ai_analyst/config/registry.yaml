# AI Analyst — Agent DAG (Dependency Graph)
# Defines execution order and dependencies between subagents.
# Used by pipeline-orchestrator to determine spawn order.
#
# LEAN version: 34 → 24 skills. Removed: router, setup, log-correction,
# model-monitor, state-manage, view-history, view-metrics.
# Merged into agents: predictive-bridge, context-builder, stakeholder-comms.

dag:
  phases:
    - id: 0
      name: blueprint
      agents: []
      skills: [triage-report]
      parallel: false
      wait_for_user: true

    - id: 1
      name: understand
      agents: [question-framer, data-profiler]
      skills: []
      parallel: true
      depends_on: [0]

    - id: 2
      name: analyze
      agents: [descriptive-analyst, diagnostic-investigator]
      skills: []
      parallel: true
      depends_on: [1]

    - id: 3
      name: predict
      agents: [predictive-trainer]
      skills: []
      parallel: false
      depends_on: [2]
      conditional: true  # Only if triage says predictive needed

    - id: 4
      name: output
      agents: [story-builder, visualizer]
      skills: []
      parallel: true
      depends_on: [3]

    - id: 5
      name: quality-gate
      agents: [quality-reviewer]
      skills: []
      parallel: false
      depends_on: [4]
      conditional: true  # Skip for L1/L2 — only run for L3/L4 (saves 4-5 min)

# Subagent registry
subagents:
  question-framer:
    file: .claude/agents/question-framer.md
    model: sonnet
    skills: [triage-report, define-metric, business-context]

  data-profiler:
    file: .claude/agents/data-profiler.md
    model: sonnet
    skills: [data-prep, validate]

  descriptive-analyst:
    file: .claude/agents/descriptive-analyst.md
    model: sonnet
    skills: [descriptive]

  diagnostic-investigator:
    file: .claude/agents/diagnostic-investigator.md
    model: sonnet
    skills: [diagnostic, size-opportunity]

  predictive-trainer:
    file: .claude/agents/predictive-trainer.md
    model: sonnet
    skills:
      - predictive-data-prep
      - train-test-split
      - forecast-train
      - regression-train
      - classification-train
      - model-evaluate
      - model-finalize

  story-builder:
    file: .claude/agents/story-builder.md
    model: sonnet
    skills: [data-storytelling]

  visualizer:
    file: .claude/agents/visualizer.md
    model: sonnet
    skills: [chart-data, chart-render, html-report, slide-builder]

  quality-reviewer:
    file: .claude/agents/quality-reviewer.md
    model: sonnet
    skills: [validate]
