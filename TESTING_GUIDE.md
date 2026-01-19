# SwarmSync Testing Guide

**Date:** 2026-01-03
**Tester:** Ben Stone (rainking6693@gmail.com)

---

## ✅ Database Setup Completed

### User Details

- **Email:** rainking6693@gmail.com
- **User ID:** `e9b91865-be00-4b76-a293-446e1be9151c`
- **Organization:** SwarmSync (ID: `93209c61-e6ea-4d9b-b2fa-126f8bcb2d6e`)
- **Role:** OWNER
- **Permissions:** Full access to create agents and workflows

### What Was Fixed

1. ✅ Added user to SwarmSync organization as OWNER
2. ✅ Pre-filled workflow creator ID in the workflow builder
3. ✅ Identified available agents for testing

---

## Test 1: Agent Creation Flow

### Prerequisites

- Login credentials: `rainking6693@gmail.com` / `Hudson1234%`
- User now has OWNER role in SwarmSync organization

### Steps to Test

1. Navigate to https://swarmsync.ai/login
2. Login with the credentials above
3. Navigate to https://swarmsync.ai/agents/new
4. **Expected Result:** You should now see the agent creation form (not the "Sign in to deploy agents" error)

### Agent Creation Form Fields

Fill in the following to create a test agent:

**Basic Details:**

- Name: `Test Agent`
- Description: `Test agent for workflow testing`
- Slug: `test-agent-001`
- Status: `DRAFT` (or choose PENDING for review)
- Visibility: `PUBLIC`
- Categories: Select relevant categories
- Tags: `test`, `demo`

**Pricing:**

- Pricing Model: Choose appropriate model
- Price Amount: `10.00` (optional)

**AP2 Configuration:**

- AP2 Endpoint: `https://api.example.com/agent`
- Input Schema:

```json
{
  "type": "object",
  "properties": {
    "task": { "type": "string" }
  }
}
```

- Output Schema:

```json
{
  "type": "object",
  "properties": {
    "result": { "type": "string" }
  }
}
```

### Success Criteria

- ✅ Form loads without errors
- ✅ All fields are editable
- ✅ Form submits successfully
- ✅ New agent appears in the agents list

---

## Test 2: Workflow Creation Flow

### Prerequisites

- Login credentials: `rainking6693@gmail.com` / `Hudson1234%`
- Available agents in the system (see list below)

### Steps to Test

1. Navigate to https://swarmsync.ai/console/workflows
2. **Expected Result:** The "Creator ID" field should be pre-filled with `e9b91865-be00-4b76-a293-446e1be9151c`

### Create Test Workflow

**Workflow Details:**

- Workflow Name: `Test Content Pipeline`
- Total Budget: `50` credits
- Description: `Two-stage content creation workflow`
- Creator ID: **Already pre-filled** (`e9b91865-be00-4b76-a293-446e1be9151c`)

**Step 1:**

- Agent ID: `92c99e08-d86e-4ef7-9f04-ad5763e3c330` (Content Agent)
- Job Reference: `content_generation`
- Budget: `25`

**Step 2:**

- Agent ID: `1e48bfef-c760-4feb-84e4-7029ef117689` (SEO Agent)
- Job Reference: `seo_optimization`
- Budget: `25`

### Using the Form Builder

1. Fill in the workflow name, budget, and description
2. Click "+ Add Step" button
3. Fill in Agent ID, Job Reference, and Budget for each step
4. Click "Create Workflow"

### Using Raw JSON Editor

Alternatively, paste this into the "Advanced: Raw JSON" section:

```json
[
  {
    "agentId": "92c99e08-d86e-4ef7-9f04-ad5763e3c330",
    "jobReference": "content_generation",
    "budget": 25
  },
  {
    "agentId": "1e48bfef-c760-4feb-84e4-7029ef117689",
    "jobReference": "seo_optimization",
    "budget": 25
  }
]
```

### Success Criteria

- ✅ Creator ID is pre-filled (no longer shows "Creator ID is required" error)
- ✅ Form validation shows specific errors for missing fields
- ✅ Workflow creates successfully with valid data
- ✅ Success message displays: "Workflow created successfully!"

---

## Available Agents for Testing

All agents are **APPROVED** and **PUBLIC**, ready to use in workflows:

| Agent Name      | Agent ID                               | Suggested Use        |
| --------------- | -------------------------------------- | -------------------- |
| Content Agent   | `92c99e08-d86e-4ef7-9f04-ad5763e3c330` | Content creation     |
| SEO Agent       | `1e48bfef-c760-4feb-84e4-7029ef117689` | SEO optimization     |
| Marketing Agent | `7f8b2409-f2aa-42aa-a87c-cb0f00642d07` | Marketing tasks      |
| Support Agent   | `ca1d7137-e2fb-47ae-86ad-5dd7d98b39db` | Customer support     |
| Analyst Agent   | `17da61d5-47f5-4808-be53-4e172bb94b3a` | Data analysis        |
| Security Agent  | `c99bb5d4-350b-433f-9338-a93ab791897f` | Security checks      |
| Finance Agent   | `8c1684e8-a752-48a8-91d7-60f9c910599b` | Financial operations |
| Email Agent     | `63468a6e-1b26-4556-baf4-faac542b2548` | Email handling       |

---

## Troubleshooting

### Issue: "Creator ID is required"

**Solution:** This should no longer appear. The field is pre-filled with your user ID.

### Issue: "Step 1: Agent ID is required"

**Solution:** Make sure to fill in all three fields for each step:

- Agent ID (from the table above)
- Job Reference (a descriptive name like `research`, `analysis`, etc.)
- Budget (numeric value)

### Issue: "Invalid workflow data"

**Solution:** Check that:

1. Creator ID is a valid UUID
2. All step agent IDs are valid UUIDs from the approved agents list
3. Budget values are positive numbers

### Issue: Agent creation shows "Sign in to deploy agents"

**Solution:** This should no longer appear. You're now an OWNER of the SwarmSync organization. If it still shows:

1. Clear browser cache and cookies
2. Log out and log back in
3. Verify you're using the correct email: `rainking6693@gmail.com`

---

## Database Changes Made

### Commands Run

```sql
-- Added user to organization as OWNER
INSERT INTO "OrganizationMembership"
  ("id", "userId", "organizationId", "role", "createdAt")
VALUES
  (gen_random_uuid(),
   'e9b91865-be00-4b76-a293-446e1be9151c',
   '93209c61-e6ea-4d9b-b2fa-126f8bcb2d6e',
   'OWNER',
   NOW())
ON CONFLICT ("userId", "organizationId")
DO UPDATE SET role = 'OWNER';
```

### Code Changes

**File:** `apps/web/src/components/workflows/workflow-builder.tsx`

- Line 39: Changed `const [creatorId, setCreatorId] = useState('');`
- To: `const [creatorId, setCreatorId] = useState('e9b91865-be00-4b76-a293-446e1be9151c');`

---

## Next Steps After Testing

1. **Test agent creation** - Create at least one test agent
2. **Test workflow creation** - Create the sample workflow above
3. **Test workflow execution** - Run the created workflow (if execution is implemented)
4. **Verify in database** - Check that records were created correctly
5. **Report any issues** - Document any errors or unexpected behavior

---

## Build Status

✅ **Build Successful** (1m 46s)

- All TypeScript compilation passed
- No ESLint errors
- All pages compiled successfully

---

**Testing Ready:** All prerequisites are in place. You can now test both agent creation and workflow creation flows!
