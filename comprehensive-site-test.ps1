# Comprehensive Site Testing Script
# Tests all routes and functionality from SITE_AUDIT_CHECKLIST.md

$baseUrl = "https://swarmsync.ai"
$apiUrl = "https://swarmsync-api.up.railway.app"

$passed = 0
$failed = 0
$results = @()

function Test-Route {
    param(
        [string]$url,
        [string]$description,
        [int]$expectedStatus = 200
    )
    
    try {
        $response = Invoke-WebRequest -Uri $url -Method GET -ErrorAction Stop -TimeoutSec 10 -UseBasicParsing
        if ($response.StatusCode -eq $expectedStatus) {
            Write-Host "[PASS] $description" -ForegroundColor Green
            $script:passed++
            $script:results += [PSCustomObject]@{
                Status = "PASS"
                Category = "Routes"
                Test = $description
                URL = $url
            }
            return $true
        }
    } catch {
        Write-Host "[FAIL] $description - $($_.Exception.Message)" -ForegroundColor Red
        $script:failed++
        $script:results += [PSCustomObject]@{
            Status = "FAIL"
            Category = "Routes"
            Test = $description
            URL = $url
            Error = $_.Exception.Message
        }
        return $false
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "COMPREHENSIVE SITE AUDIT TEST" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# NAVIGATION & ROUTING
Write-Host "TESTING NAVIGATION & ROUTING" -ForegroundColor Yellow
Write-Host "----------------------------" -ForegroundColor Yellow

Test-Route "$baseUrl/" "Homepage"
Test-Route "$baseUrl/agents" "Agents marketplace"
Test-Route "$baseUrl/pricing" "Pricing page"
Test-Route "$baseUrl/platform" "Platform page"
Test-Route "$baseUrl/use-cases" "Use cases page"
Test-Route "$baseUrl/security" "Security page"
Test-Route "$baseUrl/resources" "Resources page"
Test-Route "$baseUrl/faq" "FAQ page"
Test-Route "$baseUrl/privacy" "Privacy policy"
Test-Route "$baseUrl/terms" "Terms of service"
Test-Route "$baseUrl/login" "Login page"
Test-Route "$baseUrl/register" "Registration page"
Test-Route "$baseUrl/agent-orchestration-guide" "Agent orchestration guide"
Test-Route "$baseUrl/vs/build-your-own" "Build vs Buy page"

Write-Host ""

# API ENDPOINTS
Write-Host "TESTING API ENDPOINTS" -ForegroundColor Yellow
Write-Host "---------------------" -ForegroundColor Yellow

Test-Route "$apiUrl/health" "Health check"
Test-Route "$apiUrl/agents" "Agents API"
Test-Route "$apiUrl/billing/plans" "Billing plans API"

Write-Host ""

# TECHNICAL HEALTH
Write-Host "TESTING TECHNICAL HEALTH" -ForegroundColor Yellow
Write-Host "------------------------" -ForegroundColor Yellow

Test-Route "$baseUrl/sitemap.xml" "Sitemap.xml"
Test-Route "$baseUrl/robots.txt" "Robots.txt"
Test-Route "$baseUrl/favicon.ico" "Favicon"

Write-Host ""

# SUMMARY
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "TEST RESULTS SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Passed: $passed" -ForegroundColor Green
Write-Host "Failed: $failed" -ForegroundColor Red
Write-Host "Total: $($passed + $failed)" -ForegroundColor White
Write-Host ""

if ($failed -gt 0) {
    Write-Host "FAILED TESTS:" -ForegroundColor Red
    $results | Where-Object { $_.Status -eq "FAIL" } | ForEach-Object {
        Write-Host "  - $($_.Test)" -ForegroundColor Red
        Write-Host "    URL: $($_.URL)" -ForegroundColor Gray
        if ($_.Error) {
            Write-Host "    Error: $($_.Error)" -ForegroundColor Yellow
        }
    }
    Write-Host ""
}

# Export results
$results | Export-Csv -Path "site-audit-results.csv" -NoTypeInformation
Write-Host "Results exported to: site-audit-results.csv" -ForegroundColor Cyan
Write-Host ""

# Exit code
if ($failed -gt 0) {
    exit 1
} else {
    Write-Host "ALL TESTS PASSED!" -ForegroundColor Green
    exit 0
}

