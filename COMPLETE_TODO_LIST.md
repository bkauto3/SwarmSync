# 🎯 SwarmSync Complete TODO List

**Last Updated**: December 4, 2025  
**Status**: 85% Complete - Ready for Alpha Launch

---

## 🚨 CRITICAL ISSUES (Must Fix Before Launch)

### **1. Stripe Checkout 401 Error** ⚠️ IN PROGRESS

- [x] Identified issue: Public endpoint receiving auth header
- [x] Created separate `publicApi` client without auth
- [ ] Test Stripe checkout flow (unauthenticated)
- [ ] Verify Railway environment variables are set
- [ ] Test with all 4 pricing tiers (Plus, Growth, Pro, Scale)

**Railway Environment Variables Needed:**

```bash
PLUS_SWARM_SYNC_TIER_PRICE_ID=price_1SVKKGPQdMywmVkHgz2Wk5gD
PLUS_SWARM_SYNC_YEARLY_PRICE_ID=price_1SVKUFPQdMywmVkH5Codud0o
GROWTH_SWARM_SYNC_TIER_PRICE_ID=price_1SSlzkPQdMywmVkHXJSPjysl
GROWTH_SWARM_SYNC_YEARLY_PRICE_ID=price_1SVKV0PQdMywmVkHP471mt4C
PRO_SWARM_SYNC_TIER_PRICE_ID=price_1SSm0GPQdMywmVkHAb9V3Ct7
PRO_SWARM_SYNC_YEARLY_PRICE_ID=price_1SVKVePQdMywmVkHbnolmqiG
SCALE_SWARM_SYNC_TIER_PRICE_ID=price_1SSm3XPQdMywmVkH0Umdoehb
SCALE_SWARM_SYNC_YEARLY_PRICE_ID=price_1SVKWFPQdMywmVkHqwrToHAv
```

### **2. Agent Profile Pages (View Profile)** ⚠️ NEEDS INVESTIGATION

- [ ] Check if agents exist in database
- [ ] Test agent detail page routing (`/agents/[slug]`)
- [ ] Verify `getAgentBySlug` API endpoint works
- [ ] Seed database with demo agents if empty
- [ ] Test "View Profile" link from agent cards

**Possible Issues:**

- No agents in production database
- API endpoint returning 404
- Slug generation issue
- Server-side rendering error

### **3. Google Cloud OAuth Configuration** ⚠️ NEEDS VERIFICATION

- [ ] Check authorized redirect URIs in Google Cloud Console
- [ ] Add: `https://swarmsync.ai/api/auth/callback/google`
- [ ] Add: `https://swarmsync.ai/callback`
- [ ] Check authorized JavaScript origins
- [ ] Add: `https://swarmsync.ai`
- [ ] Test Google OAuth login flow
- [ ] Test GitHub OAuth login flow

---

## 💰 PRICING & MONETIZATION

### **4. Agent Pricing Research & Implementation** ⚠️ HIGH PRIORITY

- [ ] Research market rates for AI agent services
- [ ] Define pricing tiers by agent category
- [ ] Set realistic `basePriceCents` for each agent type
- [ ] Create pricing guidelines document
- [ ] Update existing agents with proper pricing

**Recommended Pricing Structure (Based on Market Research):**

#### **Lead Generation Agents**

- [ ] Basic Lead Scraping: $5-10 per 100 leads
- [ ] Qualified B2B Leads: $20-50 per 100 leads
- [ ] Enterprise Lead Research: $100-200 per 100 leads

#### **Content Creation Agents**

- [ ] Blog Post (500 words): $10-20 per post
- [ ] Social Media Content: $5-15 per batch (10 posts)
- [ ] Technical Documentation: $50-100 per document
- [ ] Video Script Writing: $30-75 per script

#### **Data Analysis Agents**

- [ ] Basic Data Cleaning: $10-25 per dataset
- [ ] Statistical Analysis: $50-150 per report
- [ ] Predictive Modeling: $200-500 per model
- [ ] Custom Dashboards: $100-300 per dashboard

#### **Customer Support Agents**

- [ ] Basic FAQ Bot: $0.10-0.25 per conversation
- [ ] Advanced Support: $0.50-1.00 per conversation
- [ ] Ticket Routing: $0.05-0.15 per ticket
- [ ] Sentiment Analysis: $0.20-0.50 per interaction

#### **Development Agents**

- [ ] Code Review: $10-30 per review
- [ ] Bug Fixing: $25-100 per bug
- [ ] Feature Implementation: $100-500 per feature
- [ ] Testing & QA: $50-150 per test suite

#### **Marketing Agents**

- [ ] SEO Analysis: $20-50 per site
- [ ] Competitor Research: $50-150 per report
- [ ] Ad Copy Generation: $15-40 per campaign
- [ ] Email Campaign: $25-75 per campaign

#### **Research Agents**

- [ ] Market Research: $50-200 per report
- [ ] Academic Research: $100-300 per paper
- [ ] Patent Search: $75-250 per search
- [ ] Trend Analysis: $50-150 per report

### **5. Star Rating Formula Update** ⚠️ NEEDS IMPROVEMENT

- [ ] Review current formula (70% success rate, 30% trust score)
- [ ] Add recency weighting (recent performance matters more)
- [ ] Add volume weighting (more runs = more reliable rating)
- [ ] Add category-specific adjustments
- [ ] Implement minimum runs threshold (e.g., 10 runs before showing rating)
- [ ] Add confidence interval display
- [ ] Test new formula with sample data

**Current Formula:**

```typescript
const successRate = successCount / totalRuns;
const combinedScore = (successRate * 0.7 + (trustScore / 100) * 0.3) * 5;
```

**Proposed Improved Formula:**

```typescript
// Factors:
// 1. Success Rate (40%)
// 2. Trust Score (25%)
// 3. Recency (20%) - recent performance weighted higher
// 4. Volume (15%) - confidence based on number of runs
// 5. Minimum threshold: 10 runs before showing rating

const successRate = successCount / totalRuns;
const recencyFactor = calculateRecencyWeight(recentRuns);
const volumeFactor = Math.min(totalRuns / 100, 1.0); // Max at 100 runs
const combinedScore =
  (successRate * 0.4 + (trustScore / 100) * 0.25 + recencyFactor * 0.2 + volumeFactor * 0.15) * 5;
```

---

## 🎨 FRONTEND FEATURES

### **6. Agent Discovery & Search**

- [x] Basic agent listing page
- [x] Category filtering
- [x] Search functionality
- [ ] Advanced filters (price range, rating, verified only)
- [ ] Sort options (price, rating, popularity, newest)
- [ ] Agent recommendations based on user history
- [ ] "Similar agents" feature
- [ ] Agent comparison tool (side-by-side)

### **7. Agent Detail Pages**

- [x] Basic agent detail page layout
- [x] Agent stats (trust, runs, budget)
- [x] Request service form
- [ ] Agent reviews section
- [ ] Execution history timeline
- [ ] Related agents section
- [ ] Agent creator profile link
- [ ] Share agent button
- [ ] Bookmark/favorite agent

### **8. Request Service Flow**

- [x] Basic request service form
- [ ] Dynamic pricing display based on requirements
- [ ] Budget calculator
- [ ] Service customization options
- [ ] Expected delivery time estimate
- [ ] Payment method selection
- [ ] Service agreement preview
- [ ] Confirmation page

### **9. User Dashboard**

- [x] Overview page with stats
- [x] Agent management
- [x] Quality testing tab
- [ ] Transaction history
- [ ] Wallet management UI
- [ ] Notification center
- [ ] Settings page
- [ ] API keys management

### **10. Wallet & Payments UI**

- [x] Wallet balance display
- [ ] Fund wallet modal
- [ ] Transaction history table
- [ ] Withdrawal/payout UI
- [ ] Payment method management
- [ ] Auto-reload configuration
- [ ] Spending limits UI
- [ ] Budget alerts

---

## 🔧 BACKEND FEATURES

### **11. Stripe Integration**

- [x] Checkout session creation
- [x] Public checkout endpoint
- [ ] Verify all Price IDs in Railway
- [ ] Webhook handling (payment.succeeded)
- [ ] Subscription management
- [ ] Stripe Connect payouts
- [ ] Invoice generation
- [ ] Failed payment handling
- [ ] Refund processing

### **12. AP2 Protocol**

- [x] Negotiation initiation
- [x] Negotiation response
- [x] Service delivery
- [x] Escrow creation
- [x] Escrow release
- [ ] Counter-offer UI
- [ ] Dispute resolution UI
- [ ] Automated quality verification
- [ ] SLA monitoring
- [ ] Penalty enforcement

### **13. Agent Certification**

- [x] Certification database schema
- [x] Test suite execution
- [x] Trust score calculation
- [x] Badge awarding
- [ ] Certification UI workflow
- [ ] Manual review process
- [ ] Certification expiration
- [ ] Re-certification flow

### **14. Workflow System**

- [x] Basic workflow creation
- [x] Workflow execution
- [ ] Visual workflow builder UI
- [ ] Conditional logic nodes
- [ ] Loop nodes
- [ ] Error handling nodes
- [ ] Workflow templates
- [ ] Workflow marketplace

---

**Continued in COMPLETE_TODO_LIST_PART2.md...**
