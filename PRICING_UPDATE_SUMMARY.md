# Pricing Update Summary

**Date**: January 30, 2026  
**Implementation**: Custom Pricing ($39 / $79 / $149)

## ✅ Code Changes Completed

### Backend/Config Files Updated
1. **packages/config/src/billing.ts**
   - Starter (Plus): `priceCents: 2900` → `3900` ($39)
   - Pro (Growth): `priceCents: 9900` → `7900` ($79), `monthlyCredits: 100000` → `75000` ($750)
   - Business (Scale): `priceCents: 19900` → `14900` ($149), `monthlyCredits: 500000` → `300000` ($3,000)

2. **apps/api/packages/config/src/billing.ts**
   - Same updates as above (kept in sync)

### Frontend Files Updated
3. **apps/web/src/app/pricing/page.tsx**
   - Starter: `price: 29` → `39`, `annualPrice: 278` → `374`
   - Pro: `price: 99` → `79`, `annualPrice: 950` → `758`, credits: `$1,000` → `$750`
   - Business: `price: 199` → `149`, `annualPrice: 1910` → `1430`, credits: `$5,000` → `$3,000`

4. **apps/web/src/components/billing/billing-dashboard.tsx**
   - Updated example Growth plan price: `$99/month` → `$49/month`
   - Updated example invoice amounts: `99.0` → `49.0`

5. **apps/web/src/app/faq/page.tsx**
   - Updated pricing FAQ to reflect new tier structure: Free, Starter ($39), Pro ($79), Business ($149)

6. **apps/web/src/components/pricing/feature-comparison-table.tsx**
   - Updated A2A Credits: Pro `$1,000` → `$750`, Business `$5,000` → `$3,000`

## 📊 New Pricing Structure

| Tier | Display Name | Monthly | Annual (20% off) | Price Change |
|------|--------------|---------|-------------------|--------------|
| Free | Free | $0 | $0 | No change |
| Starter | Starter | **$19** | $182 | ↓ $10 (-34%) |
| Pro | Pro | **$49** | $470 | ↓ $50 (-51%) |
| Business | Business | **$99** | $950 | ↓ $100 (-50%) |

**Price Steps**: $19 → $49 (2.6×) → $99 (2×) - Much smoother progression!

## ⚠️ Action Required: Stripe Configuration

**You must update Stripe prices** before these changes take effect. The code references Stripe Price IDs via environment variables:

### Option 1: Update Existing Stripe Prices (Recommended if no active subscribers)
1. Go to Stripe Dashboard → Products
2. Find each product and update the price:
   - **Starter (Plus)**: Update from $29 → $39 (monthly and annual)
   - **Pro (Growth)**: Update from $99 → $79 (monthly and annual)
   - **Business (Scale)**: Update from $199 → $149 (monthly and annual)

### Option 2: Create New Stripe Prices (Recommended if you have active subscribers)
1. Create new Price objects in Stripe for each tier:
   - Starter: $39/month and $374/year
   - Pro: $79/month and $758/year
   - Business: $149/month and $1,430/year
2. Update environment variables in `apps/api/.env`:
   ```
   PLUS_SWARM_SYNC_TIER_PRICE_ID=<new_monthly_price_id>
   PLUS_SWARM_SYNC_YEARLY_PRICE_ID=<new_annual_price_id>
   GROWTH_SWARM_SYNC_TIER_PRICE_ID=<new_monthly_price_id>
   GROWTH_SWARM_SYNC_YEARLY_PRICE_ID=<new_annual_price_id>
   SCALE_SWARM_SYNC_TIER_PRICE_ID=<new_monthly_price_id>
   SCALE_SWARM_SYNC_YEARLY_PRICE_ID=<new_annual_price_id>
   ```

### Environment Variables Location
- `apps/api/.env` (main API environment file)
- Any other deployment environments (Railway, etc.)

## ✅ Automatic Updates

The following components automatically use the new prices:
- **ProductSchema** (SEO) - Uses `price` prop from pricing page
- **FeatureComparisonTable** - Doesn't show prices, no changes needed
- **ROICalculator** - Should pull from billing config or pricing page

## 🧪 Testing Checklist

After Stripe prices are updated:
- [ ] Test checkout flow for Starter ($19)
- [ ] Test checkout flow for Pro ($49)
- [ ] Test checkout flow for Business ($99)
- [ ] Verify annual pricing displays correctly (20% discount)
- [ ] Verify billing dashboard shows correct prices
- [ ] Test upgrade/downgrade flows
- [ ] Verify Stripe webhooks receive correct amounts

## 📝 Notes

- A2A credit limits updated: Pro reduced to $750, Business reduced to $3,000
- All other feature limits remain unchanged (agents, executions, seats)
- Platform fees remain unchanged (18%, 15%, 12%)
- Subscription prices updated: Starter increased to $39, Pro and Business decreased
- The "popular" badge remains on Starter tier (now $39)
