# PowerShell script to update Railway DATABASE_URL
# This ensures Railway API connects to the correct Neon database with seeded agents

Write-Host "🔧 Railway Database Connection Updater" -ForegroundColor Cyan
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
    Write-Host "Or update DATABASE_URL manually in Railway dashboard:" -ForegroundColor Yellow
    Write-Host "  https://railway.app → Your Project → Variables" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host "✅ Railway CLI found" -ForegroundColor Green
Write-Host ""

# Prompt for Neon connection string
Write-Host "📋 Please provide your Neon database connection string" -ForegroundColor Yellow
Write-Host ""
Write-Host "To get this:" -ForegroundColor White
Write-Host "  1. Go to: https://console.neon.tech/app/projects/still-wind-09552467" -ForegroundColor White
Write-Host "  2. Select branch: br-bold-sun-ae1ajiqu" -ForegroundColor White
Write-Host "  3. Click 'Connection Details'" -ForegroundColor White
Write-Host "  4. Copy the connection string" -ForegroundColor White
Write-Host ""
Write-Host "Example format:" -ForegroundColor Gray
Write-Host "  postgresql://user:password@ep-bold-sun-xxxxx.us-east-2.aws.neon.tech/neondb?sslmode=require" -ForegroundColor Gray
Write-Host ""

$databaseUrl = Read-Host "Enter DATABASE_URL"

if ([string]::IsNullOrWhiteSpace($databaseUrl)) {
    Write-Host "❌ No DATABASE_URL provided. Exiting." -ForegroundColor Red
    exit 1
}

# Validate connection string format
if (-not $databaseUrl.StartsWith("postgresql://")) {
    Write-Host "⚠️  Warning: Connection string should start with 'postgresql://'" -ForegroundColor Yellow
}

if (-not $databaseUrl.Contains("sslmode=require")) {
    Write-Host "⚠️  Warning: Connection string should include '?sslmode=require'" -ForegroundColor Yellow
    $addSsl = Read-Host "Add '?sslmode=require' to the end? (y/n)"
    if ($addSsl -eq "y") {
        if ($databaseUrl.Contains("?")) {
            $databaseUrl += "&sslmode=require"
        } else {
            $databaseUrl += "?sslmode=require"
        }
    }
}

Write-Host ""
Write-Host "🔗 Linking to Railway project..." -ForegroundColor Yellow
railway link

Write-Host ""
Write-Host "📝 Updating DATABASE_URL in Railway..." -ForegroundColor Yellow
railway variables set "DATABASE_URL=$databaseUrl"

Write-Host ""
Write-Host "✅ DATABASE_URL updated successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "🚢 Railway will automatically redeploy your API service" -ForegroundColor Cyan
Write-Host "⏱️  This usually takes 2-3 minutes" -ForegroundColor Cyan
Write-Host ""

# Wait a moment
Start-Sleep -Seconds 3

Write-Host "🧪 Testing connection in 30 seconds..." -ForegroundColor Yellow
Write-Host "   (Waiting for Railway to redeploy)" -ForegroundColor Gray
Write-Host ""

# Countdown
for ($i = 30; $i -gt 0; $i--) {
    Write-Host "`r   Waiting: $i seconds..." -NoNewline -ForegroundColor Gray
    Start-Sleep -Seconds 1
}
Write-Host ""
Write-Host ""

# Test the API endpoint
Write-Host "🔍 Testing API endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "https://swarmsync-api.up.railway.app/agents" -Method GET -ErrorAction Stop
    $agents = $response.Content | ConvertFrom-Json
    
    if ($agents.Count -gt 0) {
        Write-Host "✅ SUCCESS! Found $($agents.Count) agents in database" -ForegroundColor Green
        Write-Host ""
        Write-Host "📊 Sample agents:" -ForegroundColor Cyan
        $agents | Select-Object -First 5 | ForEach-Object {
            Write-Host "  - $($_.name) ($($_.slug))" -ForegroundColor White
        }
        Write-Host ""
        Write-Host "🎉 Database connection is working correctly!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  API returned empty array" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Possible issues:" -ForegroundColor Yellow
        Write-Host "  1. Agents not seeded in this database" -ForegroundColor White
        Write-Host "  2. Wrong database branch selected" -ForegroundColor White
        Write-Host "  3. Railway still deploying (wait 2 more minutes)" -ForegroundColor White
        Write-Host ""
        Write-Host "To seed agents, run:" -ForegroundColor Yellow
        Write-Host "  railway run npm run seed:agents" -ForegroundColor White
    }
} catch {
    Write-Host "❌ Error testing API endpoint" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possible issues:" -ForegroundColor Yellow
    Write-Host "  1. Railway still deploying (wait 2 more minutes)" -ForegroundColor White
    Write-Host "  2. Database connection error" -ForegroundColor White
    Write-Host "  3. API service not running" -ForegroundColor White
    Write-Host ""
    Write-Host "Check Railway logs:" -ForegroundColor Yellow
    Write-Host "  railway logs" -ForegroundColor White
}

Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Visit https://swarmsync.ai/agents" -ForegroundColor White
Write-Host "  2. Should see list of agents" -ForegroundColor White
Write-Host "  3. Click 'View Profile' on any agent" -ForegroundColor White
Write-Host "  4. Should load agent detail page (no 404)" -ForegroundColor White
Write-Host ""
Write-Host "📚 For more help, see:" -ForegroundColor Yellow
Write-Host "  - verify-database-connection.md" -ForegroundColor White
Write-Host "  - IMMEDIATE_FIXES_GUIDE.md" -ForegroundColor White
Write-Host ""

