<# Sprint 2 Verification Script — GenASL
   Run from project root:  .\run_sprint2_verification.ps1
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
        Write-Host "  [FAIL] $desc — $_" -ForegroundColor Red
        $script:failed++
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  GenASL — Sprint 2 Verification" -ForegroundColor Cyan
Write-Host "========================================`n"

# 1. Final clips
Write-Host "1. Asset files" -ForegroundColor Yellow
Check "50 clips in assets/final/" {
    (Get-ChildItem -Path "assets\final\*.mp4" -File).Count -eq 50
}
Check "raw/ is empty (only .gitkeep)" {
    (Get-ChildItem -Path "assets\raw\*.mp4" -File -ErrorAction SilentlyContinue).Count -eq 0
}
Check "trimmed/ is empty (only .gitkeep)" {
    (Get-ChildItem -Path "assets\trimmed\*.mp4" -File -ErrorAction SilentlyContinue).Count -eq 0
}

# 2. Manifest
Write-Host "`n2. Asset manifest" -ForegroundColor Yellow
Check "asset_manifest_v1.json exists" {
    Test-Path "assets\asset_manifest_v1.json"
}
Check "manifest has 50 entries" {
    $m = Get-Content "assets\asset_manifest_v1.json" -Raw | ConvertFrom-Json
    $m.total_assets -eq 50
}

# 3. Config
Write-Host "`n3. Config" -ForegroundColor Yellow
Check "config.yaml references asset_manifest" {
    (Get-Content "config.yaml" -Raw) -match "asset_manifest"
}

# 4. Governance docs
Write-Host "`n4. Docs" -ForegroundColor Yellow
Check "docs/governance_notes.md exists" {
    Test-Path "docs\governance_notes.md"
}
Check "docs/wlasl_coverage_report.txt exists" {
    Test-Path "docs\wlasl_coverage_report.txt"
}
Check "docs/asset_qa_notes.md exists" {
    Test-Path "docs\asset_qa_notes.md"
}

# 5. Tests
Write-Host "`n5. Pytest" -ForegroundColor Yellow
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
    Write-Host "  [FAIL] Failed to run pytest — $_" -ForegroundColor Red
    $failed++
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
if ($failed -eq 0) {
    Write-Host "  ALL CHECKS PASSED" -ForegroundColor Green
} else {
    Write-Host "  $failed CHECK(S) FAILED" -ForegroundColor Red
}
Write-Host "========================================`n" -ForegroundColor Cyan

exit $failed
