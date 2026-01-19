# SwarmSync Audit Implementation Tasks

This document outlines the actionable tasks derived from the website audit conducted on Jan 9, 2026.

## 🚨 Critical Priority (Blockers)

> _These issues directly prevent core functionality or severe user friction and should be addressed immediately._

- [x] **Fix Agent Creation Form State (`new-agent-form.tsx`)**
  - [x] Investigate `react-hook-form` / `zod` validation trigger issues.
  - [x] Ensure `onChange` events bubble correctly for the "Next" button to enable immediately upon valid input.
  - [x] Debug the "dirty" state tracking to prevent users from having to toggle "Public/Private" to wake up the form.

- [x] **Fix Workflow Builder Validation (`orchestration-studio`)**
  - [x] Debug the "Agent ID is required" error even when Agent ID is present.
  - [x] Fix synchronization between the Visual Node Builder and the underlying JSON payload.
  - [x] Ensure specific node data (Budget, Job Reference) is correctly passed to the save handler.

## 🔴 High Priority (UX & Retention)

> _These issues confuse users or hide value, leading to drop-off._

- [x] **Dashboard Agent Visibility**
  - [x] Update the main Dashboard query to automatically include "My Agents" in the summary list without requiring a filter.
  - [x] Remove the "Register your first agent" empty state if the user _has_ created an agent but it's just not "Active" yet.

- [x] **Error Feedback Improvement**
  - [x] Add tooltips or explicit error text near disabled "Next" / "Create" buttons explaining _exactly_ which field is missing or invalid.

## 🟡 Medium Priority (SEO & Polish)

> _Important for growth and long-term quality._

- [x] **Dynamic SEO for Agent Profiles**
  - [x] Update `pages/agents/[agentId].tsx` (or equivalent) to generate dynamic `<title>` and `<meta name="description">` tags based on the Agent's Name and Description.

- [x] **Marketplace UX**
  - [x] Verify the "Next Steps" guide logic on the dashboard updates dynamically as users complete tasks (e.g., check off "Create Agent" once done).

## 🟢 Low Priority (Optimization)

> _Nice-to-haves for performance and edge cases._

- [x] **Accessibility Review**
  - [x] Test tab-navigation on the Workflow Builder canvas.
  - [x] Ensure all form inputs have associated `<label>` tags for screen readers.

- [x] **Performance Tuning**
  - [x] Audit form re-renders to reduce interaction latency on the `Agents` list page.
