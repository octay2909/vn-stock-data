# AI Analyst

AI Analyst is a unified analytics platform that automates the full analytical workflow:
**Business Question -> Data Cleaning -> Validation -> Analysis -> Prediction -> Report**.
It covers descriptive, diagnostic, and predictive analytics with HTML/PPTX output.

---

## Architecture

Follows Anthropic's Claude Code component architecture. **LLM is the only brain** — no intent classifier, no state machine. Claude reads descriptions and self-decides dispatch.

```
+------------------------------------------------------------------+
|                      CLAUDE CODE CORE                             |
|   Agentic Loop + Built-in Tools (Read, Edit, Bash, Grep...)     |
+------------------------------------------------------------------+
        |           |          |          |         |         |
   CLAUDE.md    Skills    Subagents    Hooks      MCP    Plugins
   (Context)   (Knowledge) (Workers)  (Auto)   (External) (Package)
```

### Components

| Component | Count | Location |
|-----------|-------|----------|
| Main Agent | 1 | `CLAUDE.md` (this file) |
| Subagents | 8 | `.claude/agents/` |
| Skills | 24 | `.claude/skills/` |
| Hooks | via | `.claude/settings.json` |
| MCP | via | `.mcp.json` |

### Project-Specific Layers

| Layer | Purpose |
|-------|---------|
| `helpers/` | Python utilities (validation, charts, stats) |
| `themes/` | Visual theming (colors, typography, brands) |
| `knowledge/` | Persistent memory (datasets, metrics, history) |
| `config/` | System config (registry, pipelines, domains) |
| `data/` | Runtime data (raw -> cleaned -> reports) |
| `scripts/` | Execution scripts (parallel runner, tests) |

---

## Key Principles

1. **Disk-driven pipeline** — Each step writes JSON to disk. Next step reads from disk. No conversational state dependency.
2. **Single entry point** — User provides data + question. System handles everything.
3. **Conclusion-first** — Every finding, chart title, headline leads with the insight, not the metric label.
4. **Clean once, read many** — Phase 1.5 decides: (A) skip if `data/cleaned/{type}/{stem}_cleaned.xlsx` already exists, (B) skip if raw file scores Grade A with zero issues (already clean — use raw directly), (C) otherwise run `data-prep` skill and write cleaned file. All Phase 2+ agents read from whichever file was selected — never re-clean independently.
5. **Validation before analysis** — Never analyze data without verifying integrity first.
6. **Theme-consistent output** — All visuals follow a single theme system (customizable per brand).
7. **Resumable pipeline** — Explicit state tracking. Fail mid-pipeline -> resume from last checkpoint.
8. **Parallel where possible** — Independent model training runs simultaneously.

---

## Critical Rules

### present_files
Skills communicate ONLY through disk files. Never through conversation context.

```
[Skill A] --writes--> data/pipeline/{stem}/output_a.json
[Skill B] --reads-->  data/pipeline/{stem}/output_a.json
          --writes--> data/pipeline/{stem}/output_b.json
[Skill C] --reads-->  data/pipeline/{stem}/output_b.json
          --writes--> data/reports/{type}/{stem}/report.html
```

### no conversational state
Do NOT rely on conversation history for data passing between pipeline steps. All intermediate results must be persisted to `data/pipeline/` as JSON files. Each skill reads its inputs from disk and writes its outputs to disk.

### run_context
Every pipeline execution operates within a run context tied to the input file stem. All outputs go to `data/pipeline/{stem}/`. This ensures:
- Multiple analyses can coexist
- Runs are resumable from any checkpoint
- No cross-contamination between datasets

---

## Heritage

This project consolidates three prior codebases:

| Source | Inherited |
|--------|-----------|
| `analysis_agents/` | Descriptive/diagnostic pipeline, skill format, HTML/PPTX output, SCQA framework |
| `predictive_agents/` | 3 ML pipelines (forecasting, regression, classification), parallel execution |
| `ai-analyst-plugin-master/` | Validation framework, confidence scoring, chart helpers, theme system, registry pattern |

### Lean Refactor

Reduced from 34 → 24 skills by removing redundancy:
- **Deleted (7):** router (inlined into triage-report), setup, log-correction, model-monitor, state-manage, view-history, view-metrics
- **Merged into agents (3):** predictive-bridge → predictive-trainer, context-builder + stakeholder-comms → story-builder
- **Simplified:** question-framer no longer generates hypotheses (diagnostic-investigator owns this)

---

## Directory Structure

```
ai_analyst/
├── .claude/
│   ├── agents/          # 8 subagents (isolated workers)
│   ├── skills/          # 24 skills (lean — redundant/overlapping skills merged or removed)
│   ├── rules/           # Path-specific rules
│   ├── output-styles/   # Response format configs
│   └── settings.json    # Hooks configuration
├── .mcp.json            # External service connections
├── CLAUDE.md            # This file (context loaded every session)
├── helpers/             # Python utilities
│   ├── validation/      # 4-layer validation + confidence scoring
│   ├── charts/          # Chart generation helpers
│   └── stats/           # Statistical utilities
├── themes/              # Visual theming system
├── knowledge/           # Persistent memory across sessions
├── config/              # Registry, pipelines, domain rules
├── data/
│   ├── raw/             # Original uploaded files
│   ├── pipeline/        # Intermediate outputs (per stem)
│   └── reports/         # Final HTML/PPTX reports
└── scripts/             # Execution & test scripts
```

---

## Deterministic Scripts — NEVER Rewrite These

These scripts are the single source of truth for output generation. Always call them directly. Never write equivalent code from scratch in an agent or skill — doing so bypasses the template, theme, and SWD rules they enforce.

| Task | Script | Called by skill | Key flag |
|------|--------|-----------------|----------|
| Render chart PNGs (matplotlib/SWD) | `scripts/render_charts_swd.py` | `chart-render` | `--stem {stem} --no-title` |
| Build PPTX from template | `scripts/build_pptx_v3.py` | `slide-builder` | `--stem {stem} --output ...` |
| Build HTML report | `scripts/render_html.py` | `html-report` | `--stem {stem} --output ...` |

**Running on Windows:** Always set `PYTHONPATH` to the repo root parent before calling any script:
```powershell
$env:PYTHONPATH = "c:\This PC\the future analyst\AIDA\AIDA-All\AIDA"
python scripts/build_pptx_v3.py --stem {stem} --output data/reports/revenue/{stem}/slidedeck.pptx
```

**Why `build_pptx_v3.py` must be used:** It loads `templates/pptx_report/pptx_report_template.pptx` as the base presentation, which carries the Office theme (fonts, colors, corner radius). Any agent writing python-pptx from scratch will produce a file that looks completely different from the intended design.

**Why `render_charts_swd.py` must be used:** It enforces all SWD (Storytelling with Data) visual rules in code — no gridlines, single highlight color, spine-only axes. A chart generated outside this script will not match the template visual style.

**Prerequisite for `build_pptx_v3.py`:** `story_arc.json` must have a `data` field on every `chart_requirements[]` entry before running `render_charts_swd.py`. If `data` fields are missing, run `data-storytelling` skill first to embed them.

---

## Reference Documents

Technical details live in the skill/agent files themselves — read on-demand:

| What you need | Where to read |
|---------------|---------------|
| Pipeline execution order | `config/registry.yaml` · `config/pipelines.yaml` |
| Skill inputs/outputs/rules | `.claude/skills/{skill-name}/SKILL.md` |
| Agent responsibilities | `.claude/agents/{agent-name}.md` |
| Domain KPI rules | `config/domains/domain_rules.md` |
| Helper API | `helpers/__init__.py` (exports) |
| Chart style rules | `.claude/skills/chart-render/references/` |
| Slide layout specs | `.claude/skills/slide-builder/references/pptx_layouts.md` |
| HTML report_context schema | `.claude/skills/html-report/references/report_context_schema.md` |
| Theme system | `themes/_base.yaml` · `themes/theme_loader.py` |
