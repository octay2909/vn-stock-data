# validate_structure.ps1 - AI Analyst Project Structure Validator
# Verifies that all required directories and files exist.
# Run: powershell -ExecutionPolicy Bypass -File scripts/validate_structure.ps1

param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$Verbose,
    [switch]$Fix
)

$ErrorActionPreference = "Continue"

# ---------------------------------------------------------------------------
# Required structure definition
# ---------------------------------------------------------------------------

$requiredDirs = @(
    "ai_analyst/helpers",
    "ai_analyst/helpers/utils",
    "ai_analyst/helpers/validation",
    "ai_analyst/themes",
    "ai_analyst/themes/brands",
    "ai_analyst/knowledge",
    "ai_analyst/knowledge/datasets",
    "ai_analyst/knowledge/datasets/_template",
    "ai_analyst/knowledge/history",
    "ai_analyst/scripts",
    "ai_analyst/config",
    "ai_analyst/config/domains"
)

$requiredFiles = @(
    # Helpers - core modules
    "ai_analyst/helpers/__init__.py",
    "ai_analyst/helpers/analytics_helpers.py",
    "ai_analyst/helpers/chart_helpers.py",
    "ai_analyst/helpers/chart_palette.py",
    "ai_analyst/helpers/deep_profiler.py",
    "ai_analyst/helpers/pipeline_state.py",
    "ai_analyst/helpers/stats_helpers.py",
    # Helpers - utils
    "ai_analyst/helpers/utils/__init__.py",
    "ai_analyst/helpers/utils/file_helpers.py",
    "ai_analyst/helpers/utils/date_helpers.py",
    # Helpers - validation
    "ai_analyst/helpers/validation/__init__.py",
    "ai_analyst/helpers/validation/structural_validator.py",
    "ai_analyst/helpers/validation/logical_validator.py",
    "ai_analyst/helpers/validation/business_rules.py",
    "ai_analyst/helpers/validation/simpsons_paradox.py",
    "ai_analyst/helpers/validation/confidence_scoring.py",
    # Themes
    "ai_analyst/themes/__init__.py",
    "ai_analyst/themes/_base.yaml",
    "ai_analyst/themes/theme_loader.py",
    # Knowledge
    "ai_analyst/knowledge/active.yaml",
    "ai_analyst/knowledge/datasets/_template/schema.md",
    "ai_analyst/knowledge/datasets/_template/quirks.md",
    "ai_analyst/knowledge/datasets/_template/metrics.yaml",
    # Scripts
    "ai_analyst/scripts/run_parallel.py",
    # Config
    "ai_analyst/config/pipelines.yaml",
    "ai_analyst/config/domains/domain_rules.md",
    # Root
    "requirements.txt",
    ".gitignore"
)

# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------

$passed = 0
$failed = 0
$fixed = 0
$errors = @()

Write-Host ""
Write-Host "AI Analyst - Structure Validation" -ForegroundColor Cyan
Write-Host ("=" * 50) -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot"
Write-Host ""

# Check directories
Write-Host "Checking directories..." -ForegroundColor Yellow
foreach ($dir in $requiredDirs) {
    $fullPath = Join-Path $ProjectRoot $dir
    if (Test-Path $fullPath -PathType Container) {
        if ($Verbose) { Write-Host "  [OK] $dir" -ForegroundColor Green }
        $passed++
    } else {
        if ($Fix) {
            New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
            Write-Host "  [FIXED] $dir (created)" -ForegroundColor Yellow
            $fixed++
        } else {
            Write-Host "  [MISSING] $dir" -ForegroundColor Red
            $errors += "Directory missing: $dir"
            $failed++
        }
    }
}

# Check files
Write-Host ""
Write-Host "Checking files..." -ForegroundColor Yellow
foreach ($file in $requiredFiles) {
    $fullPath = Join-Path $ProjectRoot $file
    if (Test-Path $fullPath -PathType Leaf) {
        if ($Verbose) { Write-Host "  [OK] $file" -ForegroundColor Green }
        $passed++
    } else {
        Write-Host "  [MISSING] $file" -ForegroundColor Red
        $errors += "File missing: $file"
        $failed++
    }
}

# Check Python files have content (not empty)
Write-Host ""
Write-Host "Checking Python files have content..." -ForegroundColor Yellow
$pyFiles = $requiredFiles | Where-Object { $_ -match "\.py$" }
foreach ($file in $pyFiles) {
    $fullPath = Join-Path $ProjectRoot $file
    if (Test-Path $fullPath) {
        $content = Get-Content $fullPath -Raw -ErrorAction SilentlyContinue
        if ([string]::IsNullOrWhiteSpace($content)) {
            Write-Host "  [EMPTY] $file" -ForegroundColor Red
            $errors += "File empty: $file"
            $failed++
        } else {
            if ($Verbose) { Write-Host "  [OK] $file (has content)" -ForegroundColor Green }
            $passed++
        }
    }
}

# Check YAML files parse correctly
Write-Host ""
Write-Host "Checking YAML files..." -ForegroundColor Yellow
$yamlFiles = $requiredFiles | Where-Object { $_ -match "\.(yaml|yml)$" }
foreach ($file in $yamlFiles) {
    $fullPath = Join-Path $ProjectRoot $file
    if (Test-Path $fullPath) {
        $content = Get-Content $fullPath -Raw -ErrorAction SilentlyContinue
        if ([string]::IsNullOrWhiteSpace($content)) {
            Write-Host "  [EMPTY] $file" -ForegroundColor Red
            $errors += "YAML file empty: $file"
            $failed++
        } else {
            if ($Verbose) { Write-Host "  [OK] $file" -ForegroundColor Green }
            $passed++
        }
    }
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host ("=" * 50) -ForegroundColor Cyan
Write-Host "Results:" -ForegroundColor Cyan
Write-Host "  Passed:  $passed" -ForegroundColor Green
if ($fixed -gt 0) { Write-Host "  Fixed:   $fixed" -ForegroundColor Yellow }
if ($failed -gt 0) {
    Write-Host "  Failed:  $failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Errors:" -ForegroundColor Red
    foreach ($err in $errors) {
        Write-Host "  - $err" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Run with -Fix to auto-create missing directories." -ForegroundColor Yellow
    exit 1
} else {
    Write-Host ""
    Write-Host "All checks passed!" -ForegroundColor Green
    exit 0
}
