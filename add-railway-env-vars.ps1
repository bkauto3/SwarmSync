# PowerShell script to add Stripe Price IDs to Railway
# Run this script to automatically add environment variables to Railway

Write-Host "🚀 Adding Stripe Price IDs to Railway" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# IMPORTANT:
# Railway CLI uses RAILWAY_TOKEN as an *auth token*.
# If you accidentally set it to a UUID (often a project/service id), the CLI will show:
#   "Unauthorized. Please login with `railway login`"
# This script auto-unsets that common misconfiguration so it doesn't keep breaking.
if ($env:RAILWAY_TOKEN -and $env:RAILWAY_TOKEN -match '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$') {
    Write-Host "⚠️  Detected RAILWAY_TOKEN set to a UUID (likely NOT a real Railway auth token). Unsetting it for this run..." -ForegroundColor Yellow
    Remove-Item Env:RAILWAY_TOKEN -ErrorAction SilentlyContinue
    Write-Host "   Tip: Remove the global Windows env var RAILWAY_TOKEN if you set it to a project id." -ForegroundColor Gray
    Write-Host ""
}

# Check if Railway CLI is installed
$railwayInstalled = Get-Command railway -ErrorAction SilentlyContinue

if (-not $railwayInstalled) {
    Write-Host "❌ Railway CLI not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Railway CLI first:" -ForegroundColor Yellow
    Write-Host "  npm install -g @railway/cli" -ForegroundColor White
    Write-Host ""
    Write-Host "Or add variables manually in Railway dashboard:" -ForegroundColor Yellow
    Write-Host "  https://railway.app → Your Project → Variables" -ForegroundColor White
    Write-Host ""
    Write-Host "Variables to add:" -ForegroundColor Yellow
    Write-Host "  PLUS_SWARM_SYNC_TIER_PRICE_ID=price_1SVKKGPQdMywmVkHgz2Wk5gD" -ForegroundColor White
    Write-Host "  PLUS_SWARM_SYNC_YEARLY_PRICE_ID=price_1SVKUFPQdMywmVkH5Codud0o" -ForegroundColor White
    Write-Host "  GROWTH_SWARM_SYNC_TIER_PRICE_ID=price_1SSlzkPQdMywmVkHXJSPjysl" -ForegroundColor White
    Write-Host "  GROWTH_SWARM_SYNC_YEARLY_PRICE_ID=price_1SVKV0PQdMywmVkHP471mt4C" -ForegroundColor White
    Write-Host "  PRO_SWARM_SYNC_TIER_PRICE_ID=price_1SSm0GPQdMywmVkHAb9V3Ct7" -ForegroundColor White
    Write-Host "  PRO_SWARM_SYNC_YEARLY_PRICE_ID=price_1SVKVePQdMywmVkHbnolmqiG" -ForegroundColor White
    Write-Host "  SCALE_SWARM_SYNC_TIER_PRICE_ID=price_1SSm3XPQdMywmVkH0Umdoehb" -ForegroundColor White
    Write-Host "  SCALE_SWARM_SYNC_YEARLY_PRICE_ID=price_1SVKWFPQdMywmVkHqwrToHAv" -ForegroundColor White
    exit 1
}

Write-Host "✅ Railway CLI found" -ForegroundColor Green
Write-Host ""

# Link to Railway project (if not already linked)
Write-Host "🔗 Linking to Railway project..." -ForegroundColor Yellow
railway link

Write-Host ""
Write-Host "📝 Adding Stripe Price ID environment variables..." -ForegroundColor Yellow
Write-Host ""

# Add environment variables
$envVars = @{
    "PLUS_SWARM_SYNC_TIER_PRICE_ID" = "price_1SVKKGPQdMywmVkHgz2Wk5gD"
    "PLUS_SWARM_SYNC_YEARLY_PRICE_ID" = "price_1SVKUFPQdMywmVkH5Codud0o"
    "GROWTH_SWARM_SYNC_TIER_PRICE_ID" = "price_1SSlzkPQdMywmVkHXJSPjysl"
    "GROWTH_SWARM_SYNC_YEARLY_PRICE_ID" = "price_1SVKV0PQdMywmVkHP471mt4C"
    "PRO_SWARM_SYNC_TIER_PRICE_ID" = "price_1SSm0GPQdMywmVkHAb9V3Ct7"
    "PRO_SWARM_SYNC_YEARLY_PRICE_ID" = "price_1SVKVePQdMywmVkHbnolmqiG"
    "SCALE_SWARM_SYNC_TIER_PRICE_ID" = "price_1SSm3XPQdMywmVkH0Umdoehb"
    "SCALE_SWARM_SYNC_YEARLY_PRICE_ID" = "price_1SVKWFPQdMywmVkHqwrToHAv"
}

foreach ($key in $envVars.Keys) {
    $value = $envVars[$key]
    Write-Host "  Adding $key..." -ForegroundColor White
    railway variables set "$key=$value"
}

Write-Host ""
Write-Host "✅ All environment variables added!" -ForegroundColor Green
Write-Host ""
Write-Host "🚢 Railway will automatically redeploy your API service" -ForegroundColor Cyan
Write-Host "⏱️  This usually takes 2-3 minutes" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Wait for Railway deployment to complete" -ForegroundColor White
Write-Host "  2. Visit https://swarmsync.ai/pricing" -ForegroundColor White
Write-Host "  3. Click 'Checkout with Stripe' on any plan" -ForegroundColor White
Write-Host "  4. Should redirect to Stripe checkout (NOT 500 error)" -ForegroundColor White
Write-Host ""
Write-Host "🔍 Monitor deployment:" -ForegroundColor Yellow
Write-Host "  railway logs" -ForegroundColor White
Write-Host ""

