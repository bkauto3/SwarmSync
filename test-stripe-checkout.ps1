# Test Stripe checkout endpoint

Write-Host "Testing Stripe Checkout Endpoint" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

$apiUrl = "https://swarmsync-api.up.railway.app"
$endpoint = "$apiUrl/billing/subscription/checkout/public"

$plans = @("plus", "growth", "pro", "scale")

foreach ($plan in $plans) {
    Write-Host "Testing $plan plan..." -ForegroundColor Yellow
    
    $body = @{
        planSlug = $plan
        successUrl = "https://swarmsync.ai/success"
        cancelUrl = "https://swarmsync.ai/pricing"
    } | ConvertTo-Json
    
    try {
        $response = Invoke-WebRequest -Uri $endpoint -Method POST -ContentType "application/json" -Body $body -ErrorAction Stop
        
        Write-Host "  Status: $($response.StatusCode)" -ForegroundColor Green
        
        $content = $response.Content | ConvertFrom-Json
        
        if ($content.checkoutUrl) {
            Write-Host "  Checkout URL: $($content.checkoutUrl)" -ForegroundColor Green
            Write-Host "  [PASS] $plan plan checkout works!" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] No checkout URL in response" -ForegroundColor Red
            Write-Host "  Response: $($response.Content)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  [FAIL] Error: $($_.Exception.Message)" -ForegroundColor Red
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode
            Write-Host "  Status Code: $statusCode" -ForegroundColor Red
        }
    }
    
    Write-Host ""
}

Write-Host "Test complete!" -ForegroundColor Cyan

