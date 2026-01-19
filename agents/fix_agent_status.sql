-- Update all agents created by genesis user to APPROVED status
-- Run this directly in your database

UPDATE "Agent" 
SET status = 'APPROVED' 
WHERE "creatorId" = '73ff1ca7-59a0-4414-bf1f-56b40339f843' 
  AND status = 'DRAFT';

-- Verify the update
SELECT name, status, visibility 
FROM "Agent" 
WHERE "creatorId" = '73ff1ca7-59a0-4414-bf1f-56b40339f843'
ORDER BY name;

