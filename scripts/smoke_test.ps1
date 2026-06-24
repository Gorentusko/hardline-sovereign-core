# Smoke test for a running Hardline Sovereign Core instance (Windows/PowerShell).
#
# Usage:
#   ./scripts/smoke_test.ps1 [-BaseUrl http://localhost:8099]
#
# Mirrors scripts/smoke_test.sh. Makes no external network calls; only
# talks to the local instance you point it at.

param(
    [string]$BaseUrl = "http://localhost:8099"
)

$pass = 0
$fail = 0

function Check-Json {
    param([string]$Description, [string]$Method, [string]$Path)
    Write-Host "-> $Description ($Method $Path)"
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl$Path" -Method $Method
        Write-Host "   OK"
        $script:pass++
        return $response
    } catch {
        Write-Host "   FAIL: $_"
        $script:fail++
        return $null
    }
}

Write-Host "Hardline Sovereign Core smoke test against $BaseUrl"
Write-Host "========================================================"

Check-Json -Description "Health check" -Method "GET" -Path "/health" | Out-Null
Check-Json -Description "Readiness check" -Method "GET" -Path "/ready" | Out-Null
Check-Json -Description "Stats" -Method "GET" -Path "/api/stats" | Out-Null
$seed = Check-Json -Description "Seed demo task" -Method "POST" -Path "/api/demo/seed"

Write-Host "-> Find newest task and run it"
try {
    $tasks = Invoke-RestMethod -Uri "$BaseUrl/api/tasks" -Method GET
    $taskId = $tasks.tasks[0].id
    $run = Invoke-RestMethod -Uri "$BaseUrl/api/tasks/$taskId/run" -Method POST
    if ($run.status -eq "success") {
        Write-Host "   OK"
        $pass++
    } else {
        Write-Host "   FAIL: run did not report success"
        $fail++
    }
} catch {
    Write-Host "   FAIL: $_"
    $fail++
}

Check-Json -Description "Verify ledger" -Method "GET" -Path "/api/ledger/verify" | Out-Null

Write-Host "========================================================"
Write-Host "Smoke test complete: $pass passed, $fail failed"

if ($fail -gt 0) {
    exit 1
}
