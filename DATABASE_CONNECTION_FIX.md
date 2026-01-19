# 🔧 Database Connection Fix - Quick Guide

**Fix: Railway API not showing seeded agents from Neon database**

---

## 🎯 Problem

- ✅ Agents are seeded in Neon database
- ❌ API endpoint returns empty: `https://swarmsync-api.up.railway.app/agents`
- ❌ "View Profile" links return 404

**Root Cause**: Railway is pointing to a different database than where agents are seeded.

---

## ✅ Solution (2 Options)

### **Option 1: Update Railway to Use Neon Database** (RECOMMENDED)

This ensures Railway uses the same database where you seeded agents.

#### **Quick Method (5 minutes)**

1. **Get Neon Connection String**
   - Go to: https://console.neon.tech/app/projects/still-wind-09552467
   - Select branch: `br-bold-sun-ae1ajiqu`
   - Click "Connection Details"
   - Copy the connection string (looks like):

   ```
   postgresql://neondb_owner:npg_xxxxx@ep-bold-sun-ae1ajiqu.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

2. **Update Railway DATABASE_URL**
   - Go to: https://railway.app
   - Login with token: `c5617b21-1704-46c3-bf94-410d17440c83`
   - Select API service → Variables tab
   - Find `DATABASE_URL` variable
   - Replace with Neon connection string from step 1
   - Click "Save"

3. **Wait for Redeploy**
   - Railway auto-redeploys (~2 minutes)
   - Watch deployment progress in Railway dashboard

4. **Test**
   ```powershell
   Invoke-WebRequest -Uri "https://swarmsync-api.up.railway.app/agents" | Select-Object -ExpandProperty Content | ConvertFrom-Json
   ```

   - Should return 20 agents

#### **Automated Method (Using Script)**

```powershell
# Run the PowerShell script
.\update-railway-database.ps1
```

This script will:

- ✅ Prompt for Neon connection string
- ✅ Update Railway DATABASE_URL
- ✅ Wait for deployment
- ✅ Test the connection
- ✅ Show results

---

### **Option 2: Seed Agents in Railway's Database**

If Railway is using a different database and you want to keep it that way.

#### **Method A: Via Railway CLI**

```powershell
# Install Railway CLI (if not installed)
npm install -g @railway/cli

# Login and link to project
railway login
railway link

# Run seed script
railway run npm run seed:agents
```

#### **Method B: Manually via Local Script**

1. **Get Railway DATABASE_URL**
   - Railway dashboard → Variables
   - Copy `DATABASE_URL` value

2. **Update Local .env Temporarily**

   ```bash
   # apps/api/.env
   DATABASE_URL="[paste Railway database URL]"
   ```

3. **Run Seed Script**

   ```powershell
   cd apps/api
   npm run seed:agents
   ```

4. **Restore Local .env**
   - Change back to your local database URL

---

## 🧪 Verification Steps

After updating the database connection:

### **1. Test API Endpoint**

```powershell
# Should return array of 20 agents
Invoke-WebRequest -Uri "https://swarmsync-api.up.railway.app/agents" -Method GET | Select-Object -ExpandProperty Content | ConvertFrom-Json
```

### **2. Test Specific Agent**

```powershell
# Should return agent details
Invoke-WebRequest -Uri "https://swarmsync-api.up.railway.app/agents/slug/b2b-lead-generator-pro" -Method GET | Select-Object -ExpandProperty Content | ConvertFrom-Json
```

### **3. Test Frontend**

- Visit: https://swarmsync.ai/agents
- Should see 20 agents listed
- Click "View Profile" on any agent
- Should load agent detail page (NOT 404)

---

## 📊 Expected Results

After fix, you should have:

**API Response** (`/agents`):

```json
[
  {
    "id": "...",
    "name": "B2B Lead Generator Pro",
    "slug": "b2b-lead-generator-pro",
    "description": "Generates qualified B2B leads...",
    "basePriceCents": 3500,
    "trustScore": 85,
    "successCount": 142,
    "categories": ["lead-generation", "sales"],
    ...
  },
  // ... 19 more agents
]
```

**Agent Categories**:

- Lead Generation: 2 agents
- Content Creation: 3 agents
- Data Analysis: 2 agents
- Customer Support: 2 agents
- Development: 2 agents
- Marketing: 3 agents
- Research: 2 agents
- Automation: 2 agents

**Total**: 20 agents

---

## 🐛 Troubleshooting

### **Still Getting Empty Array?**

1. **Check Railway Logs**

   ```powershell
   railway logs
   ```

   - Look for database connection errors
   - Look for Prisma errors

2. **Verify Neon Database**
   - Go to Neon Console → Tables
   - Click "Agent" table
   - Should see 20 rows
   - If empty, agents weren't seeded here

3. **Check DATABASE_URL Format**
   - Must start with `postgresql://`
   - Must include `?sslmode=require`
   - No extra spaces or quotes

### **Connection Errors?**

- Verify Neon database is not paused (auto-pauses after inactivity)
- Check connection string is complete
- Ensure `?sslmode=require` is at the end

### **Prisma Errors?**

```powershell
# Regenerate Prisma client in Railway
railway run npx prisma generate
```

---

## 📋 Checklist

- [ ] Got Neon connection string from console
- [ ] Updated Railway DATABASE_URL variable
- [ ] Waited for Railway to redeploy (~2 min)
- [ ] Tested `/agents` endpoint
- [ ] Confirmed 20 agents returned
- [ ] Tested `/agents/slug/b2b-lead-generator-pro`
- [ ] Visited https://swarmsync.ai/agents
- [ ] Clicked "View Profile" on an agent
- [ ] Agent detail page loaded (no 404)

---

## 🎯 Next Steps After Fix

Once agents are visible:

1. **Test All Critical Flows**
   - Agent listing page
   - Agent detail pages
   - Request service functionality
   - Stripe checkout

2. **Update Agent Pricing** (if needed)
   - See `AGENT_PRICING_GUIDE.md`
   - Adjust `basePriceCents` for each agent

3. **Implement Star Rating Formula**
   - See `IMPROVED_RATING_FORMULA.md`
   - Update rating calculation

4. **Configure OAuth**
   - See `GOOGLE_OAUTH_CONFIGURATION.md`
   - Update redirect URIs

---

## 📚 Related Documentation

- `verify-database-connection.md` - Detailed verification guide
- `IMMEDIATE_FIXES_GUIDE.md` - All critical fixes
- `FIXES_SUMMARY.md` - Summary of all fixes
- `COMPLETE_TODO_LIST.md` - All remaining tasks

---

**Estimated Time**: 5-10 minutes  
**Difficulty**: Easy  
**Impact**: HIGH - Fixes agent profile 404 errors

---

**Questions? Run the automated script: `.\update-railway-database.ps1`**
