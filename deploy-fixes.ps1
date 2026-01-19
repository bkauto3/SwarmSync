# Deployment script for critical bug fixes
# Date: December 4, 2025

Write-Host "🚀 Deploying Critical Bug Fixes to SwarmSync.ai" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "package.json")) {
    Write-Host "❌ Error: Not in project root directory" -ForegroundColor Red
    exit 1
}

Write-Host "📝 Changes to be deployed:" -ForegroundColor Yellow
Write-Host "  1. Fixed API URL configuration (View Profile links)"
Write-Host "  2. Added Stripe Price IDs for all plans"
Write-Host "  3. Created public Stripe checkout endpoint"
Write-Host "  4. Updated checkout button to work without authentication"
Write-Host ""

# Stage all changes
Write-Host "📦 Staging changes..." -ForegroundColor Yellow
git add apps/api/.env
git add apps/api/src/modules/billing/billing.controller.ts
git add apps/api/src/modules/billing/billing.service.ts
git add apps/web/.env.local
git add apps/web/src/lib/api.ts
git add apps/web/src/components/pricing/checkout-button.tsx
git add apps/web/src/app/pricing/page.tsx

Write-Host "✅ Changes staged" -ForegroundColor Green
Write-Host ""

# Show what will be committed
Write-Host "📋 Files to be committed:" -ForegroundColor Yellow
git status --short
Write-Host ""

# Commit changes
Write-Host "💾 Committing changes..." -ForegroundColor Yellow
git commit -m "fix: Critical bug fixes - View Profile links and Stripe checkout

- Fixed API URL configuration to use correct Railway backend
- Added all Stripe Price IDs (monthly and yearly plans)
- Created public checkout endpoint for unauthenticated users
- Updated CheckoutButton to use public checkout when not logged in
- Removed test Stripe links from pricing page

Fixes:
1. View Profile links now work correctly
2. Stripe checkout works for both authenticated and unauthenticated users
3. All pricing plans have correct Stripe Price IDs configured"

Write-Host "✅ Changes committed" -ForegroundColor Green
Write-Host ""

# Push to main
Write-Host "🚢 Pushing to main branch..." -ForegroundColor Yellow
git push origin main

Write-Host "✅ Pushed to GitHub" -ForegroundColor Green
Write-Host ""

Write-Host "🎉 Deployment Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Verify Railway environment variables are set (see STRIPE_CHECKOUT_FIX.md)"
Write-Host "  2. Wait for Railway auto-deploy to complete (~2-3 minutes)"
Write-Host "  3. Wait for Netlify auto-deploy to complete (~2-3 minutes)"
Write-Host "  4. Test on https://swarmsync.ai/pricing"
Write-Host ""
Write-Host "🔍 Testing Instructions:" -ForegroundColor Cyan
Write-Host "  1. Open incognito window"
Write-Host "  2. Visit https://swarmsync.ai/pricing"
Write-Host "  3. Click 'Checkout with Stripe' on any plan"
Write-Host "  4. Should redirect to Stripe checkout (NOT login page)"
Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Cyan
Write-Host "  - STRIPE_CHECKOUT_FIX.md - Complete fix documentation"
Write-Host "  - DEPLOYMENT_GUIDE.md - Deployment instructions"
Write-Host "  - CRITICAL_BUGS_FIXED.md - Bug analysis and solutions"
Write-Host ""

