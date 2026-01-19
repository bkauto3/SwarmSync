# 🔍 Database Connection Verification

**Verify Railway is connected to the correct Neon database with seeded agents**

---

## 🎯 Problem

You've seeded agents in Neon database, but the API at `https://swarmsync-api.up.railway.app/agents` returns empty.

**Possible Causes**:

1. Railway is pointing to a different database
2. Railway DATABASE_URL is not set correctly
3. Agents were seeded in a different branch/database

---

## 📊 Your Neon Database Info

Based on the console URL you provided:

- **Project**: `still-wind-09552467`
- **Branch**: `br-bold-sun-ae1ajiqu` (bold-sun)
- **Console**: https://console.neon.tech/app/projects/still-wind-09552467/branches/br-bold-sun-ae1ajiqu/tables

---

## ✅ Step 1: Get Correct Neon Connection String

1. **Go to Neon Console**
   - Visit: https://console.neon.tech/app/projects/still-wind-09552467

2. **Select the Correct Branch**
   - Click on branch: `br-bold-sun-ae1ajiqu` (or "main" if that's where agents are)

3. **Get Connection String**
   - Click "Connection Details" or "Connection String"
   - Copy the connection string (should look like):

   ```
   postgresql://[user]:[password]@[host]/[database]?sslmode=require
   ```

4. **Verify Agents Exist**
   - In Neon Console, go to "Tables" tab
   - Click on "Agent" table
   - Should see 20 agents listed
   - If empty, agents were seeded elsewhere

---

## ✅ Step 2: Update Railway DATABASE_URL

1. **Login to Railway**
   - Go to: https://railway.app
   - Use project token: `c5617b21-1704-46c3-bf94-410d17440c83`

2. **Navigate to API Service**
   - Select your API project (swarmsync-api)
   - Click "Variables" tab

3. **Update DATABASE_URL**
   - Find `DATABASE_URL` variable
   - Replace with the connection string from Neon (Step 1)
   - Should look like:

   ```
   postgresql://neondb_owner:npg_xxxxx@ep-bold-sun-ae1ajiqu.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

4. **Save and Redeploy**
   - Click "Save"
   - Railway will auto-redeploy (~2 minutes)

---

## ✅ Step 3: Verify Connection

After Railway redeploys:

### **Test API Endpoint**

```powershell
# Test agents endpoint
Invoke-WebRequest -Uri "https://swarmsync-api.up.railway.app/agents" -Method GET | Select-Object -ExpandProperty Content | ConvertFrom-Json
```

**Expected Result**: Should return array of 20 agents

### **Test Specific Agent**

```powershell
# Test agent detail endpoint
Invoke-WebRequest -Uri "https://swarmsync-api.up.railway.app/agents/slug/b2b-lead-generator-pro" -Method GET | Select-Object -ExpandProperty Content | ConvertFrom-Json
```

**Expected Result**: Should return agent details

---

## 🔧 Alternative: Seed Agents in Railway Database

If Railway is using a different database and you want to keep it that way:

### **Option A: Run Seed Script via Railway CLI**

```powershell
# Install Railway CLI (if not installed)
npm install -g @railway/cli

# Login to Railway
railway login

# Link to project
railway link

# Run seed script
railway run npm run seed:agents
```

### **Option B: Run Seed Script Locally Against Railway DB**

1. **Get Railway DATABASE_URL**
   - In Railway dashboard → Variables
   - Copy the `DATABASE_URL` value

2. **Update Local .env Temporarily**

   ```bash
   # apps/api/.env
   DATABASE_URL="[paste Railway database URL here]"
   ```

3. **Run Seed Script**

   ```powershell
   cd apps/api
   npm run seed:agents
   ```

4. **Restore Local .env**
   - Change DATABASE_URL back to your local database

---

## 🎯 Recommended Approach

**Use the same Neon database for both local and production:**

1. **Get Neon Connection String** (from console)
2. **Update Railway DATABASE_URL** (to match Neon)
3. **Update Local .env** (to match Neon)
4. **Verify agents exist** (test API endpoint)

**Benefits**:

- ✅ Same data in local and production
- ✅ No need to seed twice
- ✅ Easier debugging
- ✅ Consistent testing

---

## 📋 Checklist

- [ ] Verified agents exist in Neon database (via console)
- [ ] Copied correct Neon connection string
- [ ] Updated Railway DATABASE_URL variable
- [ ] Waited for Railway to redeploy (~2 min)
- [ ] Tested API endpoint: `/agents`
- [ ] Confirmed 20 agents returned
- [ ] Tested agent detail: `/agents/slug/b2b-lead-generator-pro`
- [ ] Tested "View Profile" link on frontend
- [ ] Verified agent page loads (no 404)

---

## 🐛 Troubleshooting

### **API Still Returns Empty Array**

1. **Check Railway Logs**

   ```powershell
   railway logs
   ```

   - Look for database connection errors
   - Look for Prisma errors

2. **Verify DATABASE_URL Format**
   - Must include `?sslmode=require` at the end
   - Must be the full connection string (not just host)
   - No extra spaces or quotes

3. **Check Neon Database**
   - Go to Neon Console → Tables
   - Verify "Agent" table has data
   - Check you're on the correct branch

### **Connection Errors**

If you see "connection refused" or "SSL required":

- Add `?sslmode=require` to connection string
- Verify Neon database is not paused (auto-pauses after inactivity)
- Check Neon IP allowlist (if configured)

### **Prisma Client Errors**

If you see "Prisma Client not generated":

```powershell
# In Railway, this should happen automatically
# But you can force it:
railway run npx prisma generate
```

---

## 📊 Expected Database State

After correct configuration, your Neon database should have:

- **20 Agents** (seeded)
- **1 User** (demo@swarmsync.ai)
- **Agent Categories**:
  - Lead Generation: 2 agents
  - Content Creation: 3 agents
  - Data Analysis: 2 agents
  - Customer Support: 2 agents
  - Development: 2 agents
  - Marketing: 3 agents
  - Research: 2 agents
  - Automation: 2 agents

---

## 🎯 Next Steps After Fix

Once agents are visible:

1. **Test Frontend**
   - Visit: https://swarmsync.ai/agents
   - Should see 20 agents listed
   - Click "View Profile" on any agent
   - Should load agent detail page (no 404)

2. **Test Request Service**
   - On agent detail page
   - Click "Request Service"
   - Should show pricing and form

3. **Update Agent Pricing** (if needed)
   - Some agents may need pricing adjustments
   - See `AGENT_PRICING_GUIDE.md` for recommendations

---

**Questions? See `IMMEDIATE_FIXES_GUIDE.md` for more help.**
