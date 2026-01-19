#!/bin/bash

# Deployment script for critical bug fixes
# Date: December 4, 2025

echo "🚀 Deploying Critical Bug Fixes to SwarmSync.ai"
echo "================================================"
echo ""

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Not in project root directory"
    exit 1
fi

echo "📝 Changes to be deployed:"
echo "  1. Fixed API URL configuration (View Profile links)"
echo "  2. Added Stripe Price IDs for all plans"
echo "  3. Created public Stripe checkout endpoint"
echo "  4. Updated checkout button to work without authentication"
echo ""

# Stage all changes
echo "📦 Staging changes..."
git add apps/api/.env
git add apps/api/src/modules/billing/billing.controller.ts
git add apps/api/src/modules/billing/billing.service.ts
git add apps/web/.env.local
git add apps/web/src/lib/api.ts
git add apps/web/src/components/pricing/checkout-button.tsx
git add apps/web/src/app/pricing/page.tsx

echo "✅ Changes staged"
echo ""

# Show what will be committed
echo "📋 Files to be committed:"
git status --short
echo ""

# Commit changes
echo "💾 Committing changes..."
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

echo "✅ Changes committed"
echo ""

# Push to main
echo "🚢 Pushing to main branch..."
git push origin main

echo "✅ Pushed to GitHub"
echo ""

echo "🎉 Deployment Complete!"
echo ""
echo "📋 Next Steps:"
echo "  1. Verify Railway environment variables are set (see STRIPE_CHECKOUT_FIX.md)"
echo "  2. Wait for Railway auto-deploy to complete (~2-3 minutes)"
echo "  3. Wait for Netlify auto-deploy to complete (~2-3 minutes)"
echo "  4. Test on https://swarmsync.ai/pricing"
echo ""
echo "🔍 Testing Instructions:"
echo "  1. Open incognito window"
echo "  2. Visit https://swarmsync.ai/pricing"
echo "  3. Click 'Checkout with Stripe' on any plan"
echo "  4. Should redirect to Stripe checkout (NOT login page)"
echo ""
echo "📚 Documentation:"
echo "  - STRIPE_CHECKOUT_FIX.md - Complete fix documentation"
echo "  - DEPLOYMENT_GUIDE.md - Deployment instructions"
echo "  - CRITICAL_BUGS_FIXED.md - Bug analysis and solutions"
echo ""

