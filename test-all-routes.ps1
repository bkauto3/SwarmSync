# PowerShell script to systematically test all routes from SITE_AUDIT_CHECKLIST.md

$baseUrl = "https://swarmsync.ai"
$apiUrl = "https://swarmsync-api.up.railway.app"

Write-Host "SYSTEMATIC ROUTE TESTING" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host ""

# Test results
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
        $response = Invoke-WebRequest -Uri $url -Method GET -ErrorAction Stop -TimeoutSec 10
        if ($response.StatusCode -eq $expectedStatus) {
            Write-Host "[PASS] $description" -ForegroundColor Green
            Write-Host "   URL: $url" -ForegroundColor Gray
            $script:passed++
            $script:results += [PSCustomObject]@{
                Status = "PASS"
                Description = $description
                URL = $url
                StatusCode = $response.StatusCode
            }
            return $true
        } else {
            Write-Host "[FAIL] $description" -ForegroundColor Red
            Write-Host "   URL: $url" -ForegroundColor Gray
            Write-Host "   Expected: $expectedStatus, Got: $($response.StatusCode)" -ForegroundColor Yellow
            $script:failed++
            $script:results += [PSCustomObject]@{
                Status = "FAIL"
                Description = $description
                URL = $url
                StatusCode = $response.StatusCode
                Expected = $expectedStatus
            }
            return $false
        }
    } catch {
        Write-Host "[FAIL] $description" -ForegroundColor Red
        Write-Host "   URL: $url" -ForegroundColor Gray
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
        $script:failed++
        $script:results += [PSCustomObject]@{
            Status = "FAIL"
            Description = $description
            URL = $url
            Error = $_.Exception.Message
        }
        return $false
    }
}

Write-Host "TESTING NAVIGATION AND ROUTING" -ForegroundColor Yellow
Write-Host ""

# Homepage
Test-Route "$baseUrl/" "Homepage"

# Main navigation
Test-Route "$baseUrl/agents" "Agents page"
Test-Route "$baseUrl/pricing" "Pricing page"

# Marketing pages
Test-Route "$baseUrl/platform" "Platform page"
Test-Route "$baseUrl/use-cases" "Use cases page"
Test-Route "$baseUrl/agent-orchestration-guide" "Agent orchestration guide"
Test-Route "$baseUrl/vs/build-your-own" "Build vs Buy page"
Test-Route "$baseUrl/security" "Security page"
Test-Route "$baseUrl/resources" "Resources page"
Test-Route "$baseUrl/faq" "FAQ page"

# Legal pages
Test-Route "$baseUrl/privacy" "Privacy policy"
Test-Route "$baseUrl/terms" "Terms of service"

# Auth pages (should load, not redirect)
Test-Route "$baseUrl/login" "Login page"
Test-Route "$baseUrl/register" "Register page"

Write-Host ""
Write-Host "TESTING API ENDPOINTS" -ForegroundColor Yellow
Write-Host ""

# API endpoints
Test-Route "$apiUrl/agents" "Agents API endpoint"
Test-Route "$apiUrl/health" "Health check endpoint"

Write-Host ""
Write-Host "TEST RESULTS SUMMARY" -ForegroundColor Cyan
Write-Host "====================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Passed: $passed" -ForegroundColor Green
Write-Host "Failed: $failed" -ForegroundColor Red
Write-Host "Total: $($passed + $failed)" -ForegroundColor White
Write-Host ""

if ($failed -gt 0) {
    Write-Host "FAILED TESTS:" -ForegroundColor Red
    Write-Host ""
    $results | Where-Object { $_.Status -eq "FAIL" } | ForEach-Object {
        Write-Host "  • $($_.Description)" -ForegroundColor Red
        Write-Host "    URL: $($_.URL)" -ForegroundColor Gray
        if ($_.Error) {
            Write-Host "    Error: $($_.Error)" -ForegroundColor Yellow
        }
        if ($_.StatusCode) {
            Write-Host "    Status: $($_.StatusCode) (Expected: $($_.Expected))" -ForegroundColor Yellow
        }
        Write-Host ""
    }
}

# Export results to file
$results | Export-Csv -Path "test-results.csv" -NoTypeInformation
Write-Host "Results exported to: test-results.csv" -ForegroundColor Cyan
Write-Host ""

# Exit with error code if any tests failed
if ($failed -gt 0) {
    exit 1
} else {
    Write-Host "ALL TESTS PASSED!" -ForegroundColor Green
    exit 0
}

