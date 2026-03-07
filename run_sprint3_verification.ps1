<# Sprint 3 Verification Script - GenASL
   Run from project root:  .\run_sprint3_verification.ps1
#>

$ErrorActionPreference = "Stop"
$failed = 0

function Check($desc, [scriptblock]$test) {
    try {
        $result = & $test
        if ($result) {
            Write-Host "  [PASS] $desc" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] $desc" -ForegroundColor Red
            $script:failed++
        }
    } catch {
        Write-Host "  [FAIL] $desc - $_" -ForegroundColor Red
        $script:failed++
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  GenASL - Sprint 3 Verification" -ForegroundColor Cyan
Write-Host "========================================`n"

# -------------------------------------------------------------------
# 1. Confidence Threshold
# -------------------------------------------------------------------
Write-Host "1. Confidence threshold" -ForegroundColor Yellow
Check "threshold is 0.80 in config.yaml" {
    (Get-Content "config.yaml" -Raw) -match "confidence_threshold:\s*0\.80"
}
Check "threshold comment block present" {
    (Get-Content "config.yaml" -Raw) -match "RAI rationale"
}
Check "threshold comparison log exists" {
    Test-Path "logs\sprint3_threshold_comparison.json"
}

# -------------------------------------------------------------------
# 2. Normalization Fixes
# -------------------------------------------------------------------
Write-Host "`n2. Normalization fixes" -ForegroundColor Yellow
Check "bracket stripping function in fetcher.py" {
    (Get-Content "src\transcript_ingestion\fetcher.py" -Raw) -match "_strip_brackets"
}
Check "short segment filter in run_pipeline.py" {
    (Get-Content "src\pipeline\run_pipeline.py" -Raw) -match "_filter_short_segments"
}

# -------------------------------------------------------------------
# 3. Overlap Resolution
# -------------------------------------------------------------------
Write-Host "`n3. Overlap resolution" -ForegroundColor Yellow
Check "_resolve_overlaps function exists" {
    (Get-Content "src\pipeline\run_pipeline.py" -Raw) -match "_resolve_overlaps"
}

# -------------------------------------------------------------------
# 4. PiP Compositor
# -------------------------------------------------------------------
Write-Host "`n4. PiP compositor" -ForegroundColor Yellow
Check "src/compositor/__init__.py exists" {
    Test-Path "src\compositor\__init__.py"
}
Check "src/compositor/compositor.py exists" {
    Test-Path "src\compositor\compositor.py"
}
Check "src/compositor/downloader.py exists" {
    Test-Path "src\compositor\downloader.py"
}
Check "compose_pip function defined" {
    (Get-Content "src\compositor\compositor.py" -Raw) -match "def compose_pip"
}
Check "disclosure label in compositor" {
    (Get-Content "src\compositor\compositor.py" -Raw) -match "AI-generated ASL overlay"
}

# -------------------------------------------------------------------
# 5. Streamlit UI
# -------------------------------------------------------------------
Write-Host "`n5. Streamlit UI" -ForegroundColor Yellow
Check "src/ui/__init__.py exists" {
    Test-Path "src\ui\__init__.py"
}
Check "src/ui/app.py exists" {
    Test-Path "src\ui\app.py"
}
Check "streamlit installed" {
    & ".venv\Scripts\python.exe" -c "import streamlit" 2>&1
    $LASTEXITCODE -eq 0
}

# -------------------------------------------------------------------
# 6. Run Log Updates
# -------------------------------------------------------------------
Write-Host "`n6. Run log updates" -ForegroundColor Yellow
Check "run log includes filtered_segments field" {
    (Get-Content "src\pipeline\run_pipeline.py" -Raw) -match '"filtered_segments"'
}
Check "run log includes overlaps_resolved field" {
    (Get-Content "src\pipeline\run_pipeline.py" -Raw) -match '"overlaps_resolved"'
}
Check "run log includes confidence_threshold field" {
    (Get-Content "src\pipeline\run_pipeline.py" -Raw) -match '"confidence_threshold"'
}

# -------------------------------------------------------------------
# 7. Pilot Feedback Docs
# -------------------------------------------------------------------
Write-Host "`n7. Pilot feedback docs" -ForegroundColor Yellow
Check "pilot_feedback_form.md exists" {
    Test-Path "docs\pilot_feedback_form.md"
}
Check "pilot_results_template.md exists" {
    Test-Path "docs\pilot_results_template.md"
}
Check "feedback form has star rating section" {
    (Get-Content "docs\pilot_feedback_form.md" -Raw) -match "1.*5 stars"
}
Check "feedback form has disclosure label question" {
    (Get-Content "docs\pilot_feedback_form.md" -Raw) -match "disclosure label"
}

# -------------------------------------------------------------------
# 8. Governance Notes
# -------------------------------------------------------------------
Write-Host "`n8. Governance notes" -ForegroundColor Yellow
Check "Sprint 3 section in governance_notes.md" {
    (Get-Content "docs\governance_notes.md" -Raw) -match "Sprint 3"
}
Check "risk assessment table in governance notes" {
    (Get-Content "docs\governance_notes.md" -Raw) -match "Updated risk assessment"
}
Check "transparency label documented" {
    (Get-Content "docs\governance_notes.md" -Raw) -match "disclosure label"
}

# -------------------------------------------------------------------
# 9. Tests
# -------------------------------------------------------------------
Write-Host "`n9. Pytest" -ForegroundColor Yellow
Check "test_sprint3.py exists" {
    Test-Path "tests\test_sprint3.py"
}
Check "test_compositor_spike.py exists" {
    Test-Path "tests\test_compositor_spike.py"
}
try {
    & ".venv\Scripts\python.exe" -m pytest tests/ -v --tb=short 2>&1 | Tee-Object -Variable pytestOut
    $pytestExit = $LASTEXITCODE
    if ($pytestExit -eq 0) {
        Write-Host "  [PASS] All pytest tests passed" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] pytest exited with code $pytestExit" -ForegroundColor Red
        $failed++
    }
} catch {
    Write-Host "  [FAIL] Failed to run pytest - $_" -ForegroundColor Red
    $failed++
}

# -------------------------------------------------------------------
# Summary
# -------------------------------------------------------------------
Write-Host "`n========================================" -ForegroundColor Cyan
if ($failed -eq 0) {
    Write-Host "  ALL CHECKS PASSED" -ForegroundColor Green
} else {
    Write-Host "  $failed CHECK(S) FAILED" -ForegroundColor Red
}
Write-Host "========================================`n" -ForegroundColor Cyan

exit $failed
