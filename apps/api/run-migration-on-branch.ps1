# PowerShell script to run migration on a Neon branch
# Usage: .\run-migration-on-branch.ps1 "your-branch-connection-string"

param(
    [Parameter(Mandatory=$true)]
    [string]$BranchDatabaseUrl
)

Write-Host "🚀 Running migration on Neon branch..." -ForegroundColor Cyan
Write-Host ""

# Check if DATABASE_URL is set
if (-not $BranchDatabaseUrl) {
    Write-Host "❌ Error: Branch connection string is required" -ForegroundColor Red
    Write-Host "Usage: .\run-migration-on-branch.ps1 'postgresql://user:pass@host/db?sslmode=require'" -ForegroundColor Yellow
    exit 1
}

# Clean up the connection string - remove 'psql' prefix if present and fix quotes
$cleanUrl = $BranchDatabaseUrl.Trim()
$cleanUrl = $cleanUrl -replace "^psql\s+['`"]?", ""
$cleanUrl = $cleanUrl -replace "['`"]$", ""
$cleanUrl = $cleanUrl.Trim()

# Ensure it starts with postgresql://
if (-not $cleanUrl.StartsWith("postgresql://") -and -not $cleanUrl.StartsWith("postgres://")) {
    Write-Host "❌ Error: Connection string must start with postgresql:// or postgres://" -ForegroundColor Red
    Write-Host "Received: $cleanUrl" -ForegroundColor Yellow
    exit 1
}

Write-Host "📋 Cleaned connection string: $($cleanUrl.Substring(0, [Math]::Min(50, $cleanUrl.Length)))..." -ForegroundColor Gray
Write-Host ""

# Set the DATABASE_URL environment variable
$env:DATABASE_URL = $cleanUrl

Write-Host "✅ DATABASE_URL set to branch connection" -ForegroundColor Green
Write-Host ""

# Run the migration
Write-Host "📦 Running Prisma migration..." -ForegroundColor Cyan
npx prisma migrate deploy

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Migration completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Verify tables were created: npx prisma studio" -ForegroundColor Yellow
    Write-Host "2. Update your .env file with the branch DATABASE_URL if you want to use it" -ForegroundColor Yellow
    Write-Host "3. Or merge the branch in Neon Console when ready" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "❌ Migration failed. Check the error above." -ForegroundColor Red
    exit 1
}

